#!/usr/bin/env bash
# Find out your Adobe organization name by scraping the PDApp log

output=$(mktemp)
grep 'OrgDetails return status is (0) server-response' ~/Library/Logs/PDApp.log | tail -n 1 | cut -d\( -f3 | cut -d\) -f1 |plutil -convert xml1 - -o - > "${output}"
/usr/libexec/PlistBuddy -c 'Print 0:orgName' "${output}"
