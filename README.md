# ccp-recipes

AutoPkg recipes for Creative Cloud Packager workflows. 
This repo has now been moved to [autopkg/adobe-ccp-recipes](https://github.com/autopkg/adobe-ccp-recipes), 
so any further development will happen there.

Recipe identifiers have not changed, so if you were already tracking this repo with Git, 
one simple way to migrate your repo to the new remote location would be to go to your AutoPkg 
recipe repo dir (most likely `~/Library/AutoPkg/RecipeRepos/com.github.mosen.ccp-recipes`) and modify 
the `.git/config` to use the new repo location of https://github.com/autopkg/adobe-ccp-recipes.

## New behaviour with CCP v1.14.0.97 (March 2018)

In v1.14.0.97 the ability to specify a custom package by its exact version was broken (either intentionally
or unintentionally) by Adobe. The only remaining options for us are the base version or "latest" version of
the product.

The following changes were made as a result:

- If you specify version "latest", it will automatically include any updates to the main product and bundled
  products at the time you generate the package. This means that recipes are non-deterministic.
- If you don't specify a version you get the base version only.
- You may use "IncludeUpdates" in place of specifying a version to mean "include all updates at the time of
  packaging", this is the same as "latest".

  