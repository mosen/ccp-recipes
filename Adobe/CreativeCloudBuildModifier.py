#!/usr/bin/python

# Copyright 2017 Mosen/Tim Sutton
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

# for debugging
from pprint import pprint
import os.path
from autopkglib import Processor, ProcessorError
from xml.etree import ElementTree

__all__ = ["CreativeCloudBuildModifier"]

ACC_PACKAGE_SETS = {
    'AAM': [
        'UWA',
        'PDApp',
        'D6',
        'DECore',
        'DWA',
        'P6',
        'LWA',
        'CCM',
        'P7',
        'AdobeGCClient',
        'IPC'
    ],
    'ADC': [
        'Runtime',
        'Core',
        'HEX',
        'CEF',
        'CoreExt',
        'ElevationManager',
        'TCC',
        'Notifications',
        'SignInApp'
    ],
    'ACC': [
        'HDCore',
        'AppsPanel'
    ]
}


class CreativeCloudBuildModifier(Processor):
    """This processor parses the output of the CCP build process and makes modifications."""
    description = __doc__
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "The package produced by Creative Cloud Packager",
        },
        "suppress_ccda": {
            "description": "Suppress the installation of Creative Cloud Desktop Application.",
            "default": True
        }
    }

    def _addPackage(self, parent, name):
        """Add a package element w/name to a set"""
        pkg = ElementTree.SubElement(parent, 'package')
        name_el = ElementTree.SubElement(pkg, 'name')
        name_el.text = name

    def _addPackageSet(self, parent, set_name, package_names):
        """Add a package set given a name and list of package names"""
        pkg_set = ElementTree.SubElement(parent, 'packageSet')
        pkg_set_name = ElementTree.SubElement(pkg_set, 'name')
        pkg_set_name.text = set_name

        pkgs = ElementTree.SubElement(parent, 'packages')
        for pkg_name in package_names:
            self._addPackage(pkgs, pkg_name)

    def _suppressCcda(self, option_xml):
        """Suppress the CCDA from being installed."""
        acc = option_xml.find('ACC')
        if acc is None:
            raise ProcessorError('Unexpected: element ACC doesnt exist in the optionXML.xml')

        acc.set('suppress', 'true')

        package_sets = option_xml.find('packageSets')
        for sap, packages in ACC_PACKAGE_SETS.items():
            self._addPackageSet(package_sets, sap, packages)

    def main(self):
        if not os.path.exists(self.env['pkg_path']):
            raise ProcessorError('The specified package does not exist: {}'.format(self.env['pkg_path']))

        option_xml_path = os.path.join(self.env['pkg_path'], 'Contents', 'Resources', 'optionXML.xml')
        option_xml = ElementTree.parse(option_xml_path)

        if self.env.get('suppress_ccda', False):
            self._suppressCcda(option_xml)


if __name__ == "__main__":
    processor = CreativeCloudBuildModifier()
    processor.execute_shell()
