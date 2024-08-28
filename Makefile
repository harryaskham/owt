test:
	python -m pytest

run:
	python -m owt.server

mypy:
	mypy --enable-incomplete-feature=NewGenericSyntax -m owt

lint:
	ruff check
	ruff format --check

check: lint test mypy
