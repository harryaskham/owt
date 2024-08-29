test:
	python -m pytest

run:
	python -m owt.server

mypy:
	mypy

lint:
	ruff check
	ruff format --check

check: lint test mypy
