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

import sys
import string
import json
import urllib2
from tempfile import mkdtemp
from urllib import urlencode
from distutils.version import LooseVersion as LV
from xml.etree import ElementTree

# for debugging
from pprint import pprint

from autopkglib import Processor, ProcessorError

__all__ = ["CreativeCloudFeed"]

AAMEE_URL = 'https://prod-rel-ffc.oobesaas.adobe.com/adobe-ffc-external/aamee/v2/products/all'
BASE_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v4/products/all'
CDN_SECURE_URL = 'https://ccmdls.adobe.com'
UPDATE_DESC_URL = 'https://prod-rel-ffc.oobesaas.adobe.com/adobe-ffc-external/core/v1/update/description'
UPDATE_FEED_URL_MAC = 'https://swupmf.adobe.com/webfeed/oobe/aam20/mac/updaterfeed.xml'
HEADERS = {'User-Agent': 'Creative Cloud', 'x-adobe-app-id': 'AUSST_4_0'}

class CreativeCloudFeed(Processor):
    """Fetch information about product(s) from the Creative Cloud products feed."""
    description = __doc__
    input_variables = {
        "product_id": {
            "required": True,
            "description": "The product sap code",
        },
        "base_version": {
            "required": False,
            "description": "The base product version. Note that some packages do not have a base version.",
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
            "default": "ccm,sti",
            "description": "The update feed channel(s), comma separated. (default is the ccm and sti channels)",
        },
        "platforms": {
            "required": False,
            "default": "osx10,osx10-64",
            "description": "The deployment platform(s), comma separated. (default is osx10,osx10-64)",
        },
        "parse_proxy_xml": {
            "required": False,
            "default": False,
            "description": "Fetch and parse the product proxy XML which will set proxy_version in the output"
        },
        "fetch_release_notes": {
            "required": False,
            "default": False,
            "description": "Fetch the update release notes in the current language"
        },
        "fetch_icon": {
            "required": False,
            "default": False,
            "description": "Fetch the product icon to the cache directory"
        }
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
        },
        "release_notes": {
            "description": "The update release notes if fetch_release_notes was true, otherwise empty string"
        },
        "icon_path": {
            "description": "Path to the downloaded icon, if fetch_icon was true."
        },
        "proxy_version": {
            "description": "The product version listed in the proxy file, which usually has more digits"
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

    def desc_url(self, sapcode, version, platform, language):
        """Build the query for fetching an update description"""
        params = [
            ('name', sapcode),
            ('version', version),
            ('platform', platform),
            ('language', language)
        ]

        return UPDATE_DESC_URL + '?' + urlencode(params)

    def fetch_proxy_data(self, proxy_data_url):
        """Fetch the proxy data to get additional information about the product."""
        self.output('Fetching proxy data from {}'.format(proxy_data_url))
        req = urllib2.Request(proxy_data_url, headers=HEADERS)
        content = urllib2.urlopen(req).read()

        proxy_data = ElementTree.fromstring(content)
        return proxy_data

    def fetch_manifest(self, manifest_url):
        """Fetch the manifest.xml at manifest_url which contains asset download and proxy data information.
        Not all products have a proxy_data element

        :returns A tuple of (manifest, proxy) ElementTree objects
        """
        self.output('Fetching manifest.xml from {}'.format(manifest_url))
        req = urllib2.Request(manifest_url, headers=HEADERS)
        content = urllib2.urlopen(req).read()

        # Write out the manifest for debugging purposes
        with open('{}/manifest.xml'.format(self.env['RECIPE_CACHE_DIR']), 'w+') as fd:
            fd.write(content)

        manifest = ElementTree.fromstring(content)

        proxy_data_url_el = manifest.find('asset_list/asset/proxy_data')
        if proxy_data_url_el is None:
            raise ProcessorError('Could not find proxy data URL in manifest, aborting since your package requires it.')

        proxy_data = self.fetch_proxy_data(proxy_data_url_el.text)

        return manifest, proxy_data

    def fetch_release_notes(self, sapcode, version, platform, language):
        """Fetch the update description (release notes).

        This returns with an xml response in the form::
            <UpdateDescriptionResponse>
                <Language>en_US</Language>
                <UpdateDescription>...</UpdateDescription>
            </UpdateDescriptionResponse>

        It usually contains the specific bugs and features introduced in this version, not a general overview of the
        product.
        """
        url = self.desc_url(sapcode, version, platform, language)
        self.output('Fetching release notes from: {}'.format(url))
        req = urllib2.Request(url, headers=HEADERS)
        raw_data = urllib2.urlopen(req).read()

        return raw_data

    def fetch(self, channels, platforms):
        """Download the main feed"""
        url = self.feed_url(channels, platforms)
        self.output('Fetching from feed URL: {}'.format(url))

        req = urllib2.Request(url, headers=HEADERS)
        data = json.loads(urllib2.urlopen(req).read())

        return data

    def main(self):
        product_id = self.env.get('product_id')
        base_version = self.env.get('base_version')
        channels = string.split(self.env.get('channels'), ',')
        platforms = string.split(self.env.get('platforms'), ',')

        data = self.fetch(channels, platforms)

        channel_data = {}
        channel_cdn = {}
        for channel in data['channel']:
            if channel['name'] in channels:
                channel_data[channel['name']] = channel
                channel_cdn[channel['name']] = channel.get('cdn')

        product = {'version': '1.0'}
        for channel in data['channel']:
            if channel['name'] not in channels:
                continue

            for prod in channel['products']['product']:
                if prod['id'] != product_id:
                    continue

                if base_version and prod['platforms']['platform'][0]['languageSet'][0].get('baseVersion') != base_version:
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

        if 'platforms' not in product:
            raise ProcessorError('No package matched the SAP Code, Base version, and version combination you specified.')

        first_platform = {}
        for platform in product['platforms']['platform']:
            if platform['id'] in platforms:
                first_platform = platform
                break

        if first_platform.get('packageType') == 'RIBS':
            raise ProcessorError('This process does not support RIBS style packages.')

        self.output('Found matching product {}, version: {}'.format(product.get('displayName'), product.get('version')))

        if len(first_platform['systemCompatibility']['operatingSystem']['range']) > 0:
            compatibility_range = first_platform['systemCompatibility']['operatingSystem']['range'][0]
            # systemCompatibility currently has values like:
            # 10.x.0-
            # 10.10- (no minor version specified)
            # (empty array)
            self.env['minimum_os_version'] = compatibility_range.split('-')[0]
        else:
            # hacky workaround to avoid packager bailing when there is no minimum os version
            self.env['minimum_os_version'] = ''

        if 'urls' in first_platform['languageSet'][0] and 'manifestURL' in first_platform['languageSet'][0]['urls']:
            self.env['manifest_url'] = '{}{}'.format(
                channel_cdn['ccm']['secure'],
                first_platform['languageSet'][0]['urls'].get('manifestURL')
            )

            if self.env.get('parse_proxy_xml', False):
                self.output('Processor will fetch manifest and proxy xml')
                manifest, proxy = self.fetch_manifest(self.env['manifest_url'])
                product_version_el = proxy.find('InstallerProperties/Property[@name="ProductVersion"]')
                if product_version_el is None:
                    raise ProcessorError('Could not find ProductVersion in proxy data, aborting.')
                else:
                    self.output('Found version in proxy.xml: {}'.format(product_version_el.text))
                    self.env['proxy_version'] = product_version_el.text
            else:
                self.env['proxy_version'] = ''
        else:
            self.output('Did not find a manifest.xml in the product json data')

        if self.env.get('fetch_release_notes', False):
            self.output('Processor will fetch update release notes')
            desc = self.fetch_release_notes(product_id, product['version'], 'osx10-64', 'en_US')
            rn_etree = ElementTree.fromstring(desc)
            release_notes_el = rn_etree.find('UpdateDescription')

            if release_notes_el is None:
                raise ProcessorError('Could not find UpdateDescription in release notes')

            self.env['release_notes'] = release_notes_el.text
        else:
            self.env['release_notes'] = ''

        # output variable naming has been kept as close to pkginfo names as possible in order to feed munkiimport
        self.env['product_info_url'] = product.get('productInfoPage')
        self.env['version'] = product.get('version')
        self.env['display_name'] = product.get('displayName')

        if 'productIcons' in product:
            for icon in product['productIcons'].get('icon', []):
                if icon.get('size') == '96x96':
                    self.env['icon_url'] = icon.get('value')
                    break

        if self.env['icon_url'] is not None and self.env.get('fetch_icon', False):
            self.output('Fetching icon from {}'.format(self.env['icon_url']))
            req = urllib2.Request(self.env['icon_url'], headers=HEADERS)
            content = urllib2.urlopen(req).read()

            with open('{}/Icon.png'.format(self.env['RECIPE_CACHE_DIR']), 'w+') as fd:
                fd.write(content)

            self.env['icon_path'] = '{}/Icon.png'.format(self.env['RECIPE_CACHE_DIR'])
        else:
            self.env['icon_path'] = ''

if __name__ == "__main__":
    processor = CreativeCloudFeed()
    processor.execute_shell()
