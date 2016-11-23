#!/usr/bin/python
#
# Copyright 2016 Mosen
#                Tim Sutton
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
import subprocess

from string import Template
import uuid
from xml.etree import ElementTree

from autopkglib import Processor, ProcessorError

__all__ = ["CreativeCloudPackager"]

# https://helpx.adobe.com/creative-cloud/packager/ccp-automation.html
#
# https://github.com/timsutton/adobe-ccp-automation/blob/master/ccp_auto

TEMPLATE_XML = """<CCPPackage>
  <CreatePackage>
    <packageName>${package_name}</packageName>
    <packagingJobId>${packaging_job_id}</packagingJobId>
    <outputLocation>${output_location}</outputLocation>
    <is64Bit>true</is64Bit>
    <customerType>${customer_type}</customerType>
    <organizationName>${organization_name}</organizationName>
    <!-- ProductCategory should be left 'Custom' -->
    <ProductCategory>Custom</ProductCategory>
    <matchOSLanguage>true</matchOSLanguage>
	<IncludeUpdates>${include_updates}</IncludeUpdates>
	<rumEnabled>${rum_enabled}</rumEnabled>
	<updatesEnabled>${updates_enabled}</updatesEnabled>
	<appsPanelEnabled>${apps_panel_enabled}</appsPanelEnabled>
	<adminPrivilegesEnabled>${admin_privileges_enabled}</adminPrivilegesEnabled>
    <Language>
      <id>${language}</id>
    </Language>
	<Products>
		<Product>
			<sapCode>${sap_code}</sapCode>
			<version>${version}</version>
		</Product>
	</Products>
  </CreatePackage>
</CCPPackage>
"""

CUSTOMER_TYPES = ["enterprise", "team"]
CCP_PREFS_FILE = os.path.expanduser(
    "~/Library/Application Support/Adobe/CCP/CCPPreferences.xml")

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
        "include_updates": {
            "required": False,
            "default": True,
            "description": "Include all available updates, defaults to true.",
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
            "description": "Allow the desktop application to run in privileged mode, so that standard users may install apps.",
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

    def main(self):
        # Handle any pre-existing package at the expected location, and end early if it matches our
        # input manifest
        # TODO: for now we just continue on if the dir already exists
        expected_output_root = os.path.join(self.env["RECIPE_CACHE_DIR"], self.env["package_name"])
        self.env["pkg_path"] = os.path.join(expected_output_root, "Build/%s_Install.pkg" % self.env["package_name"])
        self.env["uninstaller_pkg_path"] = os.path.join(expected_output_root,
                                                        "Build/%s_Uninstall.pkg" % self.env["package_name"])

        if os.path.isdir(expected_output_root):
            self.output("Naively returning early because we seem to already have a built package.")
            return

        # Set the customer type, using CCP's preferences if none provided
        customer_type = self.env.get("customer_type")
        if not customer_type:
            ccp_prefs = self.ccp_preferences()
            customer_type = ccp_prefs.get("customer_type")
            if not customer_type:
                raise ProcessorError(
                    "No customer_type input provided and unable to read one "
                    "from %s" % CCP_PREFS_FILE)
            self.output("Using customer type '%s' found in CCPPreferences: %s'"
                        % (customer_type, CCP_PREFS_FILE))

        if customer_type not in CUSTOMER_TYPES:
            raise ProcessorError(
                "customer_type input variable must be one of : %s" %
                ", ".join(CUSTOMER_TYPES))

        jobid = uuid.uuid4()
        # Take input params
        xml_data = Template(TEMPLATE_XML).safe_substitute(
            package_name=self.env["package_name"],
            packaging_job_id=jobid,
            customer_type=customer_type,
            organization_name=self.env["organization_name"],
            include_updates=self.env["include_updates"],
            rum_enabled=self.env["rum_enabled"],
            language=self.env["language"],
            updates_enabled=self.env["updates_enabled"],
            apps_panel_enabled=self.env["apps_panel_enabled"],
            admin_privileges_enabled=self.env["admin_privileges_enabled"],
            output_location=self.env["RECIPE_CACHE_DIR"],
            sap_code=self.env["product_id"],
            version=self.env["version"])

        # using .xml as a suffix because CCP's automation mode creates a '<input>_results.xml' file with the assumption
        # that the input ends in '.xml'
        xml_path = "{}/ccp_autopkg_{}.xml".format(self.env["RECIPE_CACHE_DIR"], jobid)
        with open(xml_path, 'w+') as xml_fd:
            xml_fd.write(xml_data)

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
                autopkg_error_msg += "Error type: '%s'\n" % err_msg_type.text
            if err_msg_type.text == "CustomerTypeMismatchError":
                autopkg_error_msg += (
                    "Please check that your organization is of the correct "
                    "type, either 'enterprise' or 'team'.\n")
            if err_msg_type.text == "TronWelcomeInputValidationError":
                autopkg_error_msg += (
                    "Please check that your organization ID (you provided "
                    "'%s') matches one to which your CCP-signed-in user "
                    "belongs.\n") % self.env["organization_name"]
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
