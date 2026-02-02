# HB-Staffing Development and Deployment Makefile

.PHONY: help install dev backend frontend clean test docker-build docker-up docker-down deploy migrate

# Default target
help:
	@echo "HB-Staffing Development Commands"
	@echo "==============================="
	@echo "Development:"
	@echo "  make install     - Install all dependencies"
	@echo "  make dev         - Start development servers"
	@echo "  make backend     - Start backend server only"
	@echo "  make frontend    - Start frontend server only"
	@echo "  make clean       - Clean up development environment"
	@echo "  make test        - Run all tests"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    - Build Docker images"
	@echo "  make docker-up       - Start Docker containers"
	@echo "  make docker-down     - Stop Docker containers"
	@echo "  make docker-logs     - View Docker logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run database migrations"
	@echo "  make seed        - Seed database with sample data"
	@echo ""
	@echo "Deployment:"
	@echo "  make build       - Build for production"
	@echo "  make deploy      - Deploy to production"

# Installation
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Development servers
dev: backend frontend

backend:
	@echo "Starting backend server..."
	cd backend && source venv/bin/activate && python app.py

frontend:
	@echo "Starting frontend server..."
	cd frontend && npm run dev

# Docker commands
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

# Production build
build:
	@echo "Building for production..."
	cd frontend && npm run build

# Database operations
migrate:
	@echo "Running database migrations..."
	cd backend && export FLASK_APP=app.py && flask db upgrade

seed:
	@echo "Seeding database..."
	cd backend && python -c "from database import seed_database; seed_database()"

# Testing
test:
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/ -v
	@echo "Running frontend tests..."
	cd frontend && npm test -- --watchAll=false

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete
	docker system prune -f

# Deployment
deploy: build
	@echo "Deploying to production..."
	@echo "Make sure your production environment is configured!"
	@echo "Run: docker-compose -f docker-compose.prod.yml up -d"

# Health checks
health:
	@echo "Checking backend health..."
	curl -f http://localhost:8000/api/health || echo "Backend not healthy"
	@echo "Checking frontend..."
	curl -f http://localhost:3000 || echo "Frontend not accessible"

# Database backup
backup:
	@echo "Creating database backup..."
	docker exec hb-staffing_db_1 pg_dump -U hb_user hb_staffing > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Logs
logs:
	@echo "Showing application logs..."
	docker-compose logs -f backend frontend

# Environment setup
setup:
	@echo "Setting up development environment..."
	cp env.example .env
	@echo "Please edit .env with your configuration"
	@echo "Then run: make migrate && make seed"
