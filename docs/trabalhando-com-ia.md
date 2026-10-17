---
title: Trabalhando com IA
summary: Arquivos para agentes de código (AGENTS.md, .agents/skills, llms.txt, CHANGELOG) e regras de uso.
related: [contribuindo.md, ../AGENTS.md, ../llms.txt, 02-arquitetura/decisoes/0014-repositorio-ai-friendly.md]
sources: [agents.md, llmstxt.org, agentskills.io, keepachangelog.com]
---

# Trabalhando com IA

> [Índice](README.md) › Trabalhando com IA
>
> **Responde a:** o que cada arquivo para agentes faz? como usar um agente aqui sem quebrar as regras? como saber o que o agente mudou?

A decisão está na [ADR 0014](02-arquitetura/decisoes/0014-repositorio-ai-friendly.md).

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| [`AGENTS.md`](../AGENTS.md) | Comandos, regras, camadas, fluxo e limites. Formato [agents.md](https://agents.md) |
| [`.agents/skills/`](../.agents/README.md) | Receitas: nova regra, novo erro, nova decisão, registrar mudança, revisar mudança |
| [`llms.txt`](../llms.txt) | Uma linha por documento. Formato [llmstxt.org](https://llmstxt.org) |
| [`CHANGELOG.md`](../CHANGELOG.md) | Toda mudança, com autor; as do agente filtráveis com `grep agente CHANGELOG.md` |
| `docs/**` | Front-matter (`title`, `summary`, `related`, `sources`) e linha *Responde a* em todo documento |
| [`Makefile`](../Makefile) | Um comando por tarefa |

## Uma fonte para todas as ferramentas

| Ferramenta | Arquivo local (fora do Git) | Conteúdo |
|---|---|---|
| Codex, Cursor, Aider, Copilot (agente) | — | leem `AGENTS.md` direto |
| Claude Code | `CLAUDE.md` | `@AGENTS.md` |
| Gemini CLI | `GEMINI.md` | `@AGENTS.md` |

Esses arquivos estão em `.git/info/exclude`. Para ferramentas que procuram skills em pasta própria:

```bash
mkdir -p .claude && ln -s ../.agents/skills .claude/skills
```

## Regras de uso

- Quem commita responde pelo código, escrito por agente ou não.
- TDD vale para o agente: teste vermelho primeiro.
- Agente não muda parâmetro de regra sem pedido; calibrar é decisão do time.
- Toda mudança do agente termina com uma linha no `CHANGELOG.md` com autor `agente (<ferramenta>)`.
- `make reset check` antes de declarar pronto.
- Nada de `.env`, token real ou dado de cliente no prompt.

## Manutenção

- Mudou regra, comando ou camada: `AGENTS.md` no mesmo commit.
- Tarefa que o agente erra com frequência vira skill.
- Documento novo entra no [índice](README.md) e no `llms.txt`.
