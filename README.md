# ccp-recipes

AutoPkg recipes for Creative Cloud Packager workflows

## Overview

These processors and recipes may be used to automate the creation of Adobe Creative Cloud Packager packages.
Based upon Adobes documentation for [Creative Cloud Packager Automation](https://helpx.adobe.com/creative-cloud/packager/ccp-automation.html)

## Getting Started

__Prerequisites:__

* [AutoPkg](https://autopkg.github.io/autopkg/)
* [Adobe Creative Cloud Packager (CCP) for macOS](https://www.adobe.com/go/ccp_installer_osx) *Requires Creative Cloud Sign-In*
* If you haven't yet run the Creative Cloud Packager, you must do this manually at least once to establish which account/organization you will be using to create further packages.
* This recipe repo must be added to AutoPkg.
* It is _strongly_ recommended to disable App Nap, as CCP has a tendency to sleep and stall downloads indefinitely if it is ever not the foreground application. This can be done globally (for the current user) using `defaults write NSGlobalDomain NSAppSleepDisabled -bool YES`. It does not seem possible to disable it selectively for the CCP application.

### Creating the overrides

As a rule, this repository does not contain recipes for each individual product, because each organization will require different things.

As an example, we will be creating an override recipe for Photoshop CC 2017.

In Terminal, run:

    autopkg make-override -n PhotoshopCC2017.pkg CreativeCloudApp.pkg.recipe

AutoPkg will create an override file in your RecipeOverrides folder. Edit the resulting file with a text editor of your choice.

The minimum amount of information you need to put in the override is:

- **Your organization name**: which is displayed on the top left of the enterprise dashboard or 'manage your team' dashboard.

- **A product id**: for the product you want to package. This is a 4 letter code which you can find by running the `listfeed.py` script in this repo.

- **A base version and/or product version**: some products have a base version which is 'updateable', and some can only be replaced entirely by specifying ONLY the version. If BaseVersion is not available, specify the VERSION only.

    For our example, Photoshop CC 2017, I ran the `listfeed.py` and found this in the output:

    ```
    SAP Code: PHSP
        <...lines omitted...>
        Photoshop CC (2017)                                         	BaseVersion: 18.0          	Version: 18.0
    ```

    I will use `PHSP` as the product id, and i will specify `18.0` for `BASE_VERSION`.

    There is a special value for `VERSION` which is `latest`. This means the latest update for the specified base version will always be used.

Now run your override recipe and you should see CCP download and build the package!

## Troubleshooting

- Most CCP related errors will return a validation error, even though they may be completely unrelated to validation. You should check the PDApp.log file to get to the real cause of the problem.

- You may see an error if there is a new CCP update pending. You will need to launch CCP manually to perform the update before you can proceed.

- CCP will quit immediately if a package with the same version already exists in the output folder. This processor should detect the existence of those files and skip packaging if this is the case.

## Processor Reference

### CreativeCloudFeed

#### Description

Scrapes the product feed and returns product info based on your selected version criteria.

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
    - **default:** `latest`
    - **required:** False
    - **description:** Either `latest` or a specific product version.
        Specifying `latest` returns the highest version available for the specified `base_version`

- **channels:**
    - **default:** `ccm,sti`
    - **required:** False
    - **description:** The update feed channel(s), comma separated. Typically you should not need to change this.

- **platforms:**
    - **default:** `osx10,osx10-64`
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
    - **description:** The display name of the product, as in the feed e.g. `Photoshop CC (2017)`.

- **minimum_os_version:**
    - **description:** The minimum OS version required to install the product.


### CreativeCloudPackager

#### Description

Takes information about package(s) and your license information, and builds a package using Creative Cloud Packager.

#### Input Variables
- **package_name:**
    - **default:**
    - **required:** True
    - **description:** The name of the output package. CCP will add `_Install` and `_Uninstall` suffixes.

- **license_type:**
    - **default:** (Taken from your CCP Preferences for the most recent login)
    - **required:** False
    - **description:** The license type, one of: `enterprise`, `team`. If this is omitted, CCP's preferences for
    the last logged-in user will be queried and that customer type used here.

- **organization_name:**
    - **default:** (None)
    - **required:** True
    - **description:** The organization name which must match your licensed organization. This can be obtained from either the Enterprise Dashboard (upper right), Team management dashboard (upper left), or by looking in `Contents/Resources/optionXML.xml` of a previously-built package, in the `OrganizationName` element.

- **serial_number:**
    - **default:** (None)
    - **required:** False
    - **description:** The serial number, if you are using serialized packages.  The serial number should expressed without punctuation, rather than the hyphenated format provided by Adobe (i.e. instead of `1111-2222-3333-4444-5555-6666`, use `111122223333444455556666`).

- **language:**
    - **default:** `en_US`
    - **required:** False
    - **description:** The language to build.

- **include_updates:**
    - **default:** True
    - **required:** False
    - **description:** Include all available ride-along updates (such as Camera RAW) to the package(s) specified.

- **rum_enabled:**
    - **default:** True
    - **required:** False
    - **description:** Include RUM in the package.

- **updates_enabled:**
    - **default:** False
    - **required:** False
    - **description:** Allow the end user to perform updates.

- **apps_panel_enabled:**
    - **default:** True
    - **required:** False
    - **description:** Allow the end user to see the Apps panel for app installation and removal.

- **admin_privileges_enabled:**
    - **default:** False
    - **required:** False
    - **description:** Allow the **Creative Cloud** desktop application to run in privileged mode. This allows users to perform installations without being a local administrator.

#### Output Variables
- **pkg_path:**
    - **description:** Path to the built bundle-style CCP installer pkg.

- **uninstaller_pkg_path:**
    - **description:** Path to the built bundle-style CCP uninstaller pkg.

- **package_info_text:**
    - **description:** Text notes about which packages and updates are included in the pkg.

- **ccp_version:**
    - **description:** Version of CCP tools used to build the package.
