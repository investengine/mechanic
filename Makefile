.PHONY: install-hooks lint run setup test

# Keeps an existing .env
setup:
	uv sync
	test -f .env || cp .env.template .env

run:
	uv run --env-file .env python -m mechanic

install-hooks:
	uv run pre-commit install

lint:
	uv run pre-commit run --all-files --show-diff-on-failure

test:
	uv run pytest
