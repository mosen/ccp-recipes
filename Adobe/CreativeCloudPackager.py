#!/usr/bin/python

# Copyright 2016 Mosen/Tim Sutton
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

import os
import shutil
import subprocess
import uuid

from xml.etree import ElementTree
from Foundation import CFPreferencesCopyAppValue
import FoundationPlist

from autopkglib import Processor, ProcessorError

__all__ = ["CreativeCloudPackager"]

# https://helpx.adobe.com/creative-cloud/packager/ccp-automation.html
#
# https://github.com/timsutton/adobe-ccp-automation/blob/master/ccp_auto

CUSTOMER_TYPES = ["enterprise", "team"]
CCP_PREFS_FILE = os.path.expanduser(
    "~/Library/Application Support/Adobe/CCP/CCPPreferences.xml")

CCP_ERROR_MSGS = {
    "CustomerTypeMismatchError": \
        ("Please check that your organization is of the correct "
         "type, one of ({}).".format(', '.join(CUSTOMER_TYPES))),
    "TronWelcomeInputValidationError": \
        ("Please check that your ORG_NAME matches one to which your "
         "CCP-signed-in user ""belongs."),
    "TronSerialNumberValidationError": \
        ("Serial number validation failed."),
}
# Note: TronWelcomeInputValidationError can also happen if  a file or folder
# already exists at the package path given. Sample result output in that case:
# <TronResult version="1.0">
#   <error>
#     <errorCode>2</errorCode>
#     <shouldRetry>false</shouldRetry>
#     <errorMessage>TronWelcomeInputValidationError</errorMessage>
#   </error>
# </TronResult>

# Note: if the user supplies an incorrect SAP Code or a product that cannot be packaged individually (like AAM)
# you will receive this error:
# <TronResult version="1.0">
# <error>
# <errorCode>3</errorCode>
# <shouldRetry>false</shouldRetry>
# <errorMessage>productNotFound</errorMessage>
# </error>
# </TronResult>


class CreativeCloudPackager(Processor):
    """Create and execute a CCP automation file. The package output will always be the autopkg cache directory"""
    description = "Runs the CCP packager."
    input_variables = {
        "package_name": {
            "required": True,
            "description": "The output package name",
        },
        "customer_type": {
            "required": False,
            "description": ("The license type, one of: %s. If this "
                            "is omitted, CCP's preferences for the last "
                            "logged-in user will be queried and that customer "
                            "type used here.") % ", ".join(CUSTOMER_TYPES),
        },
        "organization_name": {
            "required": True,
            "description": ("The organization name which must match your "
                            "licensed organization. This can be obtained from "
                            "either the Enterprise Dashboard (upper right), or "
                            "by looking in Contents/Resources/optionXML.xml of "
                            "a previously-built package, in the "
                            "OrganizationName element."),
        },
        "serial_number": {
            "required": False,
            "description": "The serial number, if you are using serialized packages.",
        },
        "device_pool_name": {
            "required": False,
            "description": ("The 'Deployment Pool', if building a Teams Device "
                            "License package is desired."),
        },
        "include_updates": {
            "required": False,
            "default": True,
            "description": "Include all available updates, defaults to true.",
        },
        "match_os_language": {
            "required": False,
            "default": "true",
            "description": "Match the Operating System language when building packages, default is True."
        },
        "language": {
            "required": False,
            "default": "en_US",
            "description": "The language to build, defaults to en_US.",
        },
        "rum_enabled": {
            "required": False,
            "default": True,
            "description": "Include RUM in the package",
        },
        "updates_enabled": {
            "required": False,
            "default": True,
            "description": "Enable updates",
        },
        "apps_panel_enabled": {
            "required": False,
            "default": True,
            "description": "Enable access to the apps panel in the desktop application",
        },
        "admin_privileges_enabled": {
            "required": False,
            "default": False,
            "description": (
                "Allow the desktop application to run in privileged mode,"
                "so that standard users may install apps."
            )
        },
        "download_changed": {
            "required": False,
            "description": (
                "download_changed is set by the CreativeCloudFeed processor to "
                "indicate that a new product is available. If this key is set "
                "in the environment and is False or empty the package workflow "
                "will be skipped.")
        },
    }

    output_variables = {
        "pkg_path": {
            "description": "Path to the built bundle-style CCP installer pkg.",
        },
        "uninstaller_pkg_path": {
            "description": "Path to the built bundle-style CCP uninstaller pkg.",
        },
        "ccp_path": {
            "description": "Path to the .ccp file output from the build process."
        },
        "package_info_text": {
            "description": "Text notes about which packages and updates are included in the pkg."
        },
        "ccp_version": {
            "description": "Version of CCP tools used to build the package."
        },
    }

    def ccp_preferences(self):
        """Get information about the currently signed-in CCP user, if available."""
        prefs_path = os.path.expanduser(CCP_PREFS_FILE)
        prefs_elem = ElementTree.parse(prefs_path).getroot()

        prefs = {}
        user_type_elem = prefs_elem.find('AAMEEPreferences/Preference/Screen/userType')
        if user_type_elem is not None:
            # convert 'FOO_CUSTOMER_TYPE' into 'foo'
            prefs["customer_type"] = user_type_elem.text.lower().split('_')[0]
        return prefs

    def automation_manifest_from_env(self, scrub_serial=False):
        '''Returns a dict containing CCP automation data derived from the env. Omits
        irrelevant data such as output location and packaging job id.
        scrub_serial will redact the serial number in cases where this dict
        is being recorded to disk (along with the built package).'''
        manifest = {}
        # copy all defined params for this processor into a top-level dict
        for param in self.input_variables.keys():
            if param in self.env.keys():
                # skip any parameters that are defined but empty strings,
                # like serial_number or device_pool_name.
                # CCP automation will pick a different package type depending on
                # whether these elements exist or not, so we need to be careful
                # to not copy a serial or device pool setting to the XML being
                # fed to CCP, even if it's an empty string.
                if self.env[param] == '':
                    continue
                manifest[param] = self.env[param]

        manifest['products'] = []
        manifest['products'].append({
            'sap_code': self.env['product_id'],
            'version': self.env['version'],
        })
        manifest['language'] = self.env['language']

        if manifest.get('serial_number') and scrub_serial:
            manifest['serial_number'] = 'REDACTED'
        return manifest

    def automation_xml(self):
        '''Returns the complete pretty-formatted XML string for a CCP automation
        session.'''
        params = self.automation_manifest_from_env()
        params.update({
            'output_location': self.env['RECIPE_CACHE_DIR'],
            'packaging_job_id': str(uuid.uuid4()),
        })

        # Begin assembling XML Element
        pkg_elem = ElementTree.Element('CreatePackage')
        # add some hardcoded elements
        category = ElementTree.Element('ProductCategory')
        category.text = 'Custom'
        pkg_elem.append(category)
        is_64 = ElementTree.Element('is64Bit')
        is_64.text = 'true'
        pkg_elem.append(is_64)
        match_os = ElementTree.Element('matchOSLanguage')
        if params.get('match_os_language', 'true').lower() == 'false':
            match_os.text = 'false'
        else:
            match_os.text = 'true'

        pkg_elem.append(match_os)

        # substituting snake case for camel case for all top-level elements
        # except the 'products' list
        for param, value in params.iteritems():
            if param == 'products':
                continue

            # Convert param from snake_case to camelCase
            # http://stackoverflow.com/a/19053800
            components = param.split('_')
            transformed_param = components[0] + \
                                "".join(x.title() for x in components[1:])
            # ..except 'IncludeUpdates', which has a different casing pattern!
            if param == 'include_updates':
                transformed_param = 'IncludeUpdates'
            elem = ElementTree.Element(transformed_param)
            if isinstance(value, bool):
                value = str(value).lower()
            elem.text = value
            pkg_elem.append(elem)
        # language
        lang = ElementTree.Element('Language')
        lang.append(ElementTree.Element('id'))
        lang.find('id').text = params['language']

        # products
        products = ElementTree.Element('Products')
        for prod in params['products']:
            product = ElementTree.Element('Product')
            sap = ElementTree.Element('sapCode')
            sap.text = prod['sap_code']
            ver = ElementTree.Element('version')
            ver.text = prod['version']
            product.append(sap)
            product.append(ver)
            products.append(product)
        pkg_elem.append(products)

        # serial
        if params.get('serial_number'):
            self.output('Adding serial number to ccp_automation xml')
            serial = ElementTree.Element('serialNumber')
            serial.text = params['serial_number']
            pkg_elem.append(serial)

        pkg_elem.append(lang)
        xml_root = ElementTree.Element('CCPPackage')
        xml_root.append(pkg_elem)

        # run it through `xmllint --format` just to save it pretty :/
        xml_string = ElementTree.tostring(xml_root, encoding='utf8', method='xml')
        proc = subprocess.Popen(['/usr/bin/xmllint', '--format', '-'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        out, err = proc.communicate(xml_string)
        if proc.returncode:
            raise ProcessorError("Unexpected error from running XML output through "
                                 "xmllint. Stderr output:\n%s" % err)
        return out

    def set_customer_type(self):
        # Set the customer type, using CCP's preferences if none provided
        # if not self.env.get("customer_type"):
        #     ccp_prefs = self.ccp_preferences()
        #     self.env['customer_type'] = ccp_prefs.get("customer_type")
        #     if not self.env.get("customer_type"):
        #         raise ProcessorError(
        #             "No customer_type input provided and unable to read one "
        #             "from %s" % CCP_PREFS_FILE)
        #     self.output("Using customer type '%s' found in CCPPreferences: %s'"
        #                 % (self.env['customer_type'], CCP_PREFS_FILE))

        if self.env['customer_type'] not in CUSTOMER_TYPES:
            raise ProcessorError(
                "customer_type input variable must be one of : %s" %
                ", ".join(CUSTOMER_TYPES))
        if self.env['customer_type'] != 'enterprise' and self.env.get('serial_number'):
            raise ProcessorError(
                ("Serial number was given, but serial numbers are only for "
                 "use with 'enterprise' customer types."))

    def is_ccp_running(self):
        """Determine whether CCP is already running. This would prevent us from actually running the automation XML."""
        status = subprocess.call(['/usr/bin/pgrep', '-q', 'PDApp'])
        return status == 0

    def check_disabled_appnap(self):
        """Log a warning if AppNap isn't disabled on the system."""
        appnap_disabled = CFPreferencesCopyAppValue(
            'NSAppSleepDisabled',
            '.GlobalPreferences'
        )
        if not appnap_disabled:
            self.output("WARNING: A bug in Creative Cloud Packager makes "
                        "it likely to stall indefinitely whenever it is not "
                        "the foreground application due to App Nap, which is "
                        "currently enabled on this system. To prevent this, "
                        "you may wish to disable it on the system for the "
                        "current user using this command: "
                        "'defaults write -g NSAppSleepDisabled -bool true'. "
                        "Re-enable it at any time using 'defaults delete -g "
                        "NSAppSleepDisabled'")

    def main(self):
        # if 'download_changed' in self.env and not self.env['download_changed']:
        #     self.output("Skipping CCP build: version has not changed.")
        #     return

        # establish some of our expected build paths
        expected_output_root = os.path.join(self.env["RECIPE_CACHE_DIR"], self.env["package_name"])
        self.env["pkg_path"] = os.path.join(expected_output_root, "Build/%s_Install.pkg" % self.env["package_name"])
        self.env["uninstaller_pkg_path"] = os.path.join(expected_output_root,
                                                        "Build/%s_Uninstall.pkg" % self.env["package_name"])

        saved_automation_xml_path = os.path.join(expected_output_root,
                                                 '.ccp_automation_input.xml')
        automation_manifest_plist_path = os.path.join(expected_output_root,
                                                      '.autopkg_manifest.plist')
        self.set_customer_type()
        # Handle any pre-existing package at the expected location, and end early if it matches our
        # input manifest
        if os.path.exists(automation_manifest_plist_path):
            existing_manifest = FoundationPlist.readPlist(automation_manifest_plist_path)
            new_manifest = self.automation_manifest_from_env(scrub_serial=True)
            self.output("Found existing CCP package build automation info, comparing")
            self.output("existing build: %s" % existing_manifest)
            self.output("current build: %s" % new_manifest)
            if new_manifest == existing_manifest:
                self.output("Returning early because we have an existing package "
                            "with the same parameters.")
                return

        # Going forward with building, set up or clear needed directories
        xml_workdir = os.path.join(self.env["RECIPE_CACHE_DIR"], 'automation_xml')
        if not os.path.exists(xml_workdir):
            os.mkdir(xml_workdir)
        if os.path.isdir(expected_output_root):
            shutil.rmtree(expected_output_root)

        xml_data = self.automation_xml()
        # using .xml as a suffix because CCP's automation mode creates a '<input>_results.xml' file with the assumption
        # that the input ends in '.xml'
        xml_path = os.path.join(xml_workdir, 'ccp_automation_%s.xml' % self.env['NAME'])
        with open(xml_path, 'w') as fd:
            fd.write(xml_data)

        if self.is_ccp_running():
            raise ProcessorError(
                "You cannot start a Creative Cloud Packager automation workflow " +
                "if Creative Cloud Packager is already running. Please quit CCP and start this recipe again."
            )

        self.check_disabled_appnap()

        cmd = [
            '/Applications/Utilities/Adobe Application Manager/core/Adobe Application Manager.app/Contents/MacOS/PDApp',
            '--appletID=CCP_UI',
            '--appletVersion=1.0',
            '--workflow=ccp',
            '--automationMode=ccp_automation',
            '--pkgConfigFile=%s' % xml_path]
        self.output("Executing CCP build command: %s" % " ".join(cmd))
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        if out:
            self.output("CCP Output: %s" % out)
        exitcode = proc.returncode
        self.output("CCP Exited with status {}".format(exitcode))

        results_file = os.path.join(os.path.dirname(xml_path), os.path.splitext(xml_path)[0] + '_result.xml')
        results_elem = ElementTree.parse(results_file).getroot()
        if results_elem.find('error') is not None:
            # Build an AutoPkg error message with help to diagnose
            # possible build failures
            autopkg_error_msg = "CCP package build reported failure.\n"
            err_msg_type = results_elem.find('error/errorMessage')
            if err_msg_type is not None:
                autopkg_error_msg += "Error type: '%s' - " % err_msg_type.text
            if err_msg_type.text in CCP_ERROR_MSGS:
                autopkg_error_msg += CCP_ERROR_MSGS[err_msg_type.text] + "\n"
            autopkg_error_msg += (
                "Please inspect the PDApp log file at: %s. 'results' XML file "
                "contents follow: \n%s" % (
                    os.path.expanduser("~/Library/Logs/PDApp.log"),
                    open(results_file, 'r').read()))

            raise ProcessorError(autopkg_error_msg)

        if results_elem.find('success') is None:
            raise ProcessorError(
                "Unexpected result from CCP, 'results' XML file contents follow: \n{}".format(
                    open(results_file, 'r').read()
                )
            )

        # Sanity-check that we really do have our install package!
        if not os.path.exists(self.env["pkg_path"]):
            raise ProcessorError(
                "CCP exited successfully, but no expected installer package "
                "at %s exists." % self.env["pkg_path"])

        # Save both the automation XML for posterity and our manifest plist for
        # later comparison
        shutil.copy(xml_path, saved_automation_xml_path)
        # TODO: we aren't scrubbing the automation XML file at all
        FoundationPlist.writePlist(
            self.automation_manifest_from_env(scrub_serial=True),
            automation_manifest_plist_path)

        # Save PackageInfo.txt
        packageinfo = os.path.join(expected_output_root, "PackageInfo.txt")
        if os.path.exists(packageinfo):
            self.env["package_info_text"] = open(packageinfo, 'r').read()

        ccp_path = os.path.join(expected_output_root, 'Build/{}.ccp'.format(self.env["package_name"]))
        if os.path.exists(ccp_path):
            self.env["ccp_path"] = ccp_path

        option_xml_root = ElementTree.parse(os.path.join(
            self.env["pkg_path"], 'Contents/Resources/optionXML.xml')).getroot()

        # Save the CCP build version
        self.env["ccp_version"] = ""
        ccp_version = option_xml_root.find("prodVersion")
        if ccp_version is None:
            self.output(
                "WARNING: Didn't find expected 'prodVersion' key (CCP "
                "version) in optionXML.xml")
        self.env["ccp_version"] = ccp_version.text

if __name__ == "__main__":
    processor = CreativeCloudPackager()
    processor.execute_shell()
