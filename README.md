# ccp-recipes

AutoPkg recipes for Creative Cloud Packager workflows

## Overview

These processors and recipes may be used to automate the creation of Adobe Creative Cloud Packager (CCP) packages, using Adobe's provided [automation](https://helpx.adobe.com/enterprise/package/help/ccp-automation.html) support. Currently there are three flavors of `CreativeCloudApp` recipes provided:

### pkg

Uses CCP to build a package saved to disk, exactly as one would using the CCP GUI application.

### munki

Use the pkg recipe, create DMGs from both the installers and uninstallers, and import these to a Munki repo.

### jss

Use the pkg recipe, and use the [JSSImporter](https://github.com/sheagcraig/JSSImporter) processor to import the install & uninstall packages into a Jamf Pro instance, with the required policies created.

## Getting Started

### Prerequisites

* [AutoPkg](https://autopkg.github.io/autopkg/)
* [Adobe Creative Cloud Packager (CCP) for macOS](https://www.adobe.com/go/ccp_installer_osx)
* An Adobe ID which is able to sign into either the [Teams](https://adminconsole.adobe.com/team) or [Enterprise](https://adminconsole.adobe.com/enterprise) dashboards and has the ability to build packages (for Enterprise this is at least the [Deployment Admin](https://helpx.adobe.com/enterprise/help/admin-roles.html) role)
* You must run CCP once manually in order to sign in as the account/organization you will be using to create further packages.
* This recipe repo must be added to AutoPkg
* There must be no other Adobe CC applications or the Creative Cloud application installed on the machine building packages

### Verifying your login

First log into the CCP with your username and verify that you're able to select the appropriate organization type (Teams or Enterprise) and build a package. If your Adobe ID is part of several organizations, make sure to select the one you want to be associated with the AutoPkg-built packages.

### Determining your organization name

The CCP automation support requires us to specify the actual full name of the organization to which the user belongs as part of the initial authentication to build packages. There is a script in this repo, `whats_my_org.sh`, which will attempt to scrape the organization name from the most recent login from the CCP application logs. If this fails, you can determine the organization name by looking in the upper-left in the [Teams](https://adminconsole.adobe.com/team) dashboard or the upper-right in the [Enterprise](https://adminconsole.adobe.com/enterprise) dashboard.

As stated in the prerequisites, your user must have sufficient privileges to build packages. 

### Creating the overrides

This repository does not contain separate recipes for each individual CC application, but instead provides a generic `CreativeCloudApp` recipe with `pkg`, `munki` and `jss` versions, which are meant to be overridden with specific package configurations. Typically one would create an override per application. There are a few [examples](/Adobe/examples) provided.

As a simple example: creating our own Photoshop CC 2017 package by overriding `CreativeCloudApp.pkg`:

```
autopkg make-override --name PhotoshopCC2017.pkg CreativeCloudApp.pkg
```

The minimum amount of information you need to put in the override is:

- **Your organization name**: The name described above in [Determining your organization name](#determining-your-organization-name)

- **An application SAP code**: This is a 3-4 letter code which you can find by running the `list_ccp_feed` script in this repo. Every application and any related update has an SAP code.

- **A base version**: The base version defines the major version for a given application. The base version and the SAP code, together, uniquely identify any Adobe application.

    For the example of Photoshop CC 2017, running `list_ccp_feed` currently shows this in the output:

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
	
	Notice how `BaseVersion` changes only with a major marketing version number change. Some products use `BaseVersion` values like `18.0`, others like `14.0.0`. Take care to specify these values exactly as they appear in the output of `list_ccp_feed`.

### The ccpinfo Input

The only input is **ccpinfo** which describes how your package should be built and what is included. The names of items in the `ccpinfo` dict mirrors those expected by the Creative Cloud Packager Automation XML file. The format of this file is described further in [This Adobe Article](https://helpx.adobe.com/enterprise/package/help/ccp-automation.html), but everything you would need to set is described below.

You must have at least an `organizationName`, and a `Products` which describes specific version information.

Example for a Photoshop CC 2017 package:

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
    <key>organizationName</key>
    <string>ADMIN_PLEASE_CHANGE</string>

    <!-- customerType can be either 'enterprise' or 'team' -->
    <key>customerType</key>
    <string>enterprise</string>
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

Worth noting above is the `version` key, which is set here to `latest` (which is also the default if omitted). This can instead be set to the original base version if you'd like to build that version instead. Currently it does not seem like CCP will allow you to build any additional versions that may be "in between" the original release and the current latest. The `baseVersion` defined here was derived from the `list_ccp_feed` script demonstrated above.

As `Products` is an array, multiple applications or included updates may also be included in a single package. It's not recommended to _deploy_ multiple applications via a single package, however, so child recipes (i.e. `.munki`) that try to import packages with multiple products may have undefined behaviour. This capability exists for cases where one wants to build a "collection" package with multiple items.

**Note:** Currently, the support for building packages with multiple products is experimental.

#### Serialized and device-licensed packages

To build serialized or device-licensed packages, set either the `serialNumber` or `devicePoolName` keys, respectively. If neither of these are present, a Named-licensed package will be built.

For example, to build a serialized package, you would just add `serialNumber` to the other items in the `ccpinfo` dict:

```plist
<key>ccpinfo</key>
<dict>
    < !-- other ccpinfo items here -->
    <key>serialNumber</key>
    <string>123456781234567812345678</string>
</dict>
```

Similarly, for a device-licensed package for a license pool called 'Creative Cloud All Apps':

```plist
<key>ccpinfo</key>
<dict>
    < !-- other ccpinfo items here -->
    <key>devicePoolName</key>
    <string>Creative Cloud All Apps</string>
</dict>
```

#### Case-sensitivity

`organizationName` and `devicePoolName`, and any other keys used for the `ccpinfo` dictionary are case-sensitive, and should match what you see in the CCP user interface.

## Package matching and `--check`

The `CreativeCloudPackager` processor used by these recipes records the output that was given to it and stores it alongside the recipe. This allows subsequent runs of the same recipe to avoid re-building the entire package again.

Doing an AutoPkg run using `autopkg run --check` performs the check phase after the packaging phase, making it trivial to run a list of CCP app recipes and quick see if there is anything new available, e.g.:

```shell
$ autopkg run --recipe-list lists/adobe_cc.txt --check
Processing AdobeAfterEffectsCC2017.munki...
Processing AdobeAnimateCC2017.munki...
Processing AdobeAuditionCC2017.munki...
Processing AdobeBridgeCC2017.munki...
Processing AdobeCameraRawCC.munki...
Processing AdobeDreamweaverCC2017.munki...
Processing AdobeExperienceDesignCCBeta.munki...
Processing AdobeIllustratorCC2017.munki...
Processing AdobeInDesignCC2017.munki...
Processing AdobeMediaEncoderCC2017.munki...
Processing AdobePhotoshopCC2017.munki...
Processing AdobePreludeCC2017.munki...
Processing AdobePremiereProCC2017.munki...

Nothing downloaded, packaged or imported.
```

## Other Application Updates (Camera Raw, etc.)

Multiple Adobe applications include additional updates offered alongside the main application, such as Camera Raw (multiple apps), or Preview (Photoshop). CCP is able to build standalone packages for these separate update packages (known internally within Adobe packaging tools as "STI" updates). The packages will typcially seem very large given the size of the actual update, simply because every package includes hundreds of megabytes of installer engine code and the Creative Cloud desktop app.

It's possible to build CCP packages containing _only_ update items such these. For Munki items, one could manually add `update_for` to the override's `pkginfo` so that the update will apply to a subset of base applications. There's currently no automation tools provided here to help one automatically figure out the mapping of updates to base applications.

Given the above, it's important to note at least two other differences with packages containing these update items.

### Missing Uninstaller Packages

As of around May 2017, CCP seems to no longer generate uninstaller packages for these. If one is creating Munki recipe overrides for these, the `CreativeCloudAppNoUninstall.munki` recipe is provided for this case.

### Installs keys for Munki recipes

For Munki recipes, when the MunkiImporter processor runs, it will likely not be able to generate a usable `installs` key for these pkginfos, so something must be added to them by hand. For the specific example of Camera Raw, here are two suggestions:

* Use the `.pimx` metadata file unique to this version of Camera Raw. Note this is "pinned" to this version and will not be present if ACR is ever updated to a newer version. This makes `.pimx` files useful if you _prefer_ that Munki manage the version specifically, but not desirable if you ever expect the system to have ACR updated out-of-band from your management tools.

```plist
<key>installs</key>
<array>
    <dict>
        <key>path</key>
        <string>/Library/Application Support/Adobe/Installers/uninstallXml/ACR_9_8_AdobeCameraRaw8.0All_9.8.0.63.pimx</string>
        <key>type</key>
        <string>file</string>
    </dict>
</array>
```

* Camera Raw ships a standard macOS bundle which can be used by Munki:

```plist
<key>installs</key>
<array>
    <dict>
        <key>CFBundleShortVersionString</key>
        <string>9.10 (739)</string>
        <key>CFBundleVersion</key>
        <string>9.10f739</string>
        <key>path</key>
        <string>/Library/Application Support/Adobe/Plug-Ins/CC/File Formats/Camera Raw.plugin</string>
        <key>type</key>
        <string>bundle</string>
        <key>version_comparison_key</key>
        <string>CFBundleShortVersionString</string>
    </dict>
</array>
```

Important to note here, however: historically, Camera Raw's version increments often include a third component (i.e. there could be something like a `9.10.1` after the version above). Both `CFBundleShortVersionString`'s added space and `CFBundleVersion`'s added alpha character pose a problem for Munki's version comparison operator (largely based on Python's distutils's `LooseVersion`). If, in a new release of Camera Raw, the number of components in the version number goes from 2 to 3 or vice versa, Munki will not compare the versions "accurately" due to these extra added components. See [this versioning-related Munki issue](https://github.com/munki/munki/pull/681)

## Known issues

### Non-HyperDrive installers

`list_ccp_feed` will include older versions of some applications which predate Adobe's HyperDrive format - these will show `N/A` beside `BaseVersion`. These application versions aren't compatible with these recipes, but all major CC apps are now releasing their current versions in HyperDrive format, except for Lightroom CC 2015 and Acrobat Pro. Acrobat Pro has special support written in these recipes' processors, and has example recipes provided in the `examples` folder.

### JSS Recipes

(Copied over from mosen's WIP on JSS recipes)

- No SS Icons
- No SS Description
- Camera Raw Version Smart Group does not match EA version.
- Acrobat DC Smart Group Version does not match Installed Application version.
- Version string comparison might end up scoping computers for a downgrade if two package smartgroups exist.
- Error in local.jss.Adobe.IllustratorCC: Processor: JSSImporter: Error: Central directory offset would require ZIP64 extensions


## Troubleshooting

- Most CCP related errors will return a validation error, even though they may be completely unrelated to validation. You should check the PDApp.log file to get to the real cause of the problem.

- You may see an error if there is a new CCP update pending. You will need to launch CCP manually to perform the update before you can proceed.

- If you're building packages on a headless Mac, CCP will stall unless a Screen Sharing / ARD observe session is active. As a workaround, you can install a display dongle. [This one](https://www.amazon.com/dp/B00FLZXGJ6/), [recommended by Macminicolo](https://macminicolo.net/blog/files/an-hdmi-adapter-for-a-headless-mac-mini.html) has been confirmed to work with the Mac mini (Late 2012) for this purpose.

## Other links

* [Creative Cloud Desktop App release notes](https://helpx.adobe.com/creative-cloud/release-note/cc-release-notes.html)
