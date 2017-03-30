#!/usr/bin/env bash
# Update trust information for example overrides
# If not placed in override dir, will not actually work.
AUTOPKG=/usr/local/bin/autopkg
RECIPES=*.recipe

for r in ${RECIPES}; do
    echo Updating trust information for ${r}
    ${AUTOPKG} update-trust-info ${r}
done

