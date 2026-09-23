# shellcheck shell=bash
# shellcheck disable=SC2154 # testsuite, pipeline_pid, workspace_dir are set by run_pipeline.sh
# Function definitions for run_pipeline.sh. Sourced, not executed.

# shellcheck source=scripts/env.sh
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

extract() {
    # The hash is created before the config deliberately: the reporting path
    # always reads hash.txt, so it must exist even when config creation fails.
    "$uv" sync --frozen &&
    "$uv" run --frozen python scripts/hash.py --run-id "$RUN_ID" --hash-file "$hash_filename" &&
    "$uv" run --frozen python scripts/create_config_file.py --config "$config_filename" \
        --auth-token "$GITHUB_AUTH_TOKEN" --issue-id-file <(printf '%s' "$ISSUE_ID") &&
    PYTHONPATH=src OMP_NUM_THREADS="$n_threads" NETCDF_OUTPUT_FILETYPE="$netcdf_format" \
        "$uv" run --frozen python src/processing/process_request.py --config "$config_filename" \
            --workspace "$(pwd)" --extpar-raw-data "$extpar_input_data" --logfile "$log_filename"
}

# Waits for a free slot among $n_slots.
# For a request, must run after the caller applied the "submitted" label.
acquire_slot() {
    mkdir -p "$slots_dir"
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

    if ! "$uv" run --frozen python scripts/archive_output.py --config "$config_filename" --workspace "$workspace_dir" \
        --destination "$https_public_root" --logfile "$log_filename" --hash-file "$hash_filename"; then
        status=1
        logs_flag=('--no-logs')

        # Only a successful run needs its outcome rewritten: its download
        # link would be dead. A failure or an abort stays reported as such.
        if [ "$flag" = '--success' ]; then
            flag='--publish-failure'
        fi
    fi

    "$uv" run --frozen python scripts/report.py --config "$config_filename" --hash-file "$hash_filename" \
        --issue-id-file <(printf '%s' "$ISSUE_ID") "${logs_flag[@]}" "$flag" || status=1

    return "$status"
}

# Testsuite runs are neither archived nor reported.
finish() {
    if [ "$testsuite" = true ]; then
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
