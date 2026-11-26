# Mechanic

Mechanic is planned to become InvestEngine's AI core. The first class of work it
takes on is first-line support for investigations: someone reports a problem,
Mechanic gathers the evidence and replies with what it established and what it
couldn't, before a person picks the problem up.

The first use case is #help-dev-en. Mechanic does the first pass on new threads
there, which QA does today.

It lives in its own repository with a thin image, no Django, read-only credentials,
and its own dependencies and deploys. See the architecture ADR:
[Mechanic general architecture](https://github.com/investengine/investengine.com/pull/12559)
(`docs/backend/decisions/backoffice/2026-11-12-mechanic-general-architecture.md`
in investengine.com, linked as a PR until it merges).

The repository is a scaffold for now: settings and an entry point that logs one
line and exits.

## Run locally

Needs [uv](https://docs.astral.sh/uv/). uv installs Python 3.14 if it's missing.

```sh
uv sync
uv run python -m mechanic
```

Settings come from environment variables prefixed `MECHANIC_`; `.env.template`
lists them. Settings don't read `.env` themselves, so either export the variables
or pass the file to uv:

```sh
cp .env.template .env
uv run --env-file .env python -m mechanic
```

## Test

```sh
make test   # same as: uv run pytest
```
