.PHONY: help install build up down logs restart clean test lint format discover

help:
	@echo "Marstek Automation - Available commands:"
	@echo ""
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show logs from all services"
	@echo "  make restart      - Restart all services"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make discover     - Discover batteries on network"
	@echo ""

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

clean:
	docker-compose down -v
	docker system prune -f

test:
	cd backend && poetry run pytest

lint:
	cd backend && poetry run ruff check . && poetry run mypy app

format:
	cd backend && poetry run black . && poetry run isort .

discover:
	python scripts/discover_batteries.py

setup:
	cp env.template .env
	@echo "✅ Created .env file. Please edit it with your configuration."
