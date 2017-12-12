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
            "required": False,
            "default": True
        }
    }
    output_variables = {}

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

        pkgs = ElementTree.SubElement(pkg_set, 'packages')
        for pkg_name in package_names:
            self._addPackage(pkgs, pkg_name)

    def _addOverrides(self, aam_info):
        """Add the overrideXML parts for disabling CCDA"""
        overridexml = ElementTree.SubElement(aam_info, 'overrideXML')
        override_app = ElementTree.SubElement(overridexml, 'application')
        package_sets = ElementTree.SubElement(override_app, 'packageSets')

        for sap, packages in ACC_PACKAGE_SETS.items():
            self._addPackageSet(package_sets, sap, packages)

    def _removeASUPackages(self):
        """Remove ASU packages"""
        asu_appinfo_path = os.path.join(self.env['pkg_path'], 'Contents', 'Resources', 'ASU', 'packages',
                                        'ApplicationInfo.xml')
        asu_appinfo = ElementTree.parse(asu_appinfo_path)
        asu_appinfo_root = asu_appinfo.getroot()

        acc_packageset = asu_appinfo_root.find(".//packageSet[name='ACC']")
        if acc_packageset is None:
            raise ProcessorError('Tried to modify ACC installation, but no packageSet element was found. This should' +
                                 'never happen')

        packages_to_remove = [
            'ACCC',
            'Utils',
            'CoreSync',
            'CoreSyncExtension',
            'LiveType',
            'ExchangePlugin',
            'DesignLibraryPlugin',
            'SynKit',
            'CCSyncPlugin',
            'CCLibrary',
            'HomePanel',
            'AssetsPanel',
            'FilesPanel',
            'FontsPanel',
            'MarketPanel',
            'BehancePanel',
            'SPanel',
            'CCXProcess'
        ]

        # also remove package 'ADC' from 'ADC' set

        for to_remove in packages_to_remove:
            remove_pkg = acc_packageset.find("./package[name='{}']".format(to_remove))
            if remove_pkg:
                self.output('Removing package {}'.format(to_remove))

    # <ACCPanelMaskingConfig>
    # <config>
    #     <panel>
    #         <name>AppsPanel</name>
    #         <visible>false</visible>
    #     </panel>
    #     <feature>
    #       <name>SelfServeInstalls</name>
    #       <enabled>false</enabled>
    #     </feature>
    # </config>
    # </ACCPanelMaskingConfig>
    def _addPanelMasking(self, root):
        """Disable the apps and updates panels.

        AppsPanel = false
        SelfServeInstalls = false
        """
        panels = root.findall('.//Configurations/ACCPanelMaskingConfig/config')

        for panel_or_feature in panels:
            self.output(panel_or_feature)
        return root


    def _suppressCcda(self, root):
        """Suppress the CCDA from being installed."""
        acc = root.find('.//Configurations/SuppressOptions/ACC')
        if acc is None:
            raise ProcessorError('Expected to find element .//Configurations/SuppressOptions/ACC')

        acc_suppressed = acc.get('suppress')
        self.output('Creative Cloud Desktop Application (ACC) suppressed? {}'.format(acc_suppressed))

        if acc_suppressed == 'true':
            self.output('Already suppressed, no changes required.')
        else:
            self.output('Setting ACC suppress to True')
            acc.set('suppress', 'true')

        update = root.find('.//Configurations/SuppressOptions/Update')
        if update is None:
            raise ProcessorError('Expected to find element .//Configurations/SuppressOptions/Update')

        update_suppressed = update.get('isEnabled')
        self.output('User initiated updates suppressed? {}'.format(update_suppressed))

        if update_suppressed == '1':
            self.output('Already suppressed, no changes required.')
        else:
            self.output('Setting Update isEnabled to 0')
            update.set('isEnabled', '0')

        aam_info = root.find('.//AAMInfo')

        package_sets = root.find('.//AAMInfo/overrideXML/application/packageSets')
        if package_sets is None:
            self.output('Need to add overrides for ACC')
            self._addOverrides(aam_info)

        return root

    def main(self):
        if not os.path.exists(self.env['pkg_path']):
            raise ProcessorError('The specified package does not exist: {}'.format(self.env['pkg_path']))

        option_xml_path = os.path.join(self.env['pkg_path'], 'Contents', 'Resources', 'optionXML.xml')
        option_xml = ElementTree.parse(option_xml_path)
        root = option_xml.getroot()

        if self.env.get('suppress_ccda', False):
            modified_root = self._suppressCcda(root)
            modified_root = self._addPanelMasking(modified_root)

            self._removeASUPackages()

            with open(option_xml_path, 'wb') as fd:
                fd.write(ElementTree.tostring(modified_root))

            self.output('OptionXML modified')


if __name__ == "__main__":
    processor = CreativeCloudBuildModifier()
    processor.execute_shell()
