#!/bin/bash
# The command TeamCity runs inside the test image: ./ci_actions.sh test <lint|unit>
# Tools come from the image's venv on PATH (/opt/venv/bin), not `uv run`, so CI
# never re-syncs the venv. Artifacts go to __output__/ (TeamCity's test_output).
set -euo pipefail

usage() {
    echo "Usage: $0 <action> <test_type> [additional_args]" >&2
    echo "  action:    test" >&2
    echo "  test_type: lint | unit (unit passes additional_args to pytest)" >&2
    exit 1
}

ACTION=${1:-}
TEST_TYPE=${2:-}

if [ -z "$ACTION" ] || [ -z "$TEST_TYPE" ]; then
    usage
fi

shift 2

cd "$(dirname "$0")"

case "$ACTION" in
    test)
        case "$TEST_TYPE" in
            lint)
                echo "Running linter checks..."
                mkdir -p "$HOME/.cache/pre-commit"
                # The checkout is mounted from the host, so its owner can differ
                # from the container user and git refuses it ("dubious ownership").
                # Trust it for this run only, without writing any git config file.
                export GIT_CONFIG_COUNT=1
                export GIT_CONFIG_KEY_0=safe.directory
                export GIT_CONFIG_VALUE_0="$PWD"
                pre-commit run --all-files --show-diff-on-failure
                ;;
            unit)
                echo "Running unit tests with coverage..."
                mkdir -p __output__
                exec pytest -vv \
                    --cov=mechanic \
                    --cov-report=xml:__output__/coverage.xml \
                    --cov-report=html:__output__/htmlcov \
                    "$@"
                ;;
            *)
                echo "Unknown test type: $TEST_TYPE" >&2
                usage
                ;;
        esac
        ;;
    *)
        echo "Unknown action: $ACTION" >&2
        usage
        ;;
esac
