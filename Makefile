TOOL := poetry

all: setup_poetry


setup_poetry: .mk_poetry


.mk_poetry: poetry.lock
	poetry install
	touch .mk_poetry

update: setup_poetry
	poetry update

clean:
	poetry env list | cut -d' ' -f1 | xargs poetry env remove
	rm .mk_poetry*

check: setup_poetry
	poetry run flake8 osia --max-line-length 100 --show-source --statistics
	poetry run pylint osia

dist: setup_poetry
	poetry build

release: dist
	poetry release

.PHONY: update clean all check