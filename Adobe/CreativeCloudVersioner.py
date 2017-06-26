#!/usr/bin/python

# Copyright 2017 Mosen/Tim Sutton/Macmule
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=locally-disabled, import-error, invalid-name, no-member

# for now
# pylint: disable=line-too-long

import json
import os
import re
import zipfile

from xml.etree import ElementTree

import FoundationPlist
from autopkglib import Processor, ProcessorError

__all__ = ["CreativeCloudVersioner"]


class CreativeCloudVersioner(Processor):
    '''Parses generated CCP installers for detailed application path and bundle
    version info, for use in Munki installs info and JSS application inventory
    info for Smart Group templates. 'version' is used to store the bundle version
    because the JSS recipe uses app inventory version info for the Smart Group
    criteria'''
    description = __doc__
    input_variables = {

    }

    output_variables = {
        "additional_pkginfo": {
            "description":
                "Some pkginfo fields extracted from the Adobe metadata.",
        },
        "jss_inventory_name": {
            "description": "Application title for jamf pro smart group criteria.",
        },
        "user_facing_version": {
            "description": ("The version which would be seen in the application's About window, "
                            "and which is referred to in documentation and marketing materials."),
        },
        "version": {
            "description": ("The value of CFBundleShortVersionString for the app bundle. "
                            "This may match user_facing_version, but it may also be more "
                            "specific and add another version component."),
        },
    }


    def main(self):
        ''' Read .json & .pimx to .app, then read info.plist'''
        ccpinfo = self.env["ccpinfo"]
        # 'version' contains that which was extracted from the feed, which is
        # actually what we want as a user-facing version, so just grab it
        # immediately
        self.env["user_facing_version"] = self.env["version"]
        self.env["prod"] = ccpinfo["Products"]
        self.env["sapCode"] = self.env["prod"][0]["sapCode"]
        self.output("sapCode: %s" % self.env["sapCode"])
        self.env["ccpVersion"] = self.env["prod"][0]["version"]
        self.output("ccpVersion: %s" % self.env["ccpVersion"])
        self.env["app_json"] = os.path.join(self.env["pkg_path"], "Contents/Resources/HD", self.env["sapCode"] + self.env["ccpVersion"], "Application.json")
        # If Application.json exists, we"re looking at a HD installer
        if os.path.exists(self.env["app_json"]):
            self.output("app_json: %s" % self.env["app_json"])
            self.process_hd_installer()
        else:
            # If not a HD installer
            # Legacy Installers: PKG"s but for old titles
            # RIBS: SPGD, LTRM, FLBR, KETK
            # If the above get moved to HD installs, won"t hit this.
            # Acrobat is a "current" title with a PKG installer we can extract needed
            # metadata from
            if self.env["sapCode"] != "APRO":
                raise ProcessorError("RIBS or legacy installer detected")
            else:
                self.env["proxy_xml"] = os.path.join(self.env["pkg_path"], "Contents/Resources/Setup", self.env["sapCode"] + self.env["ccpVersion"], "proxy.xml")
                if not os.path.exists(self.env["proxy_xml"]):
                    raise ProcessorError("APRO selected, proxy.xml not found at %s" % self.env["proxy_xml"])
                else:
                    self.process_apro_installer()


    def process_apro_installer(self):
        ''' Process APRO installer '''
        self.output("Processing Acrobat installer")
        self.output("proxy_xml: %s" % self.env["proxy_xml"])
        tree = ElementTree.parse(self.env["proxy_xml"])
        # The below parses the proxy.xml for the info needs to build an installs.
        # Tried to be verbose in selecting elements, in the hope we don"t trip up
        for elem in list(tree.iter("Properties")):
            for sub_elem in elem.getchildren():
                if sub_elem.attrib["name"].startswith("path"):
                    app_bundle = re.split("/", sub_elem.text)[1]
                    self.output("app_bundle: %s" % app_bundle)

        for elem in list(tree.iter("InstallDir")):
            for sub_elem in elem.getchildren():
                if sub_elem.text.startswith("[AdobeProgramFiles]"):
                    app_path = re.split("/", sub_elem.text)[1]
                    self.output("app_path: %s" % app_path)

        installed_path = os.path.join("/Applications", app_path, app_bundle)
        self.output("installed_path: %s" % installed_path)

        for elem in list(tree.iter("InstallerProperties")):
            for sub_elem in elem.getchildren():
                if sub_elem.attrib["name"].startswith("ProductVersion"):
                    app_version = sub_elem.text
                    self.output("app_version: %s" % app_version)

        #for elem in list(tree.iter("Application")):
        #    app_identifier = elem.attrib["CFBundleIdentifier"]
        #    self.output("app_identifier: %s" % app_identifier)

        # Now we have the deets, let"s use them
        self.create_pkginfo(app_bundle, app_version, installed_path)


    def process_hd_installer(self):
        ''' Process HD installer '''
        self.output("Processing HD installer")
        with open(self.env["app_json"]) as json_file:
            load_json = json.load(json_file)
            # AppLaunch is not always in the same format, but is splittable
            app_launch = load_json["AppLaunch"]
            self.output("app_launch: %s" % app_launch)
            app_details = list(re.split("/", app_launch))
            if app_details[2].endswith(".app"):
                app_bundle = app_details[2]
                app_path = app_details[1]
            else:
                app_bundle = app_details[1]
                app_path = list(re.split("/", (load_json["InstallDir"]["value"])))[1]
            self.output("app_bundle: %s" % app_bundle)
            self.output("app_path: %s" % app_path)

            installed_path = os.path.join("/Applications", app_path, app_bundle)
            self.output("installed_path: %s" % installed_path)
            zip_file = load_json["Packages"]["Package"][0]["PackageName"]
            self.output("zip_file: %s" % zip_file)

            zip_path = os.path.join(self.env["pkg_path"], "Contents/Resources/HD", self.env["sapCode"] + self.env["ccpVersion"], zip_file + ".zip")
            self.output("zip_path: %s" % zip_path)
            with zipfile.ZipFile(zip_path, mode="r") as myzip:
                with myzip.open(zip_file + ".pimx") as mytxt:
                    txt = mytxt.read()
                    tree = ElementTree.fromstring(txt)
                    # Loop through .pmx's Assets, look for target=[INSTALLDIR], then grab Assets Source.
                    # Break when found .app/Contents/Info.plist
                    for elem in tree.findall("Assets"):
                        for i in  elem.getchildren():
                            if i.attrib["target"].upper().startswith("[INSTALLDIR]"):
                                bundle_location = i.attrib["source"]
                            else:
                                continue
                            if not bundle_location.startswith("[StagingFolder]"):
                                continue
                            else:
                                bundle_location = bundle_location[16:]
                                if bundle_location.endswith(".app"):
                                    zip_bundle = os.path.join("1", bundle_location, "Contents/Info.plist")
                                else:
                                    zip_bundle = os.path.join("1", bundle_location, app_bundle, "Contents/Info.plist")
                                try:
                                    with myzip.open(zip_bundle) as myplist:
                                        plist = myplist.read()
                                        data = FoundationPlist.readPlistFromString(plist)
                                        app_version = data["CFBundleShortVersionString"]
                                        #app_identifier = data["CFBundleIdentifier"]
                                        self.output("staging_folder: %s" % bundle_location)
                                        self.output("staging_folder_path: %s" % zip_bundle)
                                        self.output("app_version: %s" % app_version)
                                        self.output("app_bundle: %s" % app_bundle)
                                        #self.output("app_identifier: %s" % app_identifier)
                                        break
                                except:
                                    continue

        # Now we have the deets, let's use them
        self.create_pkginfo(app_bundle, app_version, installed_path)


    def create_pkginfo(self, app_bundle, app_version, installed_path):
        ''' Create pkginfo with found details '''
        pkginfo = {}
        self.env["version"] = app_version
        self.env["jss_inventory_name"] = app_bundle
        pkginfo["display_name"] = self.env["display_name"]
        pkginfo["minimum_os_version"] = self.env["minimum_os_version"]
        pkginfo["installs"] = [{
            #"CFBundleIdentifier": app_identifier,
            "CFBundleShortVersionString": self.env["version"],
            "path": installed_path,
            "type": "application",
            "version_comparison_key": "CFBundleShortVersionString",
        }]
        self.env["additional_pkginfo"] = pkginfo
        self.output("additional_pkginfo: %s" % self.env["additional_pkginfo"])


if __name__ == "__main__":
    processor = CreativeCloudVersioner()
