.PHONY: format lint fix-lint

format:
	uv run black .
	uv run ruff format .

fix-lint: format
	uv run ruff check --fix .

lint: format
	uv run black --check .
	uv run ruff check .
	uv run ruff format --check .
