# Mechanic

InvestEngine's planned AI core. First job: first-line support for investigations,
starting with #help-dev-en. Python 3.14, uv, `src/mechanic`.
See README.md for the architecture ADR.

## Commands

- Install: `uv sync`
- Run: `uv run python -m mechanic` (with a local `.env`: `uv run --env-file .env python -m mechanic`)
- Test: `make test` (= `uv run pytest`)
- Lint: `make lint` (pre-commit on all files; config copied from the monolith, keep it in sync)
- Git hook: `make install-hooks`

## Conventions

- Settings: `mechanic.config.Settings` (pydantic-settings), env vars prefixed `MECHANIC_`,
  secrets as `SecretStr`. Add each new variable to `.env.template`.
- `mechanic/__main__.py` is the composition root: it builds `Settings()` once and passes
  it down. Nothing reads settings through a global.
