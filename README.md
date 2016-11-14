# ccp-recipes

Autopkg recipes for Creative Cloud Packager workflows

## Overview

These processors and recipes may be used to automate the creation of Adobe Creative Cloud Packager packages.

## Getting Started

__Prerequisites:__

* [autopkg](https://github.com/autopkg/autopkg) 
* Adobe Creative Cloud Packager for [macOS](https://www.adobe.com/go/ccp_installer_osx) *Requires Creative Cloud Sign-In*
* If you haven't yet run the Creative Cloud Packager, you must do this manually at least once to establish which
  account/organization you will be using to create further packages.
* This recipe repo must be added to autopkg.

### Creating the overrides ###

As a rule, this repository does not contain recipes for each individual product, because each organization will require
different things.

As an example, we will be creating an override recipe for Photoshop CC 2017.

At the terminal, run:

        $ autopkg make-override -n PhotoshopCC2017 CreativeCloudApp.pkg.recipe 

autopkg will create an override file in your overrides dir. Edit the resulting file with a text editor of your choice.

The minimum amount of information you need to put in the override is:

- **Your organization name**: which is displayed on the top left of the enterprise dashboard or 'manage your team' dashboard.
- **A product id**: for the product you want to package. This is a 4 letter code which you can find by running the `listfeed.py` script in this repo.
- **A base version and/or product version**: some products have a base version which is 'updateable', and some can only be replaced entirely
 by specifying ONLY the version. If BaseVersion is not available, specify the VERSION only.
 
For our example, Photoshop CC 2017, I ran the `listfeed.py` and found this in the output:
    
    SAP Code: PHSP
        <...lines omitted...>     
        Photoshop CC (2017)                                         	BaseVersion: 18.0          	Version: 18.0 

I will use `PHSP` as the product id, and i will specify `18.0` for `BASE_VERSION`.
There is a special value for `VERSION` which is 'latest'. This means the latest update for the specified base version will always be used.

Now run your override recipe and you should see CCP download and build the package!

## Processor Reference

### CreativeCloudFeed

#### Description

Scrapes the product feed and returns product info based on your selected
version criteria.

#### Input Variables
- **product_id:**
    - **default:** None
    - **required:** True
    - **description:** The product SAP code, which can be found by running the `listfeed.py` in this repo.
    
- **base_version:**
    - **default:** None
    - **required:** False
    - **description:** The base product version. *NOTE:* some packages do not have a base version.
    
- **version:**
    - **default:** "latest"
    - **required:** False
    - **description:** Either 'latest' or a specific product version. 
        Specifying 'latest' returns the highest version available for the specified `base_version`
    
- **channels:**
    - **default:** "ccm,sti"
    - **required:** False
    - **description:** The update feed channel(s), comma separated. Typically you should not need to change this.
      
- **platforms:**
    - **default:** "osx10,osx10-64"
    - **required:** False
    - **description:** The deployment platform(s), comma separated. Valid values are `osx10`, `osx10-64` (TODO) windows platforms.
   
#### Output Variables
- **product_info_url:**
    - **description:** The generic product landing page.
    
- **base_version:**
    - **description:** The base product version that was selected based on your criteria.

- **version:**
    - **description:** The product version that was selected based on your criteria.
   
- **display_name:**
    - **description:** The display name of the product, as in the feed eg. "Photoshop CC (2017)".

- **minimum_os_version:**
    - **description:** The minimum OS version required to install the product.


### CreativeCloudPackager

#### Description

Takes information about package(s) and your license information, and builds
a package using Creative Cloud Packager.

#### Input Variables

#### Output Variables



