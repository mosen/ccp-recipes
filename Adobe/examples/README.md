# Examples #

This directory contains example overrides for Adobe products.
You can copy these to your RecipeOverrides directory to get started.

You can perform some basic testing by overriding these overrides by
supplying the required `ORG_NAME` variable on the command line eg:

    $ autopkg run -k ORG_NAME="my org" ./AcrobatDC.pkg

*WARNING:* There is no guarantee that this list of recipes is complete.

## Currently Failing ##

- Experience Design
- Lightroom minor version will be incorrect due to patches not detected (RIBS).
- Preview CC never creates an Uninstall pkg
- Gaming SDK version does not include x.x.y version


### JSS ###

- No SS Icons
- No SS Description
- Camera Raw Version Smart Group does not match EA version.
- Acrobat DC Smart Group Version does not match Installed Application version.
- Version string comparison might end up scoping computers for a downgrade if two package smartgroups exist.


