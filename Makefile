.PHONY: install test demo db-load api app clean

install:
	python -m pip install -e ".[dev,app]"

test:
	pytest

demo:
	python scripts/bootstrap_demo.py

db-load:
	python scripts/load_postgres.py

api:
	uvicorn fleetopt.api.main:app --reload

app:
	streamlit run app/streamlit_app.py

clean:
	rm -rf artifacts/* data/processed/* mlruns .pytest_cache
