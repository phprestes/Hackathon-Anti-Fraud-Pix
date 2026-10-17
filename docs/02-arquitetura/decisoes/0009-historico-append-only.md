---
title: "ADR 0009: Histórico append-only, com o Pix em colunas e o payload original em JSONB"
summary: Todo Pix recebido é gravado, inclusive os reprovados; colunas tipadas e indexadas para as janelas das regras; análise e disparos em tabelas próprias.
related: [../../04-dados/modelo.md, 0005-regras-puras-com-contexto-carregado.md]
sources: [Desafio Antifraude Pix (seção 4 "Banco próprio com o histórico de tudo que chegou", critério 3), Autoestudo Aula 2 (append-only)]
---

# ADR 0009: Histórico append-only, com o Pix em colunas e o payload original em JSONB

> [Índice](../../README.md) › [Decisões](README.md) › 0009

**Status:** proposta

## Contexto

O banco precisa guardar "tudo que chegou" e servir as consultas de histórico das regras em milissegundos. A modelagem de dados é critério de avaliação.

## Decisão

- `pix_transaction`: uma linha por Pix recebido, com cada campo do payload em coluna tipada (contas, documentos, aparelho, IP, geolocalização) e o corpo original em `payload JSONB`.
- `pix_analysis`: uma por Pix, com `analysis_key` (UUID), status e `metadata`.
- `pix_analysis_reason`: uma linha por regra disparada.
- `analysis_status`: enumerador (`approved`, `two_factor_required`, `rejected`), como no padrão do Base Service.
- Tudo só recebe `INSERT`. Índices compostos para as janelas: `(source_document_number, transaction_date)`, `(device_id, transaction_date)`, `(destination_document_number, transaction_date)`.
- Os dados de conta são **retrato do momento** do Pix, sem tabela `account` normalizada.

## Alternativas descartadas

- **Só o payload em JSONB.**
  - **Preço:** consulta de velocity em campo JSON, sem tipo nem índice natural; a banca não vê modelagem.
  - **Ganharia se** o payload mudasse de formato toda semana.
- **Tabelas `account` e `device` normalizadas, com upsert a cada Pix.**
  - **Preço:** escrita extra por Pix, e `opening_date` de uma conta de outro banco pode vir diferente em dois Pix; qual vale?
  - **Ganharia se** as contas fossem cadastradas por nós (onboarding, fora do escopo).
- **Gravar só os Pix aprovados.**
  - **Preço:** perde as tentativas, que são o sinal mais forte de fraude em andamento.
  - **Ganharia se** o histórico servisse só para extrato.

## Consequências

- O `GET` lê `pix_analysis` + `pix_analysis_reason`, sem recalcular nada.
- Reprocessar o histórico com regras novas é possível a partir do `payload`.
