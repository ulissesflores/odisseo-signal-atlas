.PHONY: install install-dev lint test typecheck smoke run clean

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e .

install-dev:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check src tests scripts

test:
	.venv/bin/pytest

typecheck:
	.venv/bin/mypy src

smoke:
	ODISSEO_X_MAX_RESULTS_PER_PAGE=10 ODISSEO_X_PAGES_PER_QUERY=1 .venv/bin/python scripts/run_hunt.py --target 10 --languages en,pt,es

run:
	.venv/bin/python scripts/run_hunt.py --target 500

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete

