.PHONY: up down sentry-up sentry-down migrate api worker test test-unit test-integration

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

N ?= 1

worker:
	@bash -c 'trap "kill 0" SIGINT SIGTERM EXIT; \
	for ((i=1; i<=$(N); i++)); do \
		python -m workers.moderation_worker & \
		sleep 1; \
	done; \
	wait'


test:
	pytest -v

test-unit:
	pytest -m "not integration" -v

test-integration:
	pytest -m integration -v