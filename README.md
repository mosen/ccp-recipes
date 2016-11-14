# ccp-recipes

Autopkg recipes for Creative Cloud Packager workflows

## Overview

These processors and recipes may be used to automate the creation of Adobe Creative Cloud Packager packages.

## Getting Started

__Prerequisites:__

* [autopkg](https://github.com/autopkg/autopkg) 
* Adobe Creative Cloud Packager [macOS](https://www.adobe.com/go/ccp_installer_osx) *Requires Creative Cloud Sign-In*
* If you haven't yet run the Creative Cloud Packager, you must do this manually at least once to establish which
  account/organization you will be using to create further packages.
* This recipe repo must be added to autopkg.

### Creating the overrides ###

As a rule, this repository does not contain recipes for each individual product, because each organization will require
different things.

As an example, we will be creating an override recipe for Photoshop CC 2017.

At the terminal, run:

        $ autopkg make-override -n PhotoshopCC2017 CreativeCloudApp.pkg.recipe 


## Processor Reference

### CreativeCloudFeed

#### Description

Scrapes the product feed and returns product info based on your selected
version criteria.

#### Input Variables

#### Output Variables


### CreativeCloudPackager

#### Description

Takes information about package(s) and your license information, and builds
a package using Creative Cloud Packager.

#### Input Variables

#### Output Variables



