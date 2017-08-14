# Examples

This directory contains some example overrides. Since it's possible these may drift over time, these should be considered only as illustrative - creating overrides should always be done using `autopkg make-override --name <override name> <recipe name>`

### Known issues in JSS recipes

- No SS Icons
- No SS Description
- Camera Raw Version Smart Group does not match EA version.
- Acrobat DC Smart Group Version does not match Installed Application version.
- Version string comparison might end up scoping computers for a downgrade if two package smartgroups exist.
- Error in local.jss.Adobe.IllustratorCC: Processor: JSSImporter: Error: Central directory offset would require ZIP64 extensions
