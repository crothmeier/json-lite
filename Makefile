.PHONY: help build build-op1 build-op2 up down stop restart logs clean test shell-op1 shell-op2 monitoring

# Default target
help:
	@echo "JSON-Lite Docker Management"
	@echo "=========================="
	@echo "Available targets:"
	@echo "  make build        - Build all Docker images"
	@echo "  make build-op1    - Build only OP1 Large image"
	@echo "  make build-op2    - Build only OP2 Lite image"
	@echo "  make up           - Start all services"
	@echo "  make up-op1       - Start only OP1 Large service"
	@echo "  make up-op2       - Start only OP2 Lite service"
	@echo "  make down         - Stop and remove all containers"
	@echo "  make stop         - Stop all containers"
	@echo "  make restart      - Restart all services"
	@echo "  make logs         - View logs from all services"
	@echo "  make logs-op1     - View logs from OP1 Large"
	@echo "  make logs-op2     - View logs from OP2 Lite"
	@echo "  make clean        - Remove all containers, networks, and volumes"
	@echo "  make test         - Run all tests with coverage"
	@echo "  make test-watch   - Run tests in watch mode"
	@echo "  make test-benchmark - Run benchmark tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage - Generate HTML coverage report"
	@echo "  make test-docker  - Run tests in Docker containers"
	@echo "  make test-tox     - Run tests with tox (all Python versions)"
	@echo "  make test-lint    - Run linting checks"
	@echo "  make test-type    - Run type checking"
	@echo "  make test-security - Run security checks"
	@echo "  make shell-op1    - Open shell in OP1 container"
	@echo "  make shell-op2    - Open shell in OP2 container"
	@echo "  make monitoring   - Start with Prometheus monitoring"
	@echo "  make health       - Check health status of services"
	@echo "  make prune        - Remove unused Docker resources"

# Build targets
build:
	docker-compose build --parallel

build-op1:
	docker-compose build op1-large

build-op2:
	docker-compose build op2-lite

# Run targets
up:
	docker-compose up -d
	@echo "Services started. OP2 Lite API available at http://localhost:8000"

up-op1:
	docker-compose up -d op1-large

up-op2:
	docker-compose up -d op2-lite
	@echo "OP2 Lite API available at http://localhost:8000"

# Stop targets
down:
	docker-compose down

stop:
	docker-compose stop

# Restart target
restart:
	docker-compose restart

# Logs targets
logs:
	docker-compose logs -f

logs-op1:
	docker-compose logs -f op1-large

logs-op2:
	docker-compose logs -f op2-lite

# Clean target
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Test targets
test:
	pytest -v --cov=shared --cov=op1_large --cov=op2_lite --cov-report=term-missing

test-watch:
	ptw -- -v

test-benchmark:
	pytest -v --benchmark-only --benchmark-autosave

test-unit:
	pytest -v -m "not integration and not benchmark" tests/

test-integration:
	pytest -v -m integration tests/

test-coverage:
	pytest --cov=shared --cov=op1_large --cov=op2_lite --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-docker:
	@echo "Running tests in OP1 Large container..."
	docker-compose run --rm op1-large python -m pytest /app/tests/ || true
	@echo "Running tests in OP2 Lite container..."
	docker-compose run --rm op2-lite python -m pytest /app/tests/ || true

test-tox:
	tox

test-lint:
	tox -e lint

test-type:
	tox -e type

test-security:
	tox -e security

# Shell targets
shell-op1:
	docker-compose exec op1-large /bin/bash

shell-op2:
	docker-compose exec op2-lite /bin/bash

# Monitoring target
monitoring:
	docker-compose --profile monitoring up -d
	@echo "Prometheus available at http://localhost:9090"
	@echo "OP2 Lite API available at http://localhost:8000"

# Health check
health:
	@echo "Checking OP2 Lite health..."
	@curl -f http://localhost:8000/health 2>/dev/null && echo "OP2 Lite: Healthy" || echo "OP2 Lite: Unhealthy"
	@echo ""
	@echo "Container status:"
	@docker-compose ps

# Docker cleanup
prune:
	docker system prune -af --volumes

# Development targets
dev-op1:
	docker-compose run --rm -v $(PWD)/op1_large:/app/op1_large op1-large /bin/bash

dev-op2:
	docker-compose run --rm -v $(PWD)/op2_lite:/app/op2_lite -p 8000:8000 op2-lite /bin/bash

# Build with no cache
rebuild:
	docker-compose build --no-cache --parallel

rebuild-op1:
	docker-compose build --no-cache op1-large

rebuild-op2:
	docker-compose build --no-cache op2-lite