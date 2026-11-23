"""Argument handling of ci_actions.sh, the command TeamCity runs in the test image.

The `test lint` and `test unit` stages themselves are checked by `make ci-lint` and
`make ci-unit`; running them from here would recurse into pytest.
"""

import subprocess

from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "ci_actions.sh"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args], capture_output=True, text=True, timeout=30
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param((), id="no-args"),
        pytest.param(("test",), id="no-type"),
        pytest.param(("deploy", "unit"), id="unknown-action"),
        pytest.param(("test", "nope"), id="unknown-type"),
    ],
)
def test_bad_arguments_print_usage_and_exit_1(args: tuple[str, ...]) -> None:
    result = run_script(*args)

    assert result.returncode == 1
    assert "Usage: " in result.stderr
    assert result.stdout == ""
