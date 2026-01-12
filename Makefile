.PHONY: lint format

lint:
	uv run black --check .
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
