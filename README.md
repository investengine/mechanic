# Mechanic

Mechanic is InvestEngine's internal AI assistant.

The first class of work it takes
on is first-line support for investigations: someone reports a problem, Mechanic
gathers the evidence and replies with what it established and what it couldn't,
before a person picks the problem up.

See the architecture ADR:
[Mechanic general architecture](https://github.com/investengine/investengine.com/pull/12559)
(`docs/backend/decisions/backoffice/2026-11-12-mechanic-general-architecture.md`).

## Run locally

Needs [uv](https://docs.astral.sh/uv/). uv installs Python 3.14 if it's missing.

```sh
make setup
make run
```

Settings come from environment variables prefixed `MECHANIC_`; `.env.template`
lists them. Settings don't read `.env` themselves: `make run` passes it to uv.

## Test

```sh
make test   # same as: uv run pytest
```

## Lint

```sh
make lint            # pre-commit on all files
make install-hooks   # run it on every commit (make setup does this too)
```

## Docker image

```sh
make image                                  # mechanic:dev (app) and mechanic:test_dev (test)
docker run --rm mechanic:dev                # runs python -m mechanic
docker run --rm mechanic:test_dev pytest    # tests on the code baked into the image
```

`Dockerfile` has two targets: `app` (runtime deps only) and `test` (adds the dev group
and git, built on top of `app` through the `APP_IMAGE` build arg).

## CI

TeamCity runs `./ci_actions.sh test lint` and `./ci_actions.sh test unit` in the test
image. To run the same thing locally:

```sh
make ci-lint    # builds both images, runs ./ci_actions.sh test lint with TeamCity's mounts
make ci-unit    # same for unit; coverage.xml and htmlcov/ land in test_output/
make ci-clean   # removes the root-owned files the container leaves in the checkout
```
