import os
import subprocess
import sys

import pytest

from mechanic.__main__ import main


def run_mechanic(**env: str) -> subprocess.CompletedProcess[str]:
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("MECHANIC_")}
    return subprocess.run(
        [sys.executable, "-m", "mechanic"],
        env=clean_env | env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_main_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MECHANIC_LOG_LEVEL", raising=False)

    assert main() == 0


def test_module_run_exits_zero() -> None:
    result = run_mechanic()

    assert result.returncode == 0, result.stderr


def test_module_run_with_invalid_log_level_exits_non_zero() -> None:
    result = run_mechanic(MECHANIC_LOG_LEVEL="LOUD")

    assert result.returncode != 0
    assert "ValidationError" in result.stderr
