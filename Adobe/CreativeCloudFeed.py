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

import sys
import string
import json
import urllib2
from urllib import urlencode
from distutils.version import LooseVersion as LV

# for debugging
from pprint import pprint

from autopkglib import Processor, ProcessorError

__all__ = ["CreativeCloudFeed"]

BASE_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v4/products/all'

# Sap Codes can be seen at https://helpx.adobe.com/creative-cloud/packager/apps-deployed-without-their-base-versions.html

class CreativeCloudFeed(Processor):
    """Fetch information about product(s) from the Creative Cloud products feed."""
    description = __doc__
    input_variables = {
        "product_id": {
            "required": True,
            "description": "The product sap code",
        },
        "base_version": {
            "required": True,
            "description": "The base product version",
        },
        "version": {
            "required": False,
            "default": "latest",
            "description": ("Either 'latest' or a specific product version. "
                            "Currently only supports 'latest', which will ."
                            "return the highest version within this base "
                            "product."),
        },
        "channels": {
            "required": False,
            "default": "ccm",
            "description": "The update feed channel(s), comma separated. (default is ccm)",
        },
        "platforms": {
            "required": False,
            "default": "osx10,osx10-64",
            "desription": "The deployment platform(s), comma separated. (default is osx10,osx10-64)",
        },
    }

    output_variables = {
        "product_info_url": {
            "description": "Product main information URL"
        },
        "icon_url": {
            "description": "Icon download URL for the highest resolution available, normally 96x96."
        },
        "base_version": {
            "description": "The basic (major.minor) version"
        },
        "version": {
            "description": "The full length version"
        },
        "display_name": {
            "description": "The product full name and major version"
        },
        "manifest_url": {
            "description": "The URL to the product manifest"
        },
        "family": {
            "description": "The product family"
        },
        "minimum_os_version": {
            "description": "The minimum operating system version required to install this package"
        }
    }

    def feed_url(self, channels, platforms):
        """Build the GET query parameters for the product feed."""
        params = [
            ('payload', 'true'),
            ('productType', 'Desktop'),
            ('_type', 'json')
        ]
        for ch in channels:
            params.append(('channel', ch))

        for pl in platforms:
            params.append(('platform', pl))

        return BASE_URL + '?' + urlencode(params)

    def fetch(self, channels, platforms):
        url = self.feed_url(channels, platforms)
        self.output('Fetching from feed URL: {}'.format(url))

        req = urllib2.Request(url, headers={
            'User-Agent': 'Creative Cloud',
            'x-adobe-app-id': 'AUSST_4_0',
        })
        data = json.loads(urllib2.urlopen(req).read())

        return data

    def main(self):
        product_id = self.env.get('product_id')
        base_version = self.env.get('base_version')
        channels = string.split(self.env.get('channels'), ',')
        platforms = string.split(self.env.get('platforms'), ',')

        data = self.fetch(channels, platforms)

        channel_data = {}
        for channel in data['channel']:
            if channel['name'] in channels:
                channel_data[channel['name']] = channel

        product = {'version': '1.0'}
        for channel in data['channel']:
            if channel['name'] not in channels:
                continue

            for prod in channel['products']['product']:
                if prod['id'] != product_id:
                    continue

                if prod['platforms']['platform'][0]['languageSet'][0].get('baseVersion') != base_version:
                    continue

                if 'version' not in prod:
                    self.output('product has no version: {}'.format(prod['displayName']))
                    continue

                #  self.output('check if version: {} is greater than newest found product: {}'.format(prod['version'], product['version']))
                if self.env["version"] == "latest":
                    if LV(prod['version']) > LV(product['version']):
                        product = prod
                #  TODO: sanity check whether a specific version actually exists within the available products
                #        (may require refactoring this loop)
                else:
                    if prod['version'] == self.env["version"]:
                        product = prod
        
        first_platform = {}
        for platform in product['platforms']['platform']:
            if platform['id'] in platforms:
                first_platform = platform
                break

        if first_platform.get('packageType') == 'RIBS':
            raise ProcessorError('This process does not support RIBS style packages.')

        self.output('Found matching product {}, version: {}'.format(product.get('displayName'), product.get('version')))

        compatibility_range = first_platform['systemCompatibility']['operatingSystem']['range'][0]

        # output variable naming has been kept as close to pkginfo names as possible in order to feed munkiimport
        
        # TODO: sanity-check this "systemCompatibility range" value
        self.env['minimum_os_version'] = compatibility_range.split('-')[0]
        self.env['product_info_url'] = product.get('productInfoPage')
        self.env['version'] = product.get('version')
        self.env['display_name'] = product.get('displayName')

if __name__ == "__main__":
    processor = CreativeCloudFeed()
    processor.execute_shell()
