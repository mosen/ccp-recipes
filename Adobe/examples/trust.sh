#!/usr/bin/env bash
# Update trust information for example overrides
AUTOPKG=/usr/local/bin/autopkg
RECIPES=*.recipe

for r in ${RECIPES}; do
    echo Updating trust information for ./${r}
    ${AUTOPKG} update-trust-info ./${r}
done

