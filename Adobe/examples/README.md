# Examples #

This directory contains example overrides for Adobe products.
You can copy these to your RecipeOverrides directory to get started.

You can perform some basic testing by overriding these overrides by
supplying the required `ORG_NAME` variable on the command line eg:

    $ autopkg run -k ORG_NAME="my org" ./AcrobatDC.pkg

*WARNING:* There is no guarantee that this list of recipes is complete.

## Currently Failing ##

- Edge Code
- Experience Design
- Lightroom minor version will be incorrect due to patches not detected.
- Preview CC never creates an Uninstall pkg

