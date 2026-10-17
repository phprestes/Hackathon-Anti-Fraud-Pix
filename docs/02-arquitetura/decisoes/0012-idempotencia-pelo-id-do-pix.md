---
title: "ADR 0012: Idempotência pelo id do Pix"
summary: Mesmo id com o mesmo corpo devolve 200 com a análise original; com corpo diferente, 409; a corrida é resolvida pelo UNIQUE.
related: [0011-uuid-key-publica.md, ../../03-api/rotas.md, ../../03-api/erros.md]
sources: [Desafio Antifraude Pix (seção 3.2 "id: ID único do Pix"), Projeto fase 1 (ADR de idempotência)]
---

# ADR 0012: Idempotência pelo `id` do Pix

> [Índice](../../README.md) › [Decisões](README.md) › 0012

**Status:** proposta

## Contexto

O `id` do Pix é único por definição. Quem chama vai repetir o POST depois de timeout. Se cada repetição for analisada de novo, ela entra no histórico e dispara a velocity do próprio cliente: o retry vira fraude.

## Decisão

- `pix_transaction.pix_id` tem `UNIQUE`.
- Antes de rodar as regras, o controller busca pelo `pix_id`:
  - existe e o payload é igual: **200** com a análise original, sem rodar regra nem gravar nada;
  - existe e o payload difere: **409** `QIT002002`.
- Duas requisições novas com o mesmo `id` ao mesmo tempo: a segunda falha no `UNIQUE` no commit; o controller captura o `IntegrityError` e refaz a busca.
- Comparação de payload: o JSON canônico (chaves ordenadas) do corpo recebido contra o `payload` gravado.

## Alternativas descartadas

- **Reanalisar a cada POST.**
  - **Preço:** decisão muda entre tentativas e o histórico conta o mesmo Pix várias vezes.
  - **Ganharia se** o Pix pudesse mudar de valor com o mesmo `id`, o que o contrato não prevê.
- **Header `Idempotency-Key`.**
  - **Preço:** o contrato já tem um identificador único; seria um segundo.
  - **Ganharia se** o `id` do Pix não fosse confiável.

## Consequências

- Retry é sempre seguro para quem chama.
- O teste de idempotência confere que a velocity não sobe com a repetição.
