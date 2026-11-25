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

## CI for DevOps

CI runs on TeamCity's side-repo templates, like DevStats: `Investengine_Docker_Metarunners_BuildDockerContainer`
for images and `RunTestInDocker` for tests. Mechanic sets the same parameters as the
DevStats build configs (including `working_directory=.` on the image builds) and relies
on the templates' defaults for the rest, so those configs can be copied with the repo
name changed.

### Builds to create

| # | Build | Template | Parameters |
| --- | --- | --- | --- |
| 1 | Build Backend | `Investengine_Docker_Metarunners_BuildDockerContainer` | `docker.target_string=--target app`, `working_directory=.`; build args `VERSION`, `REPO` (accepted, unused for now) |
| 2 | Build Test Backend | same | `docker.target_string=--target test`, `working_directory=.`, `docker.image_prefix=test_`, `docker.args.APP_IMAGE=<registry>/<repo>:%env.BUILD_VCS_NUMBER%`; snapshot dependency on 1 (`onDependencyFailure = FAIL_TO_START`) |
| 3 | Backend Lint Checks | `RunTestInDocker` | `tests.command.params=lint`, `docker.mount_vcs_files=true`, agent-side checkout (`checkoutMode = AUTO`); snapshot dependency on 2 (`onDependencyFailure = FAIL_TO_START`) |
| 4 | Backend Unit Tests | `RunTestInDocker` | `tests.command.params=unit`, `docker.mount_vcs_files=true`, agent-side checkout; snapshot dependency on 2 (`onDependencyFailure = FAIL_TO_START`); artifacts `test_output/coverage.xml`, `test_output/htmlcov/` |

- `working_directory=.` on 1 and 2: the template's default is empty, which makes
  `docker.dockerfile` `/Dockerfile`. DevStats sets it on both
  (`DevStats_Builds_BuildBackend.kt`, `DevStats_Builds_BuildTestBackend.kt`).
- Snapshot dependency of 3 and 4 on 2: `RunTestInDocker` pulls the `test_<sha>` image,
  which may not exist yet without it. DevStats has it in
  `patches/buildTypes/DevStats_Tests_BackendUnitTests.kts`.
- Suggested `docker.repo`: `mechanic` (your call). Builds 3 and 4 must use the same repo as 1 and 2.
- Triggers: PRs and branches, as DevStats.
- Needs: no environment variables, no services (no database). Lint needs internet:
  pre-commit downloads its hook environments from GitHub and PyPI on every run, as in
  the monolith. A run takes a few minutes at most, well under the template's 30-minute limit.
- Lint also runs mypy and import-linter, from the test image's venv (`/opt/venv`). Nothing
  changes for DevOps: the test image already has the dev group that provides them.
- Not yet: image push for deploys, Vault, Kubernetes. Those come with the deployment work.

### What Mechanic relies on

At the template's default (please don't override):

| What | Default | Where (`teamcity/.teamcity/_Self/buildTypes/`) |
| --- | --- | --- |
| Test command | `./ci_actions.sh test %tests.command.params%`, run from the image's `WORKDIR`; exit code = green/red | `RunTestInDocker.kt:29` |
| Workdir | `docker.path_in_docker=/data/www/investengine.com`, the image's `WORKDIR`; the checkout is mounted there | `RunTestInDocker.kt:25,99-102` |
| Dockerfile | `docker.dockerfile=%working_directory%/Dockerfile`, so `./Dockerfile` with `working_directory=.` | `Investengine_Docker_Metarunners_BuildDockerContainer.kt:23` |
| No `Dockerfile.base` | if one exists, `--target` is ignored; Mechanic has none | `…BuildDockerContainer.kt:53-57` |
| Artifacts | `test_output` is mounted at `<workdir>/__output__` and published | `RunTestInDocker.kt:16,101` |
| Test reporting | `TEAMCITY_VERSION` is passed, so `teamcity-messages` reports each test | `RunTestInDocker.kt:97` |

Set per build config:

| What | Value | Where |
| --- | --- | --- |
| Targets | `docker.target_string`: `--target app` / `--target test` | `…BuildDockerContainer.kt:26` |
| Build context | `working_directory=.` on builds 1 and 2; the default is empty, which gives `/Dockerfile` | `…BuildDockerContainer.kt:19,23` |
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

The container runs as root, so it leaves root-owned files in the checkout:
`test_output/` (the artifacts, including coverage's `.coverage` data file), the lint
caches `.mypy_cache/` and `.import_linter_cache/` (both ignore themselves), and the
empty `__output__/` mount point. Unit tests write no bytecode or pytest cache.
Remove them with:

```sh
docker run --rm -v "$PWD":/w -w /w mechanic:test_dev \
    rm -rf test_output __output__ .mypy_cache .import_linter_cache
```
