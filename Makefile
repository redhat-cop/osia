TOOL := poetry

all: setup_poetry


setup_poetry: .mk_poetry


.mk_poetry: poetry.lock
	poetry install
	touch .mk_poetry

update: setup_poetry
	poetry update

clean:
	poetry env remove --all
	rm -rf .mk_poetry* dist

check: setup_poetry flake8 pylint

flake8: setup_poetry
	poetry run flake8 osia --max-line-length 100 --show-source --statistics

pylint mypy: setup_poetry
	poetry run $@ osia

black-check: setup_poetry
	poetry run black --check osia

dist: setup_poetry
	poetry build

release: dist
	poetry publish

.PHONY: update clean all check
