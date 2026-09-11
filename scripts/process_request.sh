#!/usr/bin/env bash
set -uo pipefail

# The detached entrypoint launched over ssh by process_request.yml via
# `setsid nohup scripts/process_request.sh &`. Once the launching Actions
# job exits (seconds later), there is no GitHub-side timeout and no
# `if: always()` step, so this script enforces its own 24h timeout
# (matching the old Jenkins timeout) and cleans up its own workspace.
#
# Deliberately does not use `set -e`: the failure branch below has to run
# and report even when a command in it fails.
#
# Required environment variables: see run_pipeline.sh.

script_dir="$(dirname "${BASH_SOURCE[0]}")"
# shellcheck source=scripts/run_pipeline.sh
source "$script_dir/run_pipeline.sh"
export -f run_pipeline

readonly n_slots=6
slots_dir="$HOME/.zonda/slots"
mkdir -p "$slots_dir"

# Waits for a free slot among $n_slots, matching the 6-concurrent-build
# cap Jenkins used to enforce on this host. Cheap to do here - unlike in
# the launching workflow, which exits within seconds - because runs are
# now detached and no longer bound by any job timeout. This must happen
# after the caller has applied the "submitted" label, so a queued
# request still looks "in progress"; this script never touches labels
# itself before archive_and_report, so that ordering is automatic.
acquire_slot() {
    while :; do
        for slot in $(seq 0 $((n_slots - 1))); do
            exec {lock_fd}>"$slots_dir/slot-$slot.lock"
            if flock -n "$lock_fd"; then
                return 0
            fi
            exec {lock_fd}>&-
        done
        sleep 10
    done
}

workspace_dir="$(pwd)"
# shellcheck disable=SC2329 # invoked indirectly via the EXIT trap below
cleanup_workspace() {
    cd /
    if [ -n "$workspace_dir" ] && [ "$workspace_dir" != "/" ]; then
        rm -rf -- "$workspace_dir"
    fi
}
trap cleanup_workspace EXIT

archive_and_report() {
    local flag="$1" # '--success', '--failure', or '--aborted'
    local status=0

    if ! "$uv" run --frozen python scripts/archive_output.py --config "$config_filename" --workspace "$workspace_dir" \
        --destination "$https_public_root" --logfile "$log_filename" --hash-file "$hash_filename"; then
        status=1

        # Only a successful run needs its outcome rewritten, since its
        # download link would be dead. A failure or an abort stays reported
        # as such, even when the logfiles did not reach $https_public_root.
        if [ "$flag" = '--success' ]; then
            flag='--publish-failure'
        fi
    fi

    "$uv" run --frozen python scripts/report.py --config "$config_filename" --hash-file "$hash_filename" \
        --issue-id-file <(printf '%s' "$ISSUE_ID") "$flag" || status=1

    return "$status"
}

acquire_slot

# Run under setsid so the whole subtree (timeout, the pipeline, uv, the
# processing steps) lands in its own process group, killable as a unit
# below without depending on this script's own job control.
setsid timeout 24h bash -c run_pipeline &
pipeline_pid=$!

# shellcheck disable=SC2329 # invoked indirectly via the trap below
on_terminate() {
    kill -TERM -"$pipeline_pid" 2>/dev/null
    wait "$pipeline_pid" 2>/dev/null
    archive_and_report '--aborted'
    exit 143
}
trap on_terminate TERM HUP INT

wait "$pipeline_pid"
status=$?

if [ "$status" -eq 0 ]; then
    archive_and_report '--success'
    exit $?
elif [ "$status" -eq 124 ]; then
    archive_and_report '--aborted'
    exit 1
else
    archive_and_report '--failure'
    exit 1
fi
