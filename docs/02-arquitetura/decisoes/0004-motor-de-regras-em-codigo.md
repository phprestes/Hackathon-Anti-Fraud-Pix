---
title: "ADR 0004: Regras antifraude em código, uma classe por regra em src/rules/"
summary: Cada regra é uma classe pequena com código estável, família e método evaluate; o controller roda a lista registrada.
related: [../camadas.md, ../../05-motor/motor-de-regras.md, 0005-regras-puras-com-contexto-carregado.md]
sources: [Desafio Antifraude Pix (seção 2.2), slides do hackathon ("Motor de regras")]
---

# ADR 0004: Regras antifraude em código, uma classe por regra em `src/rules/`

> [Índice](../../README.md) › [Decisões](README.md) › 0004

**Status:** aceita

## Contexto

O motor precisa de várias regras independentes (limite, velocity, montante, perfil, contraparte), cada uma explicável e testável, e o time vai acrescentar e calibrar regras durante a madrugada. Os slides mostram o produto real como "no code", com regras definidas por cliente.

## Decisão

- Pasta nova `src/rules/`, uma regra por arquivo: `<familia>/<familia>_<sinal>_rule.py`, classe `<Sinal>Rule`.
- Toda regra herda de `BaseRule` e tem `code` estável (`LIMIT_NIGHT_AMOUNT`, `VELOCITY_DEVICE_COUNT`…), `family` e `evaluate(pix, context) -> RuleResult | None`. `None` quer dizer "não disparou".
- `RuleResult` carrega `code`, `decision` (`two_factor_required` ou `rejected`) e `reason` em português.
- A lista de regras ativas fica registrada num único lugar (`src/rules/__init__.py`). Regra nova entra ali e no [catálogo](../../05-motor/regras.md).
- `rules/` é parte da camada de regra de negócio: só o controller a chama.

## Alternativas descartadas

- **Regras como dados (tabela ou JSON) interpretadas em tempo de execução, "no code".**
  - **Preço:** um mini-interpretador para escrever e testar em 26 horas; erro de regra vira erro de dado, sem lint nem teste por regra.
  - **Ganharia se** cada cliente da QI precisasse editar as próprias regras sem deploy, como no produto real.
- **Todas as regras como `if` dentro do controller.**
  - **Preço:** um método de centenas de linhas; sem código estável por regra, o `metadata` não diz qual disparou.
  - **Ganharia se** fossem duas ou três regras fixas.
- **Score ponderado único (soma de pesos com cortes).**
  - **Preço:** explicar "por que 2FA" vira "a soma deu 63"; calibrar pesos sem dado rotulado é chute.
  - **Ganharia se** houvesse histórico com fraude confirmada para ajustar os pesos.

## Consequências

- Cada regra é testada por HTTP com um cenário que a dispara e outro que não.
- Score pode entrar depois como mais uma regra que lê os resultados das outras, sem mudar o contrato.
