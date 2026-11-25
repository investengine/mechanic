#!/bin/bash
# The command TeamCity runs inside the test image: ./ci_actions.sh test <lint|unit>
# Tools come from the image's venv on PATH (/opt/venv/bin), not `uv run`, so CI
# never re-syncs the venv. Artifacts go to __output__/ (TeamCity's test_output).
set -euo pipefail

usage() {
    echo "Usage: $0 test <lint|unit> [pytest args, unit only]" >&2
    exit 1
}

test_lint() {
    # The checkout is mounted from the host, so its owner can differ from the
    # container user and git refuses it ("dubious ownership"). Trust it for
    # this run only, without writing any git config file.
    export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="$PWD"
    pre-commit run --all-files --show-diff-on-failure
}

test_unit() {
    # The container runs as root: keep bytecode, the pytest cache and the
    # coverage data file out of the mounted checkout
    export PYTHONDONTWRITEBYTECODE=1 COVERAGE_FILE=__output__/.coverage
    mkdir -p __output__
    exec pytest -vv -p no:cacheprovider --cov=mechanic \
        --cov-report=xml:__output__/coverage.xml \
        --cov-report=html:__output__/htmlcov \
        "$@"
}

[ $# -ge 2 ] || usage
cd "$(dirname "$0")"

case "$1 $2" in
    "test lint") test_lint ;;
    "test unit") shift 2; test_unit "$@" ;;
    *) echo "Unknown command: $1 $2" >&2; usage ;;
esac
