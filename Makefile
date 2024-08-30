test:
	pytest --mypy

run:
	python -m owt.server

mypy:
	mypy --check-untyped-defs

lint:
	ruff check
	ruff format --check

check: lint test mypy
