test:
	python -m pytest --mypy 

run:
	python -m owt.server

mypy:
	mypy --check-untyped-defs

lint:
	ruff check
	ruff format --check

fix:
	ruff check --fix
	ruff format

check: lint test mypy
