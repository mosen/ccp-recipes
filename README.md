# ccp-recipes

AutoPkg recipes for Creative Cloud Packager workflows

## Overview

These processors and recipes may be used to automate the creation of Adobe Creative Cloud Packager (CCP) packages, using Adobe's provided [automation](https://helpx.adobe.com/creative-cloud/packager/ccp-automation.html) support. Currently there are three flavors of `CreativeCloudApp` recipes provided:

#### pkg

Uses CCP to build a package saved to disk, exactly as one would using the CCP GUI application.

#### munki

Use the pkg recipe, wrap both the installer and uninstaller in DMGs, and import these to a Munki repo.

#### jss

Use the pkg recipe, and use the [JSSImporter](https://github.com/sheagcraig/JSSImporter) processor to import the install & uninstall packages into a Jamf Pro instance, with the required policies created.

## Getting Started

### Prerequisites

* [AutoPkg](https://autopkg.github.io/autopkg/)
* [Adobe Creative Cloud Packager (CCP) for macOS](https://www.adobe.com/go/ccp_installer_osx)
* An Adobe ID which is able to sign into either the [Teams](https://adminconsole.adobe.com/team) or [Enterprise](https://adminconsole.adobe.com/enterprise) dashboards and has the ability to build packages (for Enterprise this is at least the [Deployment Admin](https://helpx.adobe.com/enterprise/help/admin-roles.html) role)
* You must run CCP once manually in order to sign in as the account/organization you will be using to create further packages.
* This recipe repo must be added to AutoPkg.
* There must be no other Adobe CC applications or the Creative Cloud application installed on the machine building packages.

### Verifying your login

First log into the CCP with your username and verify that you're able to select the appropriate organization type (Teams or Enterprise) and build a package. If your Adobe ID is part of several organizations, make sure to select the one you want to be associated with the AutoPkg-built packages.

### Determining your organization name

The CCP automation support requires us to specify the actual full name of the organization to which the user belongs as part of the initial authentication to build packages. There is a script in this repo, `whats_my_org.sh`, which will attempt to scrape the organization name from the most recent login from the CCP application logs. If this fails, you can determine the organization name by looking in the upper-left in the [Teams](https://adminconsole.adobe.com/team) dashboard or the upper-right in the [Enterprise](https://adminconsole.adobe.com/enterprise) dashboard.

### Creating the overrides

As a rule, this repository does not contain recipes for each individual product, because each organization will require different things.
There are some examples provided however.

As an example, we will be creating an override recipe for Photoshop CC 2017.

In Terminal, run:

    autopkg make-override -n PhotoshopCC2017.pkg CreativeCloudApp.pkg

AutoPkg will create an override file in your RecipeOverrides folder. Edit the resulting file with a text editor of your choice.

The minimum amount of information you need to put in the override is:

- **Your organization name**: The name described above in 'Determining your organization name'

- **An application SAP code**: This is a 3-4 letter code which you can find by running the `listfeed.py` script in this repo. Every application and any related update has an SAP code.

- **A base version**: The base version defines the major version for a given application. The base version and the SAP code, together, uniquely identify any Adobe application.

    For the example of Photoshop CC 2017, running `listfeed.py` currently shows this in the output:

    ```
    SAP Code: PHSP
        <...lines omitted...>
		Photoshop CC (2015.5)       BaseVersion: 17.0       Version: 17.0
		Photoshop CC (2015.5)       BaseVersion: 17.0       Version: 17.0.1
		Photoshop CC (2015.5)       BaseVersion: 17.0       Version: 17.0.2
		Photoshop CC (2017)         BaseVersion: 18.0       Version: 18.0
		Photoshop CC (2017)         BaseVersion: 18.0       Version: 18.0.1
		Photoshop CC (2017)         BaseVersion: 18.0       Version: 18.1
        Photoshop CC (2017)			BaseVersion: 18.0		Version: 18.1.1
    ```
	
	Notice how `BaseVersion` changes only with a major marketing version number change. Some products use `BaseVersion` values like `18.0`, others like `14.0.0`. Take care to specify these values exactly as they appear in the output of `listfeed.py`.

### The ccpinfo Input

The only input is **ccpinfo** which describes how your package should be built and what is included.

You must have at least an **organizationName**, **sapCode** and some version information.

Example:

```plist
<key>ccpinfo</key>
<dict>
    <key>matchOSLanguage</key>
    <true/>
    <key>rumEnabled</key>
    <true/>
    <key>updatesEnabled</key>
    <false/>
    <key>appsPanelEnabled</key>
    <true/>
    <key>adminPrivilegesEnabled</key>
    <true/>
    <key>is64Bit</key>
    <true/>
    <key>organizationName</key>
    <string>ADMIN_PLEASE_CHANGE</string>
    <key>customerType</key>
    <string>team</string>
    <key>Language</key>
    <string>en_US</string>
    <key>Products</key>
    <array>
        <dict>
            <key>sapCode</key>
            <string>PHSP</string>
            <key>baseVersion</key>
            <string>18.0</string>
            <key>version</key>
            <string>latest</string>
        </dict>
    </array>
</dict>
```

Worth noting above is the `version` key, which is set here to `latest` (which is also the default if omitted). This can instead be set to the original base version if you'd like to build that version instead. Currently it does not seem like CCP will allow you to build any additional versions that may be "in between" the original release and the current latest.

As `Products` is an array, multiple applications or included updates may also be included in a single package. It's not recommended to _deploy_ multiple applications via a single package, however, so child recipes (i.e. `.munki`) that try to import packages with multiple products may have undefined behaviour. This capability exists for cases where one wants to build a "collection" package with multiple items. Currently, the support for building packages with multiple products is experimental.

The ccpinfo dict mirrors the format of the Creative Cloud Packager Automation XML file. 
The format of this file is described further in [This Adobe Article](https://helpx.adobe.com/creative-cloud/packager/ccp-automation.html)

## Troubleshooting

- Most CCP related errors will return a validation error, even though they may be completely unrelated to validation. 
    You should check the PDApp.log file to get to the real cause of the problem.

- You may see an error if there is a new CCP update pending. You will need to launch CCP manually to perform the update before you can proceed.

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
    
### CreativeCloudVersioner

#### Description

This processor raises an exception if not a HD or Acrobat Pro installer. The rationale is that the feed that the CreativeCloudFeed processor utilises only provides information on RIBS installer based titles base versions, (i.e. Prelude 9.0.0 & not 9.1.0).

It's hoped that in time more titles will move to HD installers, & then these recipes will work with minor changes (if any).

Once determined that the installer is either a HD or Acrobat Pro installer, the installers Application.json, .pimx & .zip is interogated to extract information detailed below.

#### Input Variables

#### Output Variables
 - **additional_pkginfo:**
     - **description:** Some pkginfo fields extracted from the Adobe metadata, for Munki bundle installs array & Jamf policies.
 
- **jss_inventory_name:**
    - **description:** Application title for jamf pro smart group criteria.

- **package_info_text:**
    - **description:** Text notes about which packages and updates are included in the pkg.

- **pkg_path:**
    - **description:** Path to the built bundle-style CCP installer pkg.

- **uninstaller_pkg_path:**
    - **description:** Path to the built bundle-style CCP uninstaller pkg.
