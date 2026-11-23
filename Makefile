.PHONY: install-hooks lint test

install-hooks:
	uv run pre-commit install

lint:
	uv run pre-commit run --all-files --show-diff-on-failure

test:
	uv run pytest
