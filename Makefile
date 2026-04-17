SHELL := /bin/sh

.PHONY: start stop test generate-data train load-test logs scale

start:
	docker compose up --build -d

stop:
	docker compose down

test:
	@echo "Running basic API checks..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -fsS http://localhost:8000/ >/dev/null; then \
			break; \
		fi; \
		sleep 1; \
	done
	curl -fsS http://localhost:8000/health >/dev/null
	curl -fsS http://localhost:8000/metrics >/dev/null
	@echo "Basic checks passed."

generate-data:
	docker run --rm -v "$(PWD)":/app -w /app python:3.11-slim sh -lc "pip install --no-cache-dir -r scripts/requirements.txt >/tmp/p.log && python scripts/generate_data.py"

train:
	docker run --rm -v "$(PWD)":/app -w /app python:3.11-slim sh -lc "pip install --no-cache-dir -r scripts/requirements.txt >/tmp/p.log && python scripts/train_classifier.py"

load-test:
	docker run --rm -v "$(PWD)":/app -w /app python:3.11-slim sh -lc "python scripts/load_test.py"

logs:
	docker compose logs -f

scale:
	docker compose up -d --scale worker=4
