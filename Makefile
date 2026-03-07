.PHONY: up down migrate api worker test

up:
	docker-compose up -d

down:
	docker-compose down

sentry-up:
	docker-compose -f docker-compose-sentry.yaml up -d

sentry-down:
	docker-compose -f docker-compose-sentry.yaml down

migrate:
	bash migrate.sh

api:
	uvicorn main:app --host 0.0.0.0 --port 8003

worker:
	python -m workers.moderation_worker

test:
	pytest -v

test-unit:
	pytest -m "not integration" -v

test-integration:
	pytest -m integration -v