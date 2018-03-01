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
    """Parses generated CCP installers for detailed application path and bundle
    version info, for use in Munki installs info and JSS application inventory
    info for Smart Group templates. 'version' is used to store the bundle version
    because the JSS recipe uses app inventory version info for the Smart Group
    criteria"""
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
        """
        Determine a pkginfo, version and jss inventory name from the created package.

        Inputs:
            ccpinfo: The CCPInfo dict which was included in the original recipe.
            version: The desired version
        Outputs:
            user_facing_version: The version which would be seen in the application's About window.
            prod: The CCPInfo products dictionary
            sapCode: The SAP Code of the product
            ccpVersion:
            app_json: The path of the Application.json file that CCP produced as part of the build process

        """
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
            self.output("Assuming RIBS installer since path does not exist: {}".format(self.env["app_json"]))
            # If not a HD installer
            # Legacy Installers: PKG"s but for old titles
            # RIBS: SPGD, LTRM, FLBR, KETK
            # If the above get moved to HD installs, won"t hit this.
            # Acrobat is a "current" title with a PKG installer we can extract needed
            # metadata from
            if self.env["sapCode"] != "APRO":
                self.process_ribs_installer(self.env['pkg_path'], sap_code_hint=self.env['sapCode'])
            else:
                self.env["proxy_xml"] = os.path.join(self.env["pkg_path"], "Contents/Resources/Setup", self.env["sapCode"] + self.env["ccpVersion"], "proxy.xml")
                if not os.path.exists(self.env["proxy_xml"]):
                    raise ProcessorError("APRO selected, proxy.xml not found at %s" % self.env["proxy_xml"])
                else:
                    self.process_apro_installer()

    def process_apro_installer(self):
        """ Process APRO installer """
        self.output("Processing Acrobat installer")
        self.output("proxy_xml: %s" % self.env["proxy_xml"])
        tree = ElementTree.parse(self.env["proxy_xml"])
        root = tree.getroot()

        app_bundle_text = root.findtext("./ThirdPartyComponent/Metadata/Properties/Property[@name='path']")
        app_bundle = app_bundle_text.split('/')[1]
        self.output("app_bundle: %s" % app_bundle)

        app_path_text = root.findtext('./InstallDir/Platform')
        self.output(app_path_text)
        app_path = app_path_text.split('/')[1]
        self.output("app_path: %s" % app_path)

        installed_path = os.path.join("/Applications", app_path, app_bundle)
        self.output("installed_path: %s" % installed_path)

        app_version = root.findtext('./InstallerProperties/Property[@name="ProductVersion"]')
        self.output("app_version: %s" % app_version)

        # Now we have the deets, let"s use them
        self.create_pkginfo(app_bundle, app_version, installed_path)

    def process_hd_installer(self):
        """Process HD installer

        Inputs:
              app_json: Path to the Application JSON that was extracted from the feed.
        """
        self.output("Processing HD installer")
        with open(self.env["app_json"]) as json_file:
            load_json = json.load(json_file)

            # AppLaunch is not always in the same format, but is splittable
            if 'AppLaunch' in load_json:  # Bridge CC is HD but does not have AppLaunch
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

    def process_ribs_installer(self, pkg_path, sap_code_hint=None):
        """Extract version number of RIBS based package.

        Args:
            pkg_path (str): Path to the package that was produced
            sap_code_hint (str): hint the sap code of the "main" package, to extract the version from.
        """
        option_xml_path = os.path.join(pkg_path, 'Contents', 'Resources', 'optionXML.xml')
        # ribs_root = os.path.join(pkg_path, 'Contents', 'Resources', 'Setup')

        option_xml = ElementTree.parse(option_xml_path)
        main_media = None
        for media in option_xml.findall('.//Medias/Media'):  # Media refers to RIBS media only. HD is in HDMedia
            if media.findtext('SAPCode') == sap_code_hint:
                main_media = media
                break

        if main_media is None:
            raise ProcessorError('Could not find main RIBS package indicated by SAP Code {}'.format(sap_code_hint))

        # media_path = os.path.join(ribs_root, main_media.findtext('TargetFolderName'))
        # if not os.path.exists(media_path):
        #     raise ProcessorError('Could not find Media for RIBS package in path: {}'.format(media_path))

        self.create_pkginfo('NOT_SUPPORTED', main_media.findtext('prodVersion'), '')

    def create_pkginfo(self, app_bundle, app_version, installed_path):
        """Create pkginfo with found details

        Args:
              app_bundle (str): Bundle name
              app_version (str): Bundle version
              installed_path (str): The path where the installed item will be installed.
        """
        self.env["version"] = app_version
        self.env["jss_inventory_name"] = app_bundle
        
        pkginfo = {
            'display_name': self.env["display_name"],
            'minimum_os_version': self.env["minimum_os_version"]
        }

        # Allow the user to provide an installs array that prevents CreativeCloudVersioner from overriding it.
        if 'pkginfo' not in self.env or 'installs' not in self.env['pkginfo']:
            pkginfo['installs'] = [{
                'CFBundleShortVersionString': self.env['version'],
                'path': installed_path,
                'type': 'application',
                'version_comparison_key': 'CFBundleShortVersionString',
            }]

        self.env["additional_pkginfo"] = pkginfo
        self.output("additional_pkginfo: %s" % self.env["additional_pkginfo"])


if __name__ == "__main__":
    processor = CreativeCloudVersioner()
