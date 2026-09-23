# shellcheck shell=bash
# Sourced by process_request.sh and run_testsuite_request.sh for its
# run_pipeline() function; archiving and reporting are left to the caller.
#
# Required environment variables:
#   ISSUE_ID          number of the GitHub issue the request was submitted in
#   RUN_ID            unique-ish value hashed into the download path
#   GITHUB_AUTH_TOKEN token used to fetch the issue body
#
# Run from a checkout of this repo, with uv installed at ~/.local/bin/uv.

# shellcheck source=scripts/env.sh
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

run_pipeline() {
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
