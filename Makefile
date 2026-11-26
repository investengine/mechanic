.PHONY: ci-clean ci-lint ci-unit image install-hooks lint run setup test

# Keeps an existing .env
setup:
	uv sync
	test -f .env || cp .env.template .env
	$(MAKE) install-hooks

run:
	uv run --env-file .env python -m mechanic

install-hooks:
	uv run pre-commit install

lint:
	uv run pre-commit run --all-files --show-diff-on-failure

test:
	uv run pytest

# Mirrors TeamCity: app with VERSION and REPO, then test on top of it via APP_IMAGE
image:
	docker build --pull --target app --build-arg VERSION=dev --build-arg REPO=mechanic -t mechanic:dev .
	docker build --target test --build-arg APP_IMAGE=mechanic:dev -t mechanic:test_dev .

# CI stages as TeamCity's RunTestInDocker runs them: checkout, .git and the
# artifacts dir mounted at the image's WORKDIR. Artifacts land in test_output/.
# Lint breaks in a git worktree: .git there is a file pointing outside the mount.
CI_WORKDIR := /data/www/investengine.com
CI_RUN := docker run --rm --network host -e TEAMCITY_VERSION=local \
	-v "$(CURDIR)":$(CI_WORKDIR) \
	-v "$(CURDIR)/.git":$(CI_WORKDIR)/.git \
	-v "$(CURDIR)/test_output":$(CI_WORKDIR)/__output__ \
	mechanic:test_dev ./ci_actions.sh test

ci-lint: image
	mkdir -p test_output
	$(CI_RUN) lint

ci-unit: image
	mkdir -p test_output
	$(CI_RUN) unit

# The test container runs as root, so only root can remove what it leaves behind
ci-clean:
	docker run --rm -v "$(CURDIR)":/w -w /w mechanic:test_dev \
		rm -rf test_output __output__ .mypy_cache .import_linter_cache
