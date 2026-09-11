.PHONY: test lint format

test:
	PYTHONPATH="." .\venv\Scripts\python -m pytest tests/

lint:
	.\venv\Scripts\flake8 app/ tests/

format:
	.\venv\Scripts\black app/ tests/
