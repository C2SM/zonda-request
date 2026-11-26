#!/usr/bin/env bash
set -uo pipefail

# Detached entrypoint launched over ssh by the GitHub workflows. No GitHub-side
# timeout applies once the launching job exits, so it enforces its own 24h one.
#
# Usage: run_pipeline.sh [--skip-archive-and-report] [--keep-workspace]
#   --skip-archive-and-report  skip archiving and reporting
#   --keep-workspace           keep the workspace after the run
#
# No `set -e`: the failure branch must report even when a command in it fails.
#
# Required environment variables:
#   ISSUE_NUMBER             number of the GitHub issue the request was submitted in
#   RUN_ID                   unique-ish value hashed into the download path
#   PUBLIC_OUTPUT_DATA_PATH  public directory where the output data is moved (not required with --skip-archive-and-report)
#
# Optional environment variables:
#   COMMENT_NOTE  Markdown note put on top of the report comment
#
# GitHub is accessed as the Zonda-Bot App, whose private key is expected at
# ~/.config/zonda/bot.pem. Run from a checkout of this repo, with uv installed
# at ~/.local/bin/uv.

skip_archive_and_report=false
keep_workspace=false
for arg in "$@"; do
    case "$arg" in
        --skip-archive-and-report) skip_archive_and_report=true ;;
        --keep-workspace) keep_workspace=true ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

# shellcheck source=SCRIPTDIR/pipeline_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/pipeline_functions.sh"
export -f process_request

workspace_dir="$(pwd)"
if [ "$keep_workspace" = false ]; then
    trap cleanup_workspace EXIT
fi

pipeline_pid=''
trap on_terminate TERM HUP INT

acquire_slot

# setsid puts the whole subtree in its own process group, killable as a unit.
# The slot descriptor is closed so no process outliving the pipeline holds it.
setsid timeout 24h bash -c process_request {lock_fd}>&- &
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
