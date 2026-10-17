VENV := .venv
BIN := $(VENV)/bin
COMPOSE := docker compose

# SQLAlchemy 2.0.23 breaks on Python 3.12+ (docs/06-operacao/rodando-localmente.md).
PYTHON_311 := $(shell command -v python3.11 2>/dev/null)

.DEFAULT_GOAL := help
.PHONY: help all up down stop reset rebuild ps logs shell install test test-cov lint check simulate clean

help: ## Lista os comandos
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

all: up test ## Sobe tudo e roda os testes (do clone ao verde)

up: ## Sobe api e db e espera ficarem healthy
	$(COMPOSE) up -d --build --wait

down: ## Para e remove os containers (mantém o volume)
	$(COMPOSE) down

stop: ## Para os containers sem removê-los
	$(COMPOSE) stop

reset: ## Recria o banco do zero (use após mudar database/database.sql)
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build --wait

rebuild: ## Reconstrói a imagem da api sem cache (use após mudar requirements.txt)
	$(COMPOSE) build --no-cache api
	$(COMPOSE) up -d --wait

ps: ## Mostra o estado dos containers
	$(COMPOSE) ps

logs: ## Acompanha o log da api
	$(COMPOSE) logs -f api

shell: ## Abre um shell no container da api
	$(COMPOSE) exec api sh

$(BIN)/pytest: requirements.txt requirements-dev.txt
ifdef PYTHON_311
	$(PYTHON_311) -m venv --clear $(VENV)
	$(BIN)/pip install -r requirements-dev.txt
else
	uv venv --clear -p 3.11 $(VENV)
	uv pip install -p $(VENV) -r requirements-dev.txt
endif
	@touch $@

install: $(BIN)/pytest ## Cria o .venv (Python 3.11) com as dependências de teste

test: install ## Roda os testes (precisa do make up antes)
	$(BIN)/pytest -v

test-cov: install ## Roda os testes com cobertura
	$(BIN)/pytest --cov

lint: install ## Roda o flake8
	$(BIN)/flake8 src tests

check: lint test ## Lint e testes

simulate: install ## Roda o simulador de calibração contra a api (depois, make reset limpa o banco)
	$(BIN)/python scripts/simulate.py

clean: ## Remove containers, volume, .venv e caches
	$(COMPOSE) down -v
	rm -rf $(VENV) .pytest_cache .coverage htmlcov
