import pytest
from pydantic import ValidationError

from mechanic.config import Settings


def test_log_level_defaults_to_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MECHANIC_LOG_LEVEL", raising=False)

    assert Settings().log_level == "INFO"


def test_log_level_is_read_from_prefixed_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MECHANIC_LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"


def test_invalid_log_level_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MECHANIC_LOG_LEVEL", "LOUD")

    with pytest.raises(ValidationError, match="log_level"):
        Settings()


def test_unprefixed_env_var_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MECHANIC_LOG_LEVEL", raising=False)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "INFO"
