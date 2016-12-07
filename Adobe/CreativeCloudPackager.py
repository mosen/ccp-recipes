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
import shutil
import subprocess

from string import Template
import uuid
from xml.etree import ElementTree

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
         "type, either 'enterprise' or 'team'."),
    "TronWelcomeInputValidationError": \
        ("Please check that your ORG_NAME matches one to which your "
         "CCP-signed-in user ""belongs."),
    "TronSerialNumberValidationError": \
        ("Serial number validation failed."),
}

# http://stackoverflow.com/a/19053800
def to_camel_case(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0] + "".join(x.title() for x in components[1:])

def boolify(string_bool):
    """Return a boolean True or False given 'true', 'false' input as strings,
    else None"""
    result = None
    if string_bool in ['true', 'false']:
        result = True if string_bool == 'true' else False
    return result


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
    # input variable names that map directly to automation XML element tag names
    # except snake_case -> camelCase
    XML_MAPPABLE_NAMES = [
        'package_name',
        'customer_type',
        'organization_name',
        'customer_type',
        'rum_enabled',
        'updates_enabled',
        'include_updates',
        'apps_panel_enabled',
        'admin_privileges_enabled',
    ]

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

    def compare_ccp_pkg(self):
        pass

    def automation_manifest_from_env(self):
        '''Returns a dict containing CCP automation data derived from the env. Omits
        irrelevant data such as output location and packaging job id.'''
        manifest = {}
        # copy all defined params for this processor into a top-level dict
        for param in self.input_variables.keys():
            if param in self.env.keys():
                manifest[param] = self.env[param]
        manifest['packages'] = []
        manifest['packages'].append({
            'sap_code': self.env['product_id'],
            'version': self.env['version'],
        })
        manifest['language'] = self.env['language']
        return manifest

    def automation_manifest_from_xml(self, xml_path):
        '''Returns the same dict as automation_manifest_from_env except it is loaded
        from an existing XML input file.'''
        params = {}

        pkg_elem = ElementTree.parse(xml_path).getroot().find('CreatePackage')
        # build all the top-level elements
        for param in self.XML_MAPPABLE_NAMES:
            transformed_param = to_camel_case(param)
            elem = pkg_elem.find(transformed_param)
            if elem is not None:
                if boolify(elem.text) is not None:
                    params[param] = boolify(elem.text)
                else:
                    params[param] = elem.text
        if pkg_elem.find('IncludeUpdates') is not None:
            # updates =
            params['include_updates'] = boolify(pkg_elem.find('IncludeUpdates').text)

        # Nested items
        if pkg_elem.findall('Language/id'):
            params['language'] = pkg_elem.findall('Language/id')[0].text

        if pkg_elem.findall('Products/Product'):
            prod = pkg_elem.findall('Products/Product')[0]
            params['product_id'] = prod.find('sapCode').text
            params['version'] = prod.find('version').text

        # TODO: deal with checking serial number
        return params

    def automation_xml(self):
        params = {}
        for param in self.XML_MAPPABLE_NAMES:
            params[param] = self.env[param]
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
        match_os.text = 'true'
        pkg_elem.append(match_os)

        # substituting snake case for camel case for all the top-level subelements
        for param, value in params.iteritems():
            transformed_param = to_camel_case(param)
            # 'IncludeUpdates' has a different casing pattern!
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
        lang.find('id').text = self.env['language']

        # products
        products = ElementTree.Element('Products')
        product = ElementTree.Element('Product')
        sap = ElementTree.Element('sapCode')
        sap.text = self.env['product_id']
        ver = ElementTree.Element('version')
        ver.text = self.env['version']
        product.append(sap)
        product.append(ver)
        products.append(product)
        pkg_elem.append(products)

        # serial
        if self.env.get('serial_number'):
            self.output('Adding serial number to ccp_automation xml')
            serial = ElementTree.Element('serialNumber')
            serial.text = self.env['serial_number']
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
        if not self.env.get("customer_type"):
            ccp_prefs = self.ccp_preferences()
            self.env['customer_type'] = ccp_prefs.get("customer_type")
            if not self.env.get("customer_type"):
                raise ProcessorError(
                    "No customer_type input provided and unable to read one "
                    "from %s" % CCP_PREFS_FILE)
            self.output("Using customer type '%s' found in CCPPreferences: %s'"
                        % (self.env['customer_type'], CCP_PREFS_FILE))

        if self.env['customer_type'] not in CUSTOMER_TYPES:
            raise ProcessorError(
                "customer_type input variable must be one of : %s" %
                ", ".join(CUSTOMER_TYPES))
        if self.env['customer_type'] != 'enterprise' and self.env.get('serial_number'):
            raise ProcessorError(
                ("Serial number was given, but serial numbers are only for "
                 "use with 'enterprise' customer types."))

    def main(self):
        # establish some of our expected build paths
        expected_output_root = os.path.join(self.env["RECIPE_CACHE_DIR"], self.env["package_name"])
        self.env["pkg_path"] = os.path.join(expected_output_root, "Build/%s_Install.pkg" % self.env["package_name"])
        self.env["uninstaller_pkg_path"] = os.path.join(expected_output_root,
                                                        "Build/%s_Uninstall.pkg" % self.env["package_name"])

        saved_automation_xml_path = os.path.join(expected_output_root,
                                                  'ccp_automation_input.xml')

        self.set_customer_type()
        # Handle any pre-existing package at the expected location, and end early if it matches our
        # input manifest
        # TODO: for now we just continue on if the automation xml file already exists
        if os.path.exists(saved_automation_xml_path):
            existing_ccp_automation = self.automation_manifest_from_xml(saved_automation_xml_path)
            print existing_ccp_automation
            new_ccp_automation = self.automation_manifest_from_env()
            print new_ccp_automation
            print "EXITING EARLY!"
            exit()
            self.output("Naively returning early because we seem to already have a built package.")
            return


        xml_data = self.automation_xml()
        xml_workdir = os.path.join(self.env["RECIPE_CACHE_DIR"], 'automation_xml')
        if os.path.exists(xml_workdir):
            shutil.rmtree(xml_workdir)
        os.mkdir(xml_workdir)

        # using .xml as a suffix because CCP's automation mode creates a '<input>_results.xml' file with the assumption
        # that the input ends in '.xml'
        xml_path = os.path.join(xml_workdir, 'ccp_automation_%s.xml' % self.env['NAME'])
        with open(xml_path, 'w') as fd:
            fd.write(xml_data)

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

        shutil.copy(xml_path, saved_automation_xml_path)

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
