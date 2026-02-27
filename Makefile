.PHONY: up down migrate api worker test

up:
	docker-compose up -d

down:
	docker-compose down

migrate:
	bash migrate.sh

api:
	uvicorn main:app --reload --host 0.0.0.0 --port 8003

worker:
	python -m workers.moderation_worker

test:
	pytest -v