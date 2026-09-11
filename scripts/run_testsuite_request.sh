#!/usr/bin/env bash
set -uo pipefail

# Runs the same extraction pipeline as process_request.sh, but without
# archiving, publishing or relabeling - used by .github/workflows/testsuite.yml.

# shellcheck source=scripts/run_pipeline.sh
source "$(dirname "${BASH_SOURCE[0]}")/run_pipeline.sh"

run_pipeline
