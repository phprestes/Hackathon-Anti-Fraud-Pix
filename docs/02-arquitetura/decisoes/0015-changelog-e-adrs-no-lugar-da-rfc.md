---
title: "ADR 0015: CHANGELOG e ADRs no lugar da RFC"
summary: Sem RFC versionada; cada decisão é um ADR curto e cada mudança no repositório é uma linha no CHANGELOG.md, com autor e link para o porquê.
related: [README.md, ../../../CHANGELOG.md, 0014-repositorio-ai-friendly.md]
sources: [Desafio Antifraude Pix (seção 5 "Não precisa entregar o documento"), keepachangelog.com]
---

# ADR 0015: CHANGELOG e ADRs no lugar da RFC

> [Índice](../../README.md) › [Decisões](README.md) › 0015

**Status:** aceita

## Contexto

O enunciado pede o processo de RFC ("troquem ideias e definam o escopo"), mas diz que não precisa entregar o documento. Agentes e pessoas mudam o repositório em paralelo durante a madrugada; na apresentação, o time precisa contar o que fez e por quê.

## Decisão

- **Sem `docs/rfc/`.** A discussão de escopo vira ADRs, um por decisão, lidos em dois minutos cada. ADR nasce `proposta` e vira `aceita` quando o código que a implementa entra.
- **`CHANGELOG.md` na raiz**, inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/): a seção `[Não lançado]` recebe toda mudança, agrupada por data, numa tabela com tipo, mudança, arquivos, porquê (link para ADR ou doc) e autor.
- Toda mudança feita por agente de IA leva o autor `agente (<ferramenta>)`, para ser filtrável com `grep agente CHANGELOG.md`.
- O changelog registra *o que mudou*; o porquê longo fica no ADR ou no doc linkado.

## Alternativas descartadas

- **RFC única em `docs/rfc/RFC.md`, como na fase 1.**
  - **Preço:** um documento longo que envelhece a cada calibragem; o enunciado não pede.
  - **Ganharia se** a entrega exigisse o PDF.
- **Só o histórico do Git.**
  - **Preço:** a banca e o agente não leem `git log`; mensagens curtas não dizem o porquê nem quem (humano ou agente).
  - **Ganharia se** só houvesse humanos e commits bem escritos.

## Consequências

- Toda tarefa termina com uma linha no `CHANGELOG.md` ([skill registrar-mudanca](../../../.agents/skills/registrar-mudanca/SKILL.md)).
- No fim do hackathon, a seção `[Não lançado]` vira `[1.0.0] - 2026-10-18`.
