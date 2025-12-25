.PHONY: help install dev-install start stop run test lint format db-up db-down db-migrate db-upgrade clean

help:
	@echo "Available commands:"
	@echo "  start        - 啟動 Bot（含資料庫）"
	@echo "  stop         - 停止 Bot 和資料庫"
	@echo "  run          - 只啟動 Bot（不含資料庫）"
	@echo "  install      - Install production dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linter"
	@echo "  format       - Format code"
	@echo "  db-up        - Start database container"
	@echo "  db-down      - Stop database container"
	@echo "  db-migrate   - Create a new migration"
	@echo "  db-upgrade   - Apply migrations"
	@echo "  clean        - Clean up cache files"

start:
	@./scripts/start.sh

stop:
	@./scripts/stop.sh

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

run:
	python -m src.bot.main

test:
	pytest -v --cov=src --cov-report=term-missing

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

db-up:
	docker compose up -d db

db-down:
	docker compose down

db-migrate:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-upgrade:
	alembic upgrade head

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
