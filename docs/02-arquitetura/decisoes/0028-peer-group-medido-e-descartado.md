---
title: "ADR 0028: Peer group medido e descartado"
summary: A regra que compara o pagador sem histórico com pares parecidos (PF/PJ × idade da conta) foi implementada, medida no PixSim e descartada — efeito nulo em captura e custo, e até ~94 ms a mais por Pix no pior caso.
related: [0016-sinais-estatisticos-como-regras.md, ../../05-motor/validacao-pixsim.md, ../../plano-de-implementacao-3.md]
sources: [Bolton & Hand (2002), nível 2 (Peer Group Analysis); medições da fase V4 no PixSim]
---

# ADR 0028: Peer group medido e descartado

> [Índice](../../README.md) › [Decisões](README.md) › 0028

**Status:** aceita (a regra não entra no motor)

## Contexto

`PROFILE_AMOUNT_ROBUST_Z` fica muda para o pagador sem histórico. A pesquisa propõe o nível 2 de Bolton & Hand: comparar o indivíduo com um grupo de pares. Implementamos `PROFILE_PEER_AMOUNT`, que pede 2FA quando o valor de um pagador sem perfil próprio fica mais de 3,5 desvios robustos acima dos pares do mesmo grupo (PF/PJ × idade da conta de origem; até 500 valores, mínimo 50). Medimos no PixSim, a referência das métricas ([plano 4](../../plano-de-implementacao-4.md)).

## Decisão

A regra **não entra** no motor. O código fica guardado fora da árvore (`git stash`), e a medição fica na [validação no PixSim](../../05-motor/validacao-pixsim.md#peer-group).

| Medida | Resultado |
|---|---|
| Fricção, captura por tipologia e custo ponderado no PixSim B | idênticos com e sem a regra (R$ 157,60 por 1.000 Pix) |
| Pix de vítima com pagador sem perfil próprio | 12 de 1.438 (0,8%), com z mediano de 1,7, abaixo do corte |
| Latência pela API (300 mil Pix em 30 dias) | +9 ms com grupo cheio; **+94 ms** com grupo vazio (a consulta percorre a janela inteira) |

## Alternativas descartadas

- **Manter decidindo, como rede de segurança.**
  - **Preço:** até 94 ms a mais no Pix de pagador novo, um custo que cresce com o volume, por um ganho não demonstrado.
  - **Ganharia se** houvesse uma fração relevante de fraudes vindas de contas sem histórico.
- **Manter em shadow.**
  - **Preço:** a consulta roda do mesmo jeito; mesma latência, nenhuma decisão.
  - **Ganharia se** quiséssemos acumular evidência em produção.

## Consequências

- O pagador sem histórico continua coberto pelas regras de payload e de velocity fixa.
- Voltar com a regra é recuperar o stash e reavaliar com dados em que pagador novo seja vetor de fraude.
