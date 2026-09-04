#!/usr/bin/env bash
set -uo pipefail

# Runs the same extraction pipeline as process_request.sh, but without
# archiving, publishing, commenting or relabeling - used by the CI
# testsuite (.github/workflows/testsuite.yml) to verify a fixed set of
# real-world requests still process successfully. Invoked over ssh, same
# environment variables as run_pipeline.sh.

# shellcheck source=scripts/run_pipeline.sh
source "$(dirname "${BASH_SOURCE[0]}")/run_pipeline.sh"

run_pipeline
