.PHONY: image install-hooks lint run setup test

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
