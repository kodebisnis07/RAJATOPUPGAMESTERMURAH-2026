.PHONY: install test lint run docker-up
install:
	python -m pip install -r requirements-dev.txt
test:
	python -m compileall -q app tests
	python tests_static.py
	pytest -q
lint:
	ruff check app tests run.py config.py
run:
	flask --app run.py run --debug
docker-up:
	docker compose up --build
