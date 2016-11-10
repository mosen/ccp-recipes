#!/usr/bin/env python

import json
import unicodedata
import urllib2
from urllib import urlencode

BASE_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v4/products/all'

def add_product(products, product):
    if product['id'] not in products:
        products[product['id']] = []

    products[product['id']].append(product)


def feed_url(channels, platforms):
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

def fetch(channels, platforms):
    """Fetch the feed contents."""
    url = feed_url(channels, platforms)
    print('Fetching from feed URL: {}'.format(url))

    req = urllib2.Request(url, headers={
        'User-Agent': 'Creative Cloud',
        'x-adobe-app-id': 'AUSST_4_0',
    })
    data = json.loads(urllib2.urlopen(req).read())

    return data

if __name__ == "__main__":
    data = fetch(['ccm', 'sti'], ['osx10', 'osx10-64'])
    products = {}
    for channel in data['channel']:
        for product in channel['products']['product']:
            add_product(products, product)

    for sapcode, productVersions in products.iteritems():
        print("SAP Code: {}".format(sapcode))

        for product in productVersions:
            base_version = product['platforms']['platform'][0]['languageSet'][0].get('baseVersion')
            if not base_version:
                base_version = "N/A"

            name = unicodedata.normalize("NFKD", product['displayName'])
            print("\t{0: <60}\tBaseVersion: {1: <14}\tVersion: {2: <14}".format(
                name,
                base_version,
                product['version']
            ))
        print("")
