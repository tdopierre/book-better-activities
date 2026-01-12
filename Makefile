.PHONY: format lint

format:
	uv run black .
	uv run ruff format .

lint: format
	uv run black --check .
	uv run ruff check .
	uv run ruff format --check .
