# shellcheck shell=bash
# shellcheck disable=SC2154 # skip_archive_and_report, pipeline_pid, workspace_dir are set by run_pipeline.sh
# Function definitions for run_pipeline.sh. Sourced, not executed.

# shellcheck source=SCRIPTDIR/env.sh
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

process_request() {
    # The hash is created before the config deliberately: the reporting path
    # always reads hash.txt, so it must exist even when config creation fails.
    "$UV" sync --frozen &&
    "$UV" run --frozen python scripts/hash.py --run-id "$RUN_ID" --hash-file "$HASH_FILENAME" &&
    "$UV" run --frozen python scripts/create_config_file.py --config "$CONFIG_FILENAME" --issue-id "$ISSUE_NUMBER" &&
    PYTHONPATH=src OMP_NUM_THREADS="$N_THREADS" NETCDF_OUTPUT_FILETYPE="$NETCDF_FORMAT" \
        "$UV" run --frozen python src/processing/process_request.py --config "$CONFIG_FILENAME" \
            --workspace "$(pwd)" --extpar-raw-data "$EXTPAR_INPUT_DATA" --logfile "$LOG_FILENAME"
}

# Waits for a free slot among $N_SLOTS.
# For a request, must run after the caller applied the "submitted" label.
acquire_slot() {
    mkdir -p "$SLOTS_DIR"
    while :; do
        for slot in $(seq 0 $((N_SLOTS - 1))); do
            exec {lock_fd}>"$SLOTS_DIR/slot-$slot.lock"
            if flock -n "$lock_fd"; then
                return 0
            fi
            exec {lock_fd}>&-
        done
        sleep 10
    done
}

# shellcheck disable=SC2329 # invoked indirectly via the EXIT trap
cleanup_workspace() {
    cd /
    if [ -n "$workspace_dir" ] && [ "$workspace_dir" != "/" ]; then
        rm -rf -- "$workspace_dir"
    fi
}

archive_and_report() {
    local flag="$1" # '--success', '--failure', or '--aborted'
    local status=0
    local logs_flag=()

    if ! "$UV" run --frozen python scripts/archive_output.py --config "$CONFIG_FILENAME" --workspace "$workspace_dir" \
        --destination "$PUBLIC_OUTPUT_DATA_PATH" --logfile "$LOG_FILENAME" --hash-file "$HASH_FILENAME"; then
        status=1
        logs_flag=('--no-logs')

        # Only a successful run needs its outcome rewritten: its download
        # link would be dead. A failure or an abort stays reported as such.
        if [ "$flag" = '--success' ]; then
            flag='--publish-failure'
        fi
    fi

    "$UV" run --frozen python scripts/report.py --config "$CONFIG_FILENAME" --hash-file "$HASH_FILENAME" \
        --issue-id "$ISSUE_NUMBER" ${COMMENT_NOTE:+--note "$COMMENT_NOTE"} "${logs_flag[@]}" "$flag" || status=1

    return "$status"
}

finish() {
    if [ "$skip_archive_and_report" = true ]; then
        return 0
    fi
    archive_and_report "$1"
}

# The pipeline is not running yet when the signal arrives during the slot wait.
# shellcheck disable=SC2329 # invoked indirectly via the signal trap
on_terminate() {
    if [ -n "$pipeline_pid" ]; then
        kill -TERM -"$pipeline_pid" 2>/dev/null
        wait "$pipeline_pid" 2>/dev/null
    fi
    finish '--aborted'
    exit 143
}
