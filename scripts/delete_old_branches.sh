#!/bin/bash

MAX_DAYS=${DAYS}
PATTERN="issue-*"
NOW=$(date +%s)
MAX_AGE=$((MAX_DAYS * 24 * 60 * 60))

# Get all branches matching the pattern
BRANCHES=$(git branch -r | grep "$PATTERN" | sed 's/origin\///')

for BRANCH in $BRANCHES; do
    # Get the last commit date of the branch
    LAST_COMMIT_DATE=$(git log -1 --format=%ct origin/$BRANCH)
    AGE=$((NOW - LAST_COMMIT_DATE))

    if [ $AGE -gt $MAX_AGE ]; then
        echo "Deleting branch $BRANCH"

        curl -X DELETE -H "Authorization: token $GITHUB_TOKEN" \
        "https://api.github.com/repos/${GITHUB_REPOSITORY}/git/refs/heads/$BRANCH"
    fi
done
