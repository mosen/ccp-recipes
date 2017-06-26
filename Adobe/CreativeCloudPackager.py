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
import FoundationPlist

from xml.etree import ElementTree
from Foundation import CFPreferencesCopyAppValue, CFPreferencesSetAppValue

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
        ("Please check that your organizationName matches one to which your "
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
        "ccpinfo": {
            "required": True,
            "description": "Creative Cloud Packager Product(s) Information",
        },
        "package_name": {
            "required": True,
            "description": "The output package name",
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

    def automation_xml(self):
        """Returns the complete pretty-formatted XML string for a CCP automation
        session."""
        # params = self.automation_manifest_from_ccpinfo()
        params = dict(self.env['ccpinfo'])

        # add additional parameters for which there's no need for the user to
        # supply in the 'ccpinfo' input
        params.update({
            'packageName': self.env['package_name'],
            'outputLocation': self.env['RECIPE_CACHE_DIR'],
            'packaging_job_id': str(uuid.uuid4()),
            'IncludeUpdates': False,
            'is64Bit': True,
        })

        # if params.get('serial_number') and scrub_serial:
        #     params['serial_number'] = 'REDACTED'

        # Begin assembling XML Element
        pkg_elem = ElementTree.Element('CreatePackage')
        # add some hardcoded elements
        category = ElementTree.Element('ProductCategory')
        category.text = 'Custom'
        pkg_elem.append(category)
        # language - must be included even if matchOSLanguage is true

        lang = ElementTree.Element('Language')
        lang.append(ElementTree.Element('id'))
        lang.find('id').text = params['Language']
        pkg_elem.append(lang)
        del params['Language']

        # Input keys now match the target XML to avoid transforming
        for param, value in params.iteritems():
            if param == 'Products':
                continue

            elem = ElementTree.Element(param)
            if isinstance(value, bool):
                value = str(value).lower()
            elem.text = value

            pkg_elem.append(elem)

        # Products
        products = ElementTree.Element('Products')
        for prod in params['Products']:
            product = ElementTree.Element('Product')
            sap = ElementTree.Element('sapCode')
            sap.text = prod['sapCode']
            ver = ElementTree.Element('version')
            ver.text = prod['version']
            product.append(sap)
            product.append(ver)
            products.append(product)
        pkg_elem.append(products)

        # # serial
        # if params.get('serialNumber'):
        #     self.output('Adding serial number to ccp_automation xml')
        #     serial = ElementTree.Element('serialNumber')
        #     serial.text = params['serial_number']
        #     pkg_elem.append(serial)

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

    def set_customer_type(self, ccpinfo):
        # Set the customer type, using CCP's preferences if none provided
        if not ccpinfo.get("customerType"):
            ccp_prefs = self.ccp_preferences()
            self.env['customer_type'] = ccp_prefs.get("customer_type")
            if not self.env.get("customer_type"):
                raise ProcessorError(
                    "No customer_type input provided and unable to read one "
                    "from %s" % CCP_PREFS_FILE)
            self.output("Using customer type '%s' found in CCPPreferences: %s'"
                        % (self.env['customer_type'], CCP_PREFS_FILE))

    def is_ccp_running(self):
        """Determine whether CCP is already running. This would prevent us from actually running the automation XML."""
        status = subprocess.call(['/usr/bin/pgrep', '-q', 'PDApp'])
        return status == 0

    def check_and_disable_appnap_for_pdapp(self):
        """Log a warning if AppNap isn't disabled on the system."""
        appnap_disabled = CFPreferencesCopyAppValue(
            'NSAppSleepDisabled',
            'com.adobe.PDApp')
        if not appnap_disabled:
            self.output("WARNING: A bug in Creative Cloud Packager makes "
                        "it likely to stall indefinitely whenever the app "
                        "window is hidden or obscured due to App Nap. To "
                        "prevent this, we're setting a user preference to "
                        "disable App Nap for just the "
                        "Adobe PDApp application. This can be undone using "
                        "this command: 'defaults delete com.adobe.PDApp "
                        "NSAppSleepDisabled")
            CFPreferencesSetAppValue(
                'NSAppSleepDisabled',
                True,
                'com.adobe.PDApp')

    def validate_input(self):
        """Validate input variables will produce something meaningful."""
        ccpinfo = self.env['ccpinfo']

        if 'Products' not in ccpinfo or len(ccpinfo['Products']) == 0:
            raise ProcessorError('ccpinfo does not specify any products. Please check your recipe.')

        for prod in ccpinfo['Products']:
            if 'sapCode' not in prod:
                raise ProcessorError('ccpinfo product did not contain a SAP Code')

        if 'organizationName' not in ccpinfo or ccpinfo['organizationName'] == 'ADMIN_PLEASE_CHANGE':
            raise ProcessorError('No organization name specified in recipe.')

        if ccpinfo['customerType'] not in CUSTOMER_TYPES:
            raise ProcessorError(
                "customerType input variable must be one of : %s" %
                ", ".join(CUSTOMER_TYPES))

        if ccpinfo['customerType'] != 'enterprise' and ccpinfo.get('serialNumber'):
            raise ProcessorError(
                ("Serial number was given, but serial numbers are only for "
                 "use with 'enterprise' customer types."))

    def check_ccda_installed(self):
        """Check and raise a ProcessorError if the CCDA is installed, as CCP should
        never build packages on a system with the CCDA installed"""
        ccda_path = '/Applications/Utilities/Adobe Creative Cloud/ACC/Creative Cloud.app'
        if os.path.isdir(ccda_path):
            raise ProcessorError(
                ("The Adobe Creative Cloud Desktop App was detected at '%s'. "
                 "This recipe will only run on systems without it installed, "
                 "as it can otherwise cause major issues with built packages. "
                 "It can be uninstalled using the Uninstaller located at "
                 "'/Applications/Utilities/Adobe Creative Cloud'.") % ccda_path)

    def main(self):
        # self.check_ccda_installed()

        # establish some of our expected build paths
        expected_output_root = os.path.join(self.env["RECIPE_CACHE_DIR"], self.env["package_name"])
        self.env["pkg_path"] = os.path.join(expected_output_root, "Build/%s_Install.pkg" % self.env["package_name"])
        self.env["uninstaller_pkg_path"] = os.path.join(expected_output_root,
                                                        "Build/%s_Uninstall.pkg" % self.env["package_name"])

        saved_automation_xml_path = os.path.join(expected_output_root,
                                                 '.ccp_automation_input.xml')
        automation_manifest_plist_path = os.path.join(expected_output_root,
                                                      '.autopkg_manifest.plist')
        self.set_customer_type(self.env['ccpinfo'])
        # Handle any pre-existing package at the expected location, and end early if it matches our
        # input manifest
        if os.path.exists(automation_manifest_plist_path):
            existing_manifest = FoundationPlist.readPlist(automation_manifest_plist_path)
            new_manifest = self.env['ccpinfo']
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
        xml_path = os.path.join(xml_workdir, 'ccp_automation_%s.xml' % self.env['package_name'])
        with open(xml_path, 'w') as fd:
            fd.write(xml_data)

        if self.is_ccp_running():
            raise ProcessorError(
                "You cannot start a Creative Cloud Packager automation workflow " +
                "if Creative Cloud Packager is already running. Please quit CCP and start this recipe again."
            )

        self.check_and_disable_appnap_for_pdapp()

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
            self.env['ccpinfo'],
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
