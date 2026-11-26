# Mechanic

InvestEngine's planned AI core. First job: first-line support for investigations,
starting with #help-dev-en. Python 3.14, uv, `src/mechanic`.
See README.md for the architecture ADR.

## Commands

- Setup: `make setup` (`uv sync`, and `.env` from `.env.template` if there's none)
- Run: `make run` (= `uv run --env-file .env python -m mechanic`)
- Test: `make test` (= `uv run pytest`)

## Conventions

- Settings: `mechanic.config.Settings` (pydantic-settings), env vars prefixed `MECHANIC_`,
  secrets as `SecretStr`. Add each new variable to `.env.template`.
- `mechanic/__main__.py` is the composition root: it builds `Settings()` once and passes
  it down. Nothing reads settings through a global.
