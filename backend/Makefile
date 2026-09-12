.PHONY: test lint format

test:
	PYTHONPATH="." python -m pytest tests/

lint:
	python -m flake8 app/ tests/

format:
	python -m black app/ tests/
