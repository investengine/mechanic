# One Dockerfile, two targets, in the shape TeamCity's build template expects:
#   app:  docker build --target app --build-arg VERSION=<sha> --build-arg REPO=<repo> .
#   test: docker build --target test --build-arg APP_IMAGE=<registry>/<repo>:<sha> .
# Without APP_IMAGE, test builds on the app stage in this file. Don't add a
# Dockerfile.base: the template then ignores --target.
ARG APP_IMAGE=app

###############################################################################
# Stage: App
FROM python:3.14-slim-trixie AS app

# Accepted from TeamCity, unused for now
ARG VERSION
ARG REPO

# The venv lives outside WORKDIR, so it survives CI mounting the checkout there.
# uv uses the image's Python, never a downloaded one.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /usr/local/bin/

# TeamCity's default docker.path_in_docker: CI mounts the checkout, .git and
# __output__ here and runs ./ci_actions.sh from this directory
WORKDIR /data/www/investengine.com

# Dependencies first, so code changes don't reinstall them
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY . .
RUN uv sync --no-dev --frozen

# The app doesn't run as root. Code and venv stay root-owned and read-only to it.
# Numeric, so Kubernetes' runAsNonRoot can verify it.
RUN useradd --system --uid 10001 --no-create-home mechanic
USER 10001

CMD ["python", "-m", "mechanic"]

FROM ${APP_IMAGE} AS app_inc

###############################################################################
# Stage: Test
FROM app_inc AS test

# Back to root: CI mounts the agent's checkout into WORKDIR and writes caches and
# __output__ there, and RunTestInDocker gives us no way to match the agent's uid
USER root

# pre-commit needs git
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Adds the dev group
RUN uv sync --frozen
