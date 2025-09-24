PYTHON ?= python
PIP ?= pip
SRC_DIR := src

# Default target
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@grep -E '^##' Makefile | sed -e 's/## //'

## install: Install production + development dependencies
install:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

## format: Auto-format code (isort, black)
format:
	isort $(SRC_DIR) tests
	black $(SRC_DIR) tests

## lint: Run static analysis (flake8, isort --check, black --check, mypy)
lint:
	flake8 $(SRC_DIR) tests
	isort --check-only $(SRC_DIR) tests
	black --check $(SRC_DIR) tests
	mypy $(SRC_DIR)

## test: Run test suite with coverage (global >=80%, invoices router >=90%)
test:
	pytest
	# Enforce 90% coverage on invoices router (T004)
	coverage report --fail-under=90 $(SRC_DIR)/routers/invoices.py

## perf: Run only performance tests
perf:
	pytest -m performance -k invoice -q

## clean: Remove build, cache, coverage artifacts
clean:
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage

## cov-html: Open HTML coverage report (generate if missing)
cov-html:
	[ -f htmlcov/index.html ] || pytest >/dev/null 2>&1 || true
	@echo "Open htmlcov/index.html in your browser"

.PHONY: help install format lint test perf clean cov-html
