# ZoubiVM - Makefile for Docker management

.PHONY: help build up down restart logs shell clean pull test

# Colors for display
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m # No Color

# Main commands
help: ## Display this help
	@echo "Available commands for ZoubiVM:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

build: ## Build the Docker image
	@echo "$(BLUE)[Docker]$(NC) Building image..."
	docker compose build
	@echo "$(GREEN)[OK]$(NC) Image built successfully"

up: ## Start the bot in the background
	@echo "$(BLUE)[Docker]$(NC) Starting container..."
	docker compose up -d
	@echo "$(GREEN)[OK]$(NC) Bot started (use 'docker compose logs -f' to view logs)"

down: ## Stop the bot
	@echo "$(BLUE)[Docker]$(NC) Stopping container..."
	docker compose down
	@echo "$(GREEN)[OK]$(NC) Container stopped"

restart: ## Restart the bot
	@echo "$(BLUE)[Docker]$(NC) Restarting bot..."
	docker compose down && docker compose up -d
	@echo "$(GREEN)[OK]$(NC) Bot restarted"

logs: ## Show logs in real-time
	@echo "$(BLUE)[Docker]$(NC) Displaying logs (Ctrl+C to quit)..."
	docker compose logs -f

shell: ## Open a shell in the container
	@echo "$(BLUE)[Docker]$(NC) Opening shell in container..."
	docker compose exec bot bash

clean: ## Clean containers, images, and volumes
	@echo "$(YELLOW)[Warning]$(NC) Cleaning Docker resources..."
	docker compose down -v --rmi local
	docker system prune -f
	@echo "$(GREEN)[OK]$(NC) Cleanup complete"

pull: ## Update Docker image from registry
	@echo "$(BLUE)[Docker]$(NC) Updating image..."
	docker compose pull
	@echo "$(GREEN)[OK]$(NC) Image updated"

# Development commands
test: ## Test Docker build
	@echo "$(BLUE)[Test]$(NC) Testing Docker build..."
	docker compose build --no-cache
	@echo "$(GREEN)[OK]$(NC) Test complete"

rebuild: ## Rebuild image completely
	@echo "$(BLUE)[Docker]$(NC) Full image rebuild..."
	docker compose build --no-cache
	@echo "$(GREEN)[OK]$(NC) Image rebuilt"

# Python commands (in container)
python: ## Run Python in container
	@echo "$(BLUE)[Python]$(NC) Opening Python in container..."
	docker compose exec bot python

pip-install: ## Install a Python package in the container
	@if [ -z "${package}" ]; then \
		@echo "$(RED)[Error]$(NC) Please specify a package: make pip-install package=<package-name>"; \
		@exit 1; \
	fi
	@echo "$(BLUE)[Python]$(NC) Installing ${package}..."
	docker compose exec bot pip install ${package}
	@echo "$(GREEN)[OK]$(NC) Package installed"

# File management
init-env: ## Create .env file from example
	@echo "$(BLUE)[Config]$(NC) Creating .env file..."
	@if [ ! -f .env ]; then \
		cp .env.example .env 2>/dev/null || \
		printf 'DISCORD_TOKEN=\nROOT_ME_API_KEY=\nTARGET_CHANNEL_ID=\nUSERS_LIST_FILE=users.json\n' > .env; \
	fi
	@echo "$(GREEN)[OK]$(NC) .env file created. Edit it before starting."

# Info commands
info: ## Display container information
	@echo "$(BLUE)[Info]$(NC) Container information:"
	docker compose ps
	docker images zoubivm-bot
	@echo ""
