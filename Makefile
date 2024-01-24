VENV := $(shell echo $${VIRTUAL_ENV-$$PWD/.venv})
INSTALL_STAMP = $(VENV)/.install.stamp

.IGNORE: clean
.PHONY: all install virtualenv tests tests-once

OBJECTS = .venv .coverage

all: install

$(VENV)/bin/python:
	python -m venv $(VENV)

install: $(INSTALL_STAMP) pyproject.toml requirements.txt
$(INSTALL_STAMP): $(VENV)/bin/python pyproject.toml requirements.txt
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install ".[dev,s3,gcloud,docs]"
	touch $(INSTALL_STAMP)

lint: install
	$(VENV)/bin/ruff check pyramid_storage tests
	$(VENV)/bin/ruff format --check pyramid_storage tests

format: install
	$(VENV)/bin/ruff check --fix pyramid_storage tests
	$(VENV)/bin/ruff format pyramid_storage tests

requirements.txt: requirements.in
	pip-compile requirements.in

tests: test
test: install
	$(VENV)/bin/py.test

docs: install
	cd docs/ && make html SPHINXBUILD=$(VENV)/bin/sphinx-build

clean:
	find pyramid_storage/ -name '*.pyc' -delete
	find pyramid_storage/ -name '__pycache__' -type d -exec rm -fr {} \;
	rm -rf $(VENV) mail/ *.egg-info .pytest_cache .ruff_cache .coverage build dist
