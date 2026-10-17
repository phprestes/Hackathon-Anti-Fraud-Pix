---
title: "ADR 0014: Repositório AI-friendly"
summary: AGENTS.md é a fonte única de instruções para agentes; receitas em .agents/skills/; llms.txt como mapa; arquivos de ferramenta ficam locais.
related: [../../trabalhando-com-ia.md, ../../contribuindo.md, 0015-changelog-e-adrs-no-lugar-da-rfc.md]
sources: [agents.md, llmstxt.org, agentskills.io, Projeto fase 1 (ADR 0008)]
---

# ADR 0014: Repositório AI-friendly

> [Índice](../../README.md) › [Decisões](README.md) › 0014

**Status:** aceita

## Contexto

São 26 horas, várias pessoas e vários agentes de código escrevendo em paralelo. Sem instrução escrita, o agente põe regra no resource, importa `src/` no teste, inventa código de erro e muda parâmetro sem registrar.

## Decisão

- **`AGENTS.md` na raiz**: comandos, regras, camadas, fluxo e limites. Formato aberto [agents.md](https://agents.md).
- **`.agents/skills/<tarefa>/SKILL.md`**: receitas das tarefas recorrentes deste projeto (nova regra, novo erro, nova decisão, registrar mudança, revisar mudança).
- **`llms.txt`**: uma linha por documento.
- **Todo documento** abre com front-matter (`title`, `summary`, `related`, `sources`) e a linha *Responde a*.
- `CLAUDE.md`, `GEMINI.md` e `.cursor/` ficam fora do Git (`.git/info/exclude`) e só apontam para o `AGENTS.md`.

## Alternativas descartadas

- **Um arquivo versionado por ferramenta.**
  - **Preço:** o mesmo conteúdo em vários lugares, que divergem no primeiro PR esquecido.
  - **Ganharia se** o time inteiro usasse uma só ferramenta.
- **Nada específico; o agente lê `docs/`.**
  - **Preço:** gasta contexto e ainda erra regra escondida.
  - **Ganharia se** o projeto coubesse inteiro no contexto.

## Consequências

- Mudou regra, comando ou camada: o `AGENTS.md` muda no mesmo commit. Em divergência, vale o documento de origem em `docs/`.
