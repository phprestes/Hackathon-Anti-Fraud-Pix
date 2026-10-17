# AGENTS.md

Instruções para agentes de código, no formato [agents.md](https://agents.md). Pessoas começam pelo [README](README.md); o porquê deste arquivo está em [docs/trabalhando-com-ia.md](docs/trabalhando-com-ia.md).

## Projeto

Motor antifraude de Pix do Hackathon QI Tech 2026: `POST /pix/transaction` recebe um Pix e devolve `{key, status, metadata}` com `approved`, `two_factor_required` ou `rejected`; `GET /pix/transaction/{id}` devolve a análise gravada. Python 3.11, FastAPI, SQLAlchemy 2, PostgreSQL 16, jsonschema, Docker Compose (`api`, `db`). Nasceu do `bootcamp-base-api` da Aula 1; o exemplo `sample_entity` ainda está no código até a rota do Pix substituí-lo.

Entrega: domingo 18/10, até 12:00, link do repositório no Slack. A banca começa pelo README.

A documentação é a fonte da verdade. Comece por [docs/README.md](docs/README.md) ou pelo [llms.txt](llms.txt). Enunciado em [docs/01-contexto/enunciado.md](docs/01-contexto/enunciado.md). Decisões em [docs/02-arquitetura/decisoes/](docs/02-arquitetura/decisoes/README.md). Não existe RFC.

## Comandos

```bash
make                # lista os alvos
make all            # sobe api/db (espera healthy), cria .venv 3.11 e roda pytest -v
make up             # só sobe
make test           # só testa (precisa do make up)
make lint           # flake8 src tests; precisa sair limpo
make check          # lint + test
make reset          # depois de mudar database/database.sql
make rebuild        # depois de mudar requirements.txt
make logs           # log da api
```

Use Python 3.11: o SQLAlchemy 2.0.23 quebra no 3.12+. O `make install` resolve isso.

## Regras que não se negociam

- **R1.** Teste nunca importa de `src/` e nunca lê o banco. Cenário e histórico nascem por `POST /pix/transaction`.
- **R2.** Um comando sobe tudo numa máquina Linux limpa (`make all`).
- **R3.** Recusa da API é classe em `src/errors/custom_errors.py` com código `QIT` único; próximo livre em [docs/03-api/erros.md](docs/03-api/erros.md). Decisão `rejected` **não** é erro: sai 201 ([ADR 0003](docs/02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md)).
- **R4.** Tabelas append-only: só `INSERT`. Todo Pix recebido é gravado, inclusive os reprovados.
- **R5.** `id` do banco nunca sai. A saída tem `key` (UUID da análise); a consulta usa o `id` do Pix.
- **R6.** Dinheiro é `BIGINT` em centavos; nunca float.

## Motor de regras

- Uma regra = uma classe em `src/rules/<familia>_<sinal>_rule.py`, com `code`, `family` e `evaluate(pix, context) -> RuleResult | None`.
- Regra é pura: não importa `repositories`, `database`, `os.environ` nem chama `datetime.now()`. O "agora" é o `transaction_date` do Pix ([ADR 0007](docs/02-arquitetura/decisoes/0007-relogio-da-transacao.md)).
- O controller monta o `RuleContext` com agregados do repository, roda **todas** as regras de `ACTIVE_RULES`, e a decisão mais severa vence (`rejected` > `two_factor_required` > `approved`). Todos os disparos vão para `metadata.reasons`.
- Parâmetro de regra é constante `RULE_*` em `src/constants.py`, lida do ambiente. Nada de número mágico.
- **Não mude parâmetro de regra sem pedido explícito.** Calibrar é decisão do time e precisa de porquê no [catálogo](docs/05-motor/regras.md) e no README.

## Camadas

| Pasta | Faz | Não faz |
|---|---|---|
| `resources/` | HTTP de entrada e saída; escolhe 201 ou 200 | regra, `raise` |
| `controllers/` | idempotência, contexto, regras, decisão; único `session.commit()`, como última linha antes do `return` | SQL direto |
| `rules/` | decidir se uma regra dispara | banco, ambiente, relógio |
| `repositories/` | consultas e agregados por janela | decidir |
| `schemas/` | JSON Schema com `additionalProperties: false` | regra |
| `dtos/` | `{key, status, metadata}` | serializar `id` ou FK |

Detalhe em [docs/02-arquitetura/camadas.md](docs/02-arquitetura/camadas.md).

## Como trabalhar

- **TDD.** Nenhuma linha nova em `src/` sem teste vermelho pedindo. Toda regra tem um teste que não dispara e um que dispara.
- **Nome de teste:** `test_<ação>_<cenário>_returns_<status ou decisão>`, com docstring citando o código da regra ou a exigência (E/R).
- **Idioma:** código, rotas, campos e códigos de regra em inglês; prosa da documentação, `reason` e `translation` em português.
- **Comentários** explicam o porquê, em uma ou duas linhas. Racional longo vai para `docs/`.
- **Documentação junto com o código:** regra nova → [regras.md](docs/05-motor/regras.md) + README; rota → [rotas.md](docs/03-api/rotas.md); erro → [erros.md](docs/03-api/erros.md); tabela → [modelo.md](docs/04-dados/modelo.md); decisão → ADR + `llms.txt`.
- **CHANGELOG obrigatório.** Toda tarefa termina com uma linha em [`CHANGELOG.md`](CHANGELOG.md), seção `[Não lançado]`, tabela da data de hoje, autor `agente (<ferramenta>)`. Formato na skill [registrar-mudanca](.agents/skills/registrar-mudanca/SKILL.md).
- **ADR muda de status** de `proposta` para `aceita` quando o código que a implementa entra.
- **Commits:** Conventional Commits (`feat(rules): …`), sem trailers de co-autoria ou de ferramenta. Não faça commit sem pedido.
- **Antes de dizer que terminou:** `make reset check` precisa passar.

## Skills

Receitas em [`.agents/skills/`](.agents/README.md), uma pasta por tarefa com um `SKILL.md`. Leia a skill da tarefa antes de começar: `nova-regra`, `novo-erro`, `nova-decisao`, `registrar-mudanca`, `revisar-mudanca`.

## Limites

- Não leia, crie nem versione `.env` com segredo real.
- Não altere `docker-compose.yml`, `Dockerfile` ou `database/database.sql` sem pedido explícito: mexem em R2.
- Não apague nem reescreva teste existente para fazê-lo passar.
- Não edite [docs/01-contexto/enunciado.md](docs/01-contexto/enunciado.md) além de correção de transcrição: é cópia dos PDFs.
