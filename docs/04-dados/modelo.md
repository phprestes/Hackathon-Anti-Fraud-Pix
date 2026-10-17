---
title: Modelo de dados
summary: Tabelas propostas para o histórico de Pix, análises e motivos; DDL de referência, índices e invariantes.
related: [../02-arquitetura/decisoes/0009-historico-append-only.md, ../02-arquitetura/decisoes/0011-uuid-key-publica.md, ../05-motor/regras.md]
sources: [Desafio Antifraude Pix (seções 3 e 4, critério 3), bootcamp-base-api database.sql]
---

# Modelo de dados

> [Índice](../README.md) › Dados › Modelo
>
> **Responde a:** quais tabelas existem? por que cada coluna? quais índices servem às regras?

**Estado:** proposta. O `database/database.sql` atual ainda é o do Base Service; esta DDL entra junto com a rota do Pix.

## Diagrama

```mermaid
erDiagram
    pix_transaction ||--|| pix_analysis : "tem uma"
    pix_analysis ||--o{ pix_analysis_reason : "disparou"
    analysis_status ||--o{ pix_analysis : "status"
    analysis_status ||--o{ pix_analysis_reason : "decisão"
```

## DDL de referência

```sql
CREATE TABLE analysis_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    severity                        SMALLINT NOT NULL UNIQUE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO analysis_status (enumerator, severity) VALUES
('approved', 0),
('two_factor_required', 1),
('rejected', 2);

CREATE TABLE pix_transaction(
    id                              SERIAL PRIMARY KEY,
    pix_id                          VARCHAR(100) NOT NULL UNIQUE,
    amount                          BIGINT NOT NULL CHECK (amount > 0),
    transaction_date                TIMESTAMPTZ NOT NULL,
    source_branch                   VARCHAR(10) NOT NULL,
    source_account_number           VARCHAR(20) NOT NULL,
    source_opening_date             TIMESTAMPTZ NOT NULL,
    source_document_number          VARCHAR(18) NOT NULL,
    destination_participant         CHAR(8) NOT NULL,
    destination_branch              VARCHAR(10) NOT NULL,
    destination_account_number      VARCHAR(20) NOT NULL,
    destination_opening_date        TIMESTAMPTZ NOT NULL,
    destination_document_number     VARCHAR(18) NOT NULL,
    device_id                       VARCHAR(100) NOT NULL,
    channel                         VARCHAR(30) NOT NULL,
    ip                              INET NOT NULL,
    latitude                        NUMERIC(9,6),
    longitude                       NUMERIC(9,6),
    payload                         JSONB NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE INDEX pix_transaction_source_date_idx      ON pix_transaction (source_document_number, transaction_date);
CREATE INDEX pix_transaction_device_date_idx      ON pix_transaction (device_id, transaction_date);
CREATE INDEX pix_transaction_destination_date_idx ON pix_transaction (destination_document_number, transaction_date);

CREATE TABLE pix_analysis(
    id                              SERIAL PRIMARY KEY,
    analysis_key                    CHAR(36) NOT NULL UNIQUE,
    pix_transaction_id              INTEGER NOT NULL UNIQUE REFERENCES pix_transaction(id),
    status_id                       INTEGER NOT NULL REFERENCES analysis_status(id),
    metadata                        JSONB NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE pix_analysis_reason(
    id                              SERIAL PRIMARY KEY,
    pix_analysis_id                 INTEGER NOT NULL REFERENCES pix_analysis(id),
    rule_code                       VARCHAR(60) NOT NULL,
    decision_status_id              INTEGER NOT NULL REFERENCES analysis_status(id),
    reason                          TEXT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);
```

## Por que cada escolha

| Escolha | Porquê |
|---|---|
| Colunas tipadas + `payload JSONB` | Colunas para consultar e indexar; JSONB para reprocessar e para a idempotência comparar o corpo ([ADR 0009](../02-arquitetura/decisoes/0009-historico-append-only.md)) |
| `pix_id UNIQUE` | Idempotência e corrida resolvidas pelo banco ([ADR 0012](../02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)) |
| `TIMESTAMPTZ` em `transaction_date` | O fuso vem no payload e importa para a regra noturna ([ADR 0007](../02-arquitetura/decisoes/0007-relogio-da-transacao.md)) |
| `BIGINT` + `CHECK (amount > 0)` | Centavos, sem float ([ADR 0010](../02-arquitetura/decisoes/0010-dinheiro-em-centavos.md)) |
| `INET` em `ip` | Valida o formato e permite agrupar por faixa |
| `analysis_status.severity` | A regra "mais severa vence" vira `ORDER BY severity` sem lista no código ([ADR 0006](../02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md)) |
| `pix_analysis` separada de `pix_transaction` | O fato (o Pix) e a opinião (a análise) têm ciclos diferentes; reanálise futura não reescreve o fato |
| `pix_analysis_reason` em tabela | Calibrar uma regra é contar os disparos dela com SQL, sem abrir JSON |
| Índices `(documento/aparelho, transaction_date)` | Cada regra de janela é um range scan no índice |

## Invariantes

- Todas as tabelas só recebem `INSERT` (R4).
- Todo `pix_transaction` tem exatamente um `pix_analysis`, gravados no mesmo commit.
- `analysis_key` e `pix_id` são os únicos identificadores que saem da API (R5).
