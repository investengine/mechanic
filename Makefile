.PHONY: run setup test

# Keeps an existing .env
setup:
	uv sync
	test -f .env || cp .env.template .env

run:
	uv run --env-file .env python -m mechanic

test:
	uv run pytest
