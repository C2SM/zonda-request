#!/usr/bin/env bash
set -uo pipefail

# Detached entrypoint launched over ssh by the GitHub workflows. No GitHub-side
# timeout applies once the launching job exits, so it enforces its own 24h one.
#
# Usage: run_pipeline.sh [--testsuite] [--debug]
#   --testsuite  skip archiving and reporting
#   --debug      keep the workspace after the run
#
# No `set -e`: the failure branch must report even when a command in it fails.
#
# Required environment variables:
#   ISSUE_ID          number of the GitHub issue the request was submitted in
#   RUN_ID            unique-ish value hashed into the download path
#   GITHUB_AUTH_TOKEN token used to fetch the issue body
#
# Run from a checkout of this repo, with uv installed at ~/.local/bin/uv.

testsuite=false
debug=false
for arg in "$@"; do
    case "$arg" in
        --testsuite) testsuite=true ;;
        --debug) debug=true ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

# shellcheck source=scripts/pipeline_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/pipeline_functions.sh"
export -f extract

workspace_dir="$(pwd)"
if [ "$debug" = false ]; then
    trap cleanup_workspace EXIT
fi

pipeline_pid=''
trap on_terminate TERM HUP INT

acquire_slot

# setsid puts the whole subtree in its own process group, killable as a unit.
# The slot descriptor is closed so no process outliving the pipeline holds it.
setsid timeout 24h bash -c extract {lock_fd}>&- &
pipeline_pid=$!

wait "$pipeline_pid"
status=$?

if [ "$status" -eq 0 ]; then
    finish '--success'
    exit $?
elif [ "$status" -eq 124 ]; then
    finish '--aborted'
    exit 1
else
    finish '--failure'
    exit 1
fi
