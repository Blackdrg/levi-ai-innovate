# LEVI-AI Sovereign OS v22.1 Makefile

.PHONY: build run stop clean test kernel-build help

help:
	@echo "LEVI-AI Sovereign OS v22.1 Management"
	@echo "------------------------------------"
	@echo "make build       - Build all Docker containers"
	@echo "make run         - Launch the full Sovereign stack"
	@echo "make stop        - Stop all containers"
	@echo "make clean       - Remove all containers and volumes"
	@echo "make test        - Run Python integration tests"
	@echo "make kernel-test - Run Rust kernel self-tests"
	@echo "make migration   - Apply database migrations"

build:
	docker-compose build

run:
	docker-compose up -d

stop:
	docker-compose stop

clean:
	docker-compose down -v

test:
	pytest tests/

kernel-test:
	cd backend/kernel && cargo test

migration:
	alembic upgrade head

# Local development (no docker)
dev-kernel:
	cd backend/kernel && cargo run

dev-mainframe:
	uvicorn backend.main:app --reload --port 8000
