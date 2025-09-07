# FPL Chatbot - Development Makefile

.PHONY: help install dev clean test lint format docker-build docker-run deploy

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  dev         - Run development server"
	@echo "  clean       - Clean cache files"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linter"
	@echo "  format      - Format code"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  deploy       - Deploy to production"

# Install dependencies
install:
	pip install -r requirements.txt

# Run development server
dev:
	export FLASK_ENV=development && python app.py

# Clean cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

# Run tests (if any)
test:
	@echo "No tests configured yet"

# Run linter
lint:
	@echo "No linter configured yet"

# Format code
format:
	@echo "No formatter configured yet"

# Docker commands
docker-build:
	docker build -t fpl-chatbot .

docker-run:
	docker run -p 8080:8080 --env-file .env fpl-chatbot

# Deploy (placeholder)
deploy:
	@echo "Deploy command not configured yet"
