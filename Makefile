.PHONY: image install-hooks lint test

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
