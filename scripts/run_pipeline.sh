# shellcheck shell=bash
# Shared by process_request.sh and run_testsuite_request.sh - not
# executable on its own, meant to be `source`d for its run_pipeline()
# function. Fetches the request JSON from the issue and runs the
# extraction. Does not archive, publish or report anything; callers
# decide what to do with the result.
#
# Required environment variables:
#   ISSUE_ID          number of the GitHub issue the request was submitted in
#   RUN_ID            unique-ish value hashed into the download path
#   GITHUB_AUTH_TOKEN token used to fetch the issue body
#
# Expects to be run from a directory that already contains this repo's
# checkout (src/, scripts/, pyproject.toml, uv.lock), and that uv is
# already installed for this account (~/.local/bin/uv) - non-interactive
# ssh sessions do not source ~/.bashrc, so it will not be on PATH.

set -a
# shellcheck source=scripts/env.sh
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
set +a

run_pipeline() {
    uv="$HOME/.local/bin/uv"

    # The hash is created before the config, deliberately: the reporting
    # path always reads hash.txt, so it must exist even when config
    # creation fails.
    "$uv" sync --frozen &&
    python3 scripts/hash.py --build-id "$RUN_ID" --hash-file "$hash_filename" &&
    python3 scripts/create_config_file.py --config "$config_filename" \
        --auth-token "$GITHUB_AUTH_TOKEN" --issue-id-file <(printf '%s' "$ISSUE_ID") &&
    PYTHONPATH=src OMP_NUM_THREADS="$n_threads" NETCDF_OUTPUT_FILETYPE="$netcdf_format" \
        python3 src/processing/process_request.py --config "$config_filename" \
            --workspace "$(pwd)" --extpar-raw-data "$extpar_input_data" --logfile "$log_filename"
}
