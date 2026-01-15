.PHONY: format fix-lint lint

run:
	PYTHONPATH=. uv run --env-file .env python src/main.py

format:
	uv run black .
	uv run ruff format .

fix-lint: format
	uv run ruff check --fix .

lint: format
	uv run black --check .
	uv run ruff check .
	uv run ruff format --check .

clean: format fix-lint lint
	