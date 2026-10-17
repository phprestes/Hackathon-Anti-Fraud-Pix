---
name: revisar-mudanca
description: Use antes de declarar uma tarefa pronta ou abrir PR. Checklist das regras do projeto, com o comando que verifica cada uma.
---

# Revisar mudança

Rode e leia a saída; não declare pronto sem ela.

```bash
make reset check                                     # R2 + lint + testes, banco do zero
grep -rn "from src\|import src" tests/               # R1: precisa voltar vazio
grep -rn "raise" src/resources/                      # resource sem raise: vazio
grep -rn "float" src/                                # R6: dinheiro nunca em float
grep -rnE "repositories|database|environ|now\(\)" src/rules/   # regra pura: vazio
```

Depois confira à mão:

- [ ] Cada regra nova tem um teste que não dispara e um que dispara.
- [ ] Nenhum número mágico em `src/rules/`; parâmetros em `src/constants.py`.
- [ ] Nenhum DTO devolve `id` ou FK (R5).
- [ ] `session.commit()` só no controller, como última linha antes do `return`.
- [ ] Regra, rota, erro, tabela ou decisão nova estão em `regras.md` + README, `rotas.md`, `erros.md`, `modelo.md` ou num ADR.
- [ ] Linha no [`CHANGELOG.md`](../../../CHANGELOG.md) com autor ([registrar-mudanca](../registrar-mudanca/SKILL.md)).
- [ ] Nenhum segredo no diff; `.env` fora do Git.
- [ ] Commit em Conventional Commits, sem trailer de ferramenta.

Checklist completo de PR: [docs/contribuindo.md](../../../docs/contribuindo.md#checklist-de-pr).
