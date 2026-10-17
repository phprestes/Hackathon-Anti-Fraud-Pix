VENV := .venv
BIN := $(VENV)/bin
COMPOSE := docker compose

# SQLAlchemy 2.0.23 breaks on Python 3.12+ (docs/06-operacao/rodando-localmente.md).
PYTHON_311 := $(shell command -v python3.11 2>/dev/null)

.DEFAULT_GOAL := help
.PHONY: help all up down stop reset rebuild ps logs shell install test test-cov lint check simulate events backtest parity calibrate calibrate-check train-models-mock pixsim-datasets train-graphsage train-hmm clean pixsim validate-pixsim pixsim-parity

help: ## Lista os comandos
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

all: up test ## Sobe tudo e roda os testes (do clone ao verde)

up: ## Sobe api, db e worker (religa o worker parado pelo make test)
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

logs: ## Acompanha o log da api e do worker
	$(COMPOSE) logs -f api worker

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

test: install ## Roda os testes com o worker parado (os testes chamam 1 ciclo); religue com make up
	$(COMPOSE) stop worker
	$(BIN)/pytest -v

test-cov: install ## Roda os testes com cobertura
	$(COMPOSE) stop worker
	$(BIN)/pytest --cov

lint: install ## Roda o flake8
	$(BIN)/flake8 src tests

check: lint test ## Lint e testes

simulate: install ## Roda o simulador de calibração contra a api (depois, make reset limpa o banco)
	$(BIN)/python scripts/simulate.py

events: install ## Gera scripts/out/events.jsonl (seed 42, 60 pagadores, 7 dias)
	$(BIN)/python scripts/simulate.py --generate-only --events scripts/out/events.jsonl --seed 42 --payers 60 --days 7

backtest: events ## Roda o backtest em memória sobre scripts/out/events.jsonl (sem HTTP, sem banco)
	$(BIN)/python scripts/backtest.py scripts/out/events.jsonl

parity: events ## Zera o banco, para o worker e compara API (SQL) x backtest (memória) Pix a Pix
	$(MAKE) reset
	$(COMPOSE) stop worker
	$(BIN)/python scripts/parity.py scripts/out/events.jsonl

calibrate: install ## Grid de parametros sobre o backtest; grava scripts/out/calibration.md/.json (sem banco)
	$(BIN)/python scripts/calibrate.py

calibrate-check: install ## Trava de regressao: backtest com os padroes contra scripts/calibration-gate.json
	$(BIN)/python scripts/calibrate.py --check

DATASET_ARGS := --payers 300 --days 14

datasets: install ## Gera os eventos e as features de treino (seed 42), teste (seed 7) e teste perturbado (seed 7)
	$(BIN)/python scripts/simulate.py --generate-only --events scripts/out/train-events.jsonl --seed 42 $(DATASET_ARGS)
	$(BIN)/python scripts/simulate.py --generate-only --events scripts/out/test-events.jsonl --seed 7 $(DATASET_ARGS)
	$(BIN)/python scripts/simulate.py --generate-only --events scripts/out/test-perturbed-events.jsonl --seed 7 --fraud-variant perturbed $(DATASET_ARGS)
	$(BIN)/python scripts/export_features.py scripts/out/train-events.jsonl scripts/out/train-features.jsonl
	$(BIN)/python scripts/export_features.py scripts/out/test-events.jsonl scripts/out/test-features.jsonl
	$(BIN)/python scripts/export_features.py scripts/out/test-perturbed-events.jsonl scripts/out/test-perturbed-features.jsonl

train-models: datasets pixsim-datasets ## Treina LogReg e LightGBM no mundo A do PixSim, avalia no B e no nosso simulador e instala os JSON
	ulimit -v 2500000; $(BIN)/python scripts/train_models.py --source pixsim --install logreg lightgbm

train-models-mock: datasets ## Treina no nosso simulador (rótulos nossos); SOBRESCREVE os modelos do PixSim em src/rules/model/
	$(BIN)/python scripts/train_models.py

train-graphsage: datasets ## Treina o GraphSAGE (numpy, ~5 min) e escreve src/worker/model/graphsage.json e a secao em scripts/model-results.md
	$(BIN)/python scripts/train_graphsage.py scripts/out/train-events.jsonl

train-hmm: datasets ## Treina o HMM de sequencia (numpy) e escreve src/worker/model/hmm.json e a secao em scripts/model-results.md
	$(BIN)/python scripts/train_hmm.py scripts/out/train-events.jsonl

model-parity: install ## Compara os avaliadores em Python puro com sklearn/lightgbm no conjunto de teste
	$(BIN)/python scripts/check_model_parity.py

clean: ## Remove containers, volume, .venv e caches
	$(COMPOSE) down -v
	rm -rf $(VENV) .pytest_cache .coverage htmlcov

analyze: install ## Gera docs/05-motor/analises.md (log-normalidade, dispersao, PSI, sensibilidade; sem API e sem banco)
	$(BIN)/python scripts/analyze.py

calibrate-cost: install ## Grid de parametros pelo custo assimetrico (scripts/cost-model.json); grava scripts/out/calibration.md/.json (sem banco)
	$(BIN)/python scripts/calibrate.py --objective cost

PIXSIM_DIR := scripts/out/pixsim
PIXSIM_SEED ?= 20260910
PIXSIM_OUT ?= $(PIXSIM_DIR)/data

pixsim: ## Clona o PixSim (SHA fixo), cria o venv proprio e gera um mundo reduzido (PIXSIM_SEED, PIXSIM_OUT; padrao: mundo A em scripts/out/pixsim/data)
	scripts/pixsim_setup.sh
	ulimit -v 3000000; OPENBLAS_NUM_THREADS=1 $(PIXSIM_DIR)/.venv/bin/python -I scripts/pixsim_export.py --seed $(PIXSIM_SEED) --out $(PIXSIM_OUT)

validate-pixsim: install ## Adaptador, backtest e relatorio (atualiza docs/05-motor/validacao-pixsim.md)
	test -f $(PIXSIM_DIR)/data/transactions.csv || $(MAKE) pixsim
	$(BIN)/python scripts/pixsim_adapter.py
	ulimit -v 2500000; $(BIN)/python scripts/backtest.py $(PIXSIM_DIR)/events.jsonl --json $(PIXSIM_DIR)/backtest.json > /dev/null
	ulimit -v 2500000; $(BIN)/python scripts/pixsim_report.py

pixsim-datasets: install ## Gera os mundos A e B do PixSim (se faltarem) e exporta as features de treino e teste
	test -f $(PIXSIM_DIR)/data/transactions.csv || $(MAKE) pixsim
	test -f $(PIXSIM_DIR)/data-b/transactions.csv || $(MAKE) pixsim PIXSIM_SEED=20261017 PIXSIM_OUT=$(PIXSIM_DIR)/data-b
	test -f $(PIXSIM_DIR)/events.jsonl || $(BIN)/python scripts/pixsim_adapter.py
	test -f $(PIXSIM_DIR)/events-b.jsonl || $(BIN)/python scripts/pixsim_adapter.py --data $(PIXSIM_DIR)/data-b --out $(PIXSIM_DIR)/events-b.jsonl
	ulimit -v 2500000; $(BIN)/python scripts/export_features.py $(PIXSIM_DIR)/events.jsonl $(PIXSIM_DIR)/features-a.jsonl
	ulimit -v 2500000; $(BIN)/python scripts/export_features.py $(PIXSIM_DIR)/events-b.jsonl $(PIXSIM_DIR)/features-b.jsonl

pixsim-parity: install ## Zera o banco e compara API x backtest nas 500 linhas de scripts/out/pixsim/events-parity.jsonl
	n=$$(grep -n '"burn_in":false' $(PIXSIM_DIR)/events.jsonl | grep -v '"label":"legit"' | head -1 | cut -d: -f1); sed -n "$$((n-250)),$$((n+249))p" $(PIXSIM_DIR)/events.jsonl > $(PIXSIM_DIR)/events-parity.jsonl
	$(MAKE) reset
	$(COMPOSE) stop worker
	$(BIN)/python scripts/parity.py $(PIXSIM_DIR)/events-parity.jsonl
