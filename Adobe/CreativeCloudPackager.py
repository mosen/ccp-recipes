#!/usr/bin/python
#
# Copyright 2016 Mosen
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

from autopkglib import Processor, ProcessorError

__all__ = ["CreativeCloudPackager"]

# https://helpx.adobe.com/creative-cloud/packager/ccp-automation.html

TEMPLATE_XML = """<CCPPackage>
  <CreatePackage>
    <packageName>${package_name}</packageName>
    <packagingJobId>12345</packagingJobId>
    <outputLocation>${output_location}</outputLocation>
    <is64Bit>true</is64Bit>
    <customerType>enterprise</customerType>
    <organizationName>Concordia University, Quebec</organizationName>
    <!-- ProductCategory should be left 'Custom' -->
    <ProductCategory>Custom</ProductCategory>
    <matchOSLanguage>true</matchOSLanguage>
	<IncludeUpdates>false</IncludeUpdates>
	<rumEnabled>true</rumEnabled>
	<updatesEnabled>false</updatesEnabled>
	<appsPanelEnabled>false</appsPanelEnabled>
	<adminPrivilegesEnabled>false</adminPrivilegesEnabled>
    <Language>
      <id>en_US</id>
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

class CreativeCloudPackager(Processor):
    """Create and execute a CCP automation file. The package output will always be the autopkg cache directory"""
    description = __doc__
    input_variables = {
        "package_name": {
            "required": True,
            "description": "The output package name"
        },
        "customer_type": {
            "required": True,
            "description": "The license type 'enterprise' or 'team'"
        },
        "organization_name": {
            "required": True,
            "description": "The organization name which must match your licensed organization."
        },
        "serial_number": {
            "required": False,
            "description": "The serial number, if you are using serialized packages."
        },
        "include_updates": {
            "required": False,
            "default": True,
            "description": "Include all available updates, defaults to true."
        },
        "language": {
            "required": True,
            "default": "en_US",
            "description": "The language to build, defaults to en_US."
        },
        "rum_enabled": {
            "required": False,
            "default": True,
            "description": "Include RUM in the package"
        },
        "updates_enabled": {
            "required": False,
            "default": True,
            "description": "Enable updates"
        },
        "apps_panel_enabled": {
            "required": False,
            "default": True,
            "description": "Enable access to the apps panel in the desktop application"
        },
        "admin_privileges_enabled": {
            "required": False,
            "default": False,
            "description": "Allow the desktop application to run in privileged mode, so that standard users may install apps."
        }
    }

    output_variables = {

    }