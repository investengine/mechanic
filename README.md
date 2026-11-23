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

## Lint

```sh
make lint            # pre-commit on all files
make install-hooks   # run it on every commit
```

The config (`.pre-commit-config.yaml`, `.flake8`, `[tool.*]` in `pyproject.toml`)
is copied from the monolith (the investengine.com backend) except the differences
listed in `.pre-commit-config.yaml`: among them strict mypy, import-linter contracts
for the architecture ADR's layers, and formatters that fix files in place. Keep the
rest in sync until the shared linters repo replaces the copy.

## Docker image

```sh
make image                                  # mechanic:dev (app) and mechanic:test_dev (test)
docker run --rm mechanic:dev                # runs python -m mechanic
docker run --rm mechanic:test_dev pytest    # tests on the code baked into the image
```

`Dockerfile` has two targets: `app` (runtime deps only) and `test` (adds the dev group
and git, built on top of `app` through the `APP_IMAGE` build arg).

## CI for DevOps

CI runs on TeamCity's side-repo templates, like DevStats: `Investengine_Docker_Metarunners_BuildDockerContainer`
for images and `RunTestInDocker` for tests. Mechanic keeps those templates' defaults, so
the DevStats build configs can be copied with the repo name changed.

### Builds to create

| # | Build | Template | Parameters |
| --- | --- | --- | --- |
| 1 | Build Backend | `Investengine_Docker_Metarunners_BuildDockerContainer` | `docker.target_string=--target app`; build args `VERSION`, `REPO` (accepted, unused for now) |
| 2 | Build Test Backend | same | `docker.target_string=--target test`, `docker.image_prefix=test_`, `docker.args.APP_IMAGE=<registry>/<repo>:%env.BUILD_VCS_NUMBER%`; snapshot dependency on 1 |
| 3 | Backend Lint Checks | `RunTestInDocker` | `tests.command.params=lint`, `docker.mount_vcs_files=true`, agent-side checkout (`checkoutMode = AUTO`) |
| 4 | Backend Unit Tests | `RunTestInDocker` | `tests.command.params=unit`, `docker.mount_vcs_files=true`, agent-side checkout; artifacts `test_output/coverage.xml`, `test_output/htmlcov/` |

- Suggested `docker.repo`: `mechanic` (your call). Builds 3 and 4 must use the same repo as 1 and 2.
- Triggers: PRs and branches, as DevStats.
- Needs: no environment variables, no services (no database). Lint needs internet:
  pre-commit downloads its hook environments from GitHub and PyPI on every run, as in
  the monolith. A run takes a few minutes at most, well under the template's 30-minute limit.
- Not yet: image push for deploys, Vault, Kubernetes. Those come with the deployment work.

### What Mechanic relies on

At the template's default (please don't override):

| What | Default | Where (`teamcity/.teamcity/_Self/buildTypes/`) |
| --- | --- | --- |
| Test command | `./ci_actions.sh test %tests.command.params%`, run from the image's `WORKDIR`; exit code = green/red | `RunTestInDocker.kt:28` |
| Workdir | `docker.path_in_docker=/data/www/investengine.com`, the image's `WORKDIR`; the checkout is mounted there | `RunTestInDocker.kt:25,99-107` |
| Dockerfile | `docker.dockerfile=%working_directory%/Dockerfile` | `Investengine_Docker_Metarunners_BuildDockerContainer.kt:23` |
| No `Dockerfile.base` | if one exists, `--target` is ignored; Mechanic has none | `…BuildDockerContainer.kt:53-61` |
| Artifacts | `test_output` is mounted at `<workdir>/__output__` and published | `RunTestInDocker.kt:16,101` |
| Test reporting | `TEAMCITY_VERSION` is passed, so `teamcity-messages` reports each test | `RunTestInDocker.kt:97` |

Set per build config:

| What | Value | Where |
| --- | --- | --- |
| Targets | `docker.target_string`: `--target app` / `--target test` | `…BuildDockerContainer.kt:26` |
| `APP_IMAGE` | passed only when set; the `test` stage builds `FROM` it (without it, from the `app` stage in the same Dockerfile) | `…BuildDockerContainer.kt:73-74` |
| `.git` in the container | only with `docker.mount_vcs_files=true` and an agent-side checkout; lint needs it | `RunTestInDocker.kt:20,100`; `DevStats_Tests_BackendUnitTests.kt:12,20` |
| Environment | build parameter `env.IE_FOO` reaches the container as `FOO`, so Mechanic settings go in as `env.IE_MECHANIC_*` (none needed yet) | `RunTestInDocker.kt:72-73` |

The test image runs as root, like the monolith's. `ci_actions.sh test lint` marks the
mounted checkout as a git `safe.directory` for its run, so git accepts it whichever
user owns the checkout on the agent.

### Run CI locally

```sh
make ci-lint   # builds both images, runs ./ci_actions.sh test lint with TeamCity's mounts
make ci-unit   # same for unit; coverage.xml and htmlcov/ land in test_output/
```

Run these from a regular clone: in a git worktree, `.git` is a file pointing outside
the mounted directory, so lint can't find the repository.

The container runs as root, so it leaves root-owned files in the checkout
(`test_output/`, `.pytest_cache/`, `.mypy_cache/`, `__pycache__/`, `.coverage`, all
gitignored).
Remove them with:

```sh
docker run --rm -v "$PWD":/w -w /w mechanic:test_dev \
    rm -rf test_output __output__ .pytest_cache .mypy_cache .coverage \
        src/mechanic/__pycache__ tests/__pycache__
```
