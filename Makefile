.PHONY: ci-lint ci-unit image install-hooks lint test

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
