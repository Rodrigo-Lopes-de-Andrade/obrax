# Obrax — atalhos de desenvolvimento. Ver docs/CLAUDE.md > Setup e Execução.
# Backend roda via `uv` dentro de backend/; frontend via pnpm dentro de frontend/.
# Alvos ainda não disponíveis nesta fase (gen-types, build de produção) chegam
# com as tarefas de frontend/DevOps das próximas sprints.

.DEFAULT_GOAL := help
BACKEND := backend
FRONTEND := frontend

.PHONY: help up down migrate dev dev-backend dev-frontend test lint fmt

help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Sobe Postgres + Redis (docker compose)
	docker compose up -d

down: ## Derruba a stack local
	docker compose down

migrate: ## Aplica migrations (alembic upgrade head)
	cd $(BACKEND) && uv run alembic upgrade head

dev: ## Backend + frontend juntos
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend: ## FastAPI com reload (uvicorn)
	cd $(BACKEND) && uv run uvicorn app.main:app --reload

dev-frontend: ## Next.js dev server
	cd $(FRONTEND) && pnpm dev

test: ## Testes do backend (pytest)
	cd $(BACKEND) && uv run pytest

lint: ## Lint + format check + typecheck do backend
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check . && uv run mypy app

fmt: ## Aplica ruff format no backend
	cd $(BACKEND) && uv run ruff format .
