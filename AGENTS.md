# Mechanic

InvestEngine's internal AI assistant. First job: first-line support for investigations,
starting with #help-dev-en. Python 3.14, uv, `src/mechanic`.
See README.md for the architecture ADR.

## Commands

- Setup: `make setup` (`uv sync`, `.env` from `.env.template` if there's none, and `make install-hooks`)
- Run: `make run` (= `uv run --env-file .env python -m mechanic`)
- Test: `make test` (= `uv run pytest`)
- Lint: `make lint` (pre-commit on all files; config copied from the monolith except the differences listed in `.pre-commit-config.yaml`; keep the rest in sync)
- Git hook: `make install-hooks` (`make setup` runs it)
- CI stages as TeamCity runs them: `make ci-lint`, `make ci-unit` (build the images, run `./ci_actions.sh test <lint|unit>` in `mechanic:test_dev`); `make ci-clean` removes the root-owned files they leave
- Images: `make image` (`mechanic:dev` from `--target app`, `mechanic:test_dev` from `--target test`)

## Conventions

- Settings: `mechanic.config.Settings` (pydantic-settings), env vars prefixed `MECHANIC_`,
  secrets as `SecretStr`. Add each new variable to `.env.template`.
- `mechanic/__main__.py` is the composition root: it builds `Settings()` once and passes
  it down. Nothing reads settings through a global.
