---
title: "ADR 0008: Parâmetros de regra em src/constants.py, lidos do ambiente"
summary: Todo limite, janela e corte de regra tem nome, valor padrão justificado e pode ser trocado por variável de ambiente.
related: [../../05-motor/regras.md, ../../06-operacao/rodando-localmente.md]
sources: [bootcamp-base-api (constants.py), Desafio Antifraude Pix ("Expliquem o porquê de cada parâmetro")]
---

# ADR 0008: Parâmetros de regra em `src/constants.py`, lidos do ambiente

> [Índice](../../README.md) › [Decisões](README.md) › 0008

**Status:** aceita

## Contexto

A banca lê "o porquê de cada parâmetro". Calibrar no meio da madrugada não pode exigir caçar números espalhados no código. O Base Service já lê configuração do ambiente em `src/constants.py`.

## Decisão

- Cada parâmetro vira uma constante `RULE_<CODIGO>_<NOME>` em `src/constants.py`, lida do ambiente com padrão: `RULE_LIMIT_NIGHT_AMOUNT_CENTS = int(os.environ.get(..., "100000"))`.
- O valor padrão e o porquê dele ficam na coluna "Parâmetros" do [catálogo de regras](../../05-motor/regras.md) e no README. O código não repete a justificativa.
- A regra recebe o parâmetro por construtor, o que permite testar valores diferentes sem mudar o ambiente.

## Alternativas descartadas

- **Números direto no `evaluate`.**
  - **Preço:** número mágico; calibrar é editar regra.
  - **Ganharia se** o parâmetro fosse uma constante regulatória, como o limite noturno do Banco Central.
- **Tabela de parâmetros no banco.**
  - **Preço:** mais uma tabela e uma consulta por Pix; muda a decisão sem deploy nem registro no Git.
  - **Ganharia se** houvesse operação que calibra em produção sem time de engenharia.

## Consequências

- O `docker-compose.yml` repassa só as variáveis que o time quiser expor; as demais usam o padrão do código.
- Mudar um padrão é entrada no [CHANGELOG](../../../CHANGELOG.md), com o porquê.
