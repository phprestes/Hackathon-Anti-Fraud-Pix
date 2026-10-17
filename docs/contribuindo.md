---
title: Como contribuir
summary: Clean Code aplicado às camadas e às regras, nomes, Conventional Commits, CHANGELOG e checklist de PR.
related: [02-arquitetura/camadas.md, 07-testes/estrategia.md, trabalhando-com-ia.md, ../CHANGELOG.md]
sources: [bootcamp-base-api (convenções), Aula 1 tarde, Aula 3 tarde (TDD), Projeto fase 1 (contribuindo)]
---

# Como contribuir

> [Índice](README.md) › Contribuindo
>
> **Responde a:** como nomear? como comentar? como commitar? como registrar a mudança? o que conferir antes do PR?

## Clean Code nas camadas

- **Uma responsabilidade por camada** ([camadas](02-arquitetura/camadas.md)). `grep raise src/resources/` volta vazio; repository não decide; regra não consulta banco.
- **Uma regra por classe, um sinal por regra.** Se o nome precisa de "e", são duas regras.
- **Funções pequenas com nome de intenção.** Métodos privados do controller dizem o passo: `_find_replay`, `_build_context`, `_decide`. No repository, o nome diz a busca: `count_by_source_since`, `sum_by_source_since`.
- **Erro é classe, não string**, com o próximo código livre ([erros](03-api/erros.md)).
- **Sem número mágico.** Todo limite, janela e corte vem de `src/constants.py` ([ADR 0008](02-arquitetura/decisoes/0008-parametros-de-regra-por-ambiente.md)).
- **Comentário explica o porquê, nunca o quê**, em uma ou duas linhas. Racional de parâmetro mora no [catálogo de regras](05-motor/regras.md), não no código.
- **Nada de código morto ou comentado.** O Git guarda o histórico.

## Nomes

| Item | Padrão | Exemplo |
|---|---|---|
| Arquivo | snake_case, singular | `pix_transaction_controller.py` |
| Classe | `<Recurso><Camada>` | `PixTransactionController`, `PixAnalysisDTO` |
| Regra (arquivo) | `<familia>_<sinal>_rule.py` | `velocity_source_count_rule.py` |
| Regra (classe) | `<Familia><Sinal>Rule` | `VelocitySourceCountRule` |
| Regra (código) | `<FAMILIA>_<SINAL>` | `VELOCITY_SOURCE_COUNT` |
| Parâmetro | `RULE_<…>` com unidade no fim | `RULE_VELOCITY_WINDOW_MINUTES`, `RULE_LIMIT_NIGHT_AMOUNT_CENTS` |
| Schema | `<verbo>_<recurso>.json` | `post_pix_transaction.json` |
| Tabela | snake_case, singular | `pix_analysis_reason` |
| Teste | `test_<ação>_<cenário>_returns_<status ou decisão>` | `test_post_pix_from_shared_device_returns_rejected` |

Código, rotas, campos e códigos de regra em inglês. Prosa da documentação, `reason` das regras e `translation` dos erros em português.

## Commits: Conventional Commits

```
<tipo>(<escopo>): <resumo no imperativo, ≤ 72 caracteres>
```

- **Tipos:** `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `build`.
- **Escopos:** `pix`, `rules`, `db`, `infra`, `docs`, `agents`.
- Sem trailers de co-autoria ou de ferramenta.

```
feat(rules): add VELOCITY_SOURCE_COUNT with 10-minute window
docs(rules): justify night limit of R$ 1.000
```

## CHANGELOG

Toda mudança que alguém precisa saber depois ganha uma linha no [`CHANGELOG.md`](../CHANGELOG.md), na tabela da data de hoje dentro de `[Não lançado]` ([ADR 0015](02-arquitetura/decisoes/0015-changelog-e-adrs-no-lugar-da-rfc.md)). Calibragem de parâmetro sempre entra. A [skill registrar-mudanca](../.agents/skills/registrar-mudanca/SKILL.md) tem o formato.

## Checklist de PR

- [ ] Cada regra nova tem um teste que não dispara e um que dispara.
- [ ] Nenhum teste importa `src/` (R1).
- [ ] `make reset check` passa: banco do zero, lint limpo, testes verdes (R2).
- [ ] Regra nova ou parâmetro novo está no [catálogo](05-motor/regras.md) **e** no README, com o porquê.
- [ ] Erro novo está no [catálogo de erros](03-api/erros.md); decisão nova virou ADR.
- [ ] Linha no `CHANGELOG.md`.
- [ ] Regra, comando ou camada mudou? O [`AGENTS.md`](../AGENTS.md) acompanha.
- [ ] Nenhum segredo no diff.
