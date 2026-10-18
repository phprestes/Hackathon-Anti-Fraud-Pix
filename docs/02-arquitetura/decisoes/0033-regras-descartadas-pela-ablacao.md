---
title: "ADR 0033: Três regras descartadas pela ablação no PixSim"
summary: TYPOLOGY_SPLITTING, COUNTERPARTY_FLAGGED e AMOUNT_SOURCE_DAILY_SUM saem do motor — custam mais do que evitam nos dois mundos do PixSim e não têm âncora regulatória verificada; o motor fica com 15 regras que decidem.
related: [0018-regras-compostas-por-tipologia.md, 0019-reputacao-de-contraparte-derivada.md, 0028-peer-group-medido-e-descartado.md, 0029-pixsim-como-referencia.md, ../../05-motor/regras.md, ../../05-motor/validacao-pixsim.md]
sources: [scripts/rule_ablation.py, scripts/backtest.py --disable, PixSim mundos A (seed 20260910) e B (seed 20261017), scripts/cost-model.json]
---

# ADR 0033: Três regras descartadas pela ablação no PixSim

> [Índice](../../README.md) › [Decisões](README.md) › 0033

**Status:** aceita (as três regras saem do motor)

## Contexto

A ablação por regra no mundo B do PixSim ([validação](../../05-motor/validacao-pixsim.md#contribuição-de-cada-regra)) mostrou sete regras com contribuição negativa: o custo ponderado cai quando são desligadas. Decidir só pelo mundo B o transformaria em mundo de ajuste, então a remoção foi medida também no mundo A.

## Critério

Uma regra fica se tiver valor nesta entrega por pelo menos um caminho:

1. **Contribui no PixSim** (ablação positiva).
2. **Tem âncora regulatória verificada** (BCB), mesmo com o PixSim preferindo outra coisa.
3. **Cobre um sinal que o PixSim não gera** (geolocalização, rajada, fazenda de aparelhos, funil, grafo do worker): não dispara lá, logo custa zero, e cobre um golpe que o gerador não tem.

Sai a regra com ablação negativa e nenhum dos três caminhos.

## Decisão

| Regra | Família | Ablação no mundo B (R$ por 1.000 Pix) | Por que sai |
|---|---|---|---|
| `TYPOLOGY_SPLITTING` | tipologia | −25,99 | Sem fonte regulatória nem acadêmica para os números; o PixSim não tem fracionamento, então a regra só reprova legítimos |
| `COUNTERPARTY_FLAGGED` | contraparte | −11,76 | Só análoga ao art. 39-B, §1º, I (usa as nossas reprovações, não notificações de infração do DICT); 2FA em 0,72% dos legítimos com lift de 1,8x |
| `AMOUNT_SOURCE_DAILY_SUM` | montante | −8,69 | Nenhum normativo conferido fixa soma diária de Pix; platô de custo entre R$ 30 mil e R$ 60 mil |

Ficam, mesmo negativas: `COUNTERPARTY_NEW_ACCOUNT` (art. 39-B, §1º, II), `LIMIT_NIGHT_AMOUNT` (Res. BCB 142/2021 e IN BCB 512/2024), `PROFILE_AMOUNT_ROBUST_Z` (Iglewicz & Hoaglin; −R$ 1,45) e `TYPOLOGY_MULE` (art. 39-B, §1º, II + funil; −R$ 0,38).

## Resultado das três juntas desligadas

Custo ponderado por 1.000 Pix (visão vítima), com os parâmetros calibrados de `2026.10.18-pixsim`:

| Mundo | 18 regras | 15 regras | Pix de vítima barrados | 2FA em legítimos | Reprovação em legítimos |
|---|---|---|---|---|---|
| A (escolhe) | R$ 132,13 | R$ 109,61 | 51,7% → 50,7% | 3,81% → 2,97% | 0,012% → 0,000% |
| B (confirma) | R$ 153,51 | R$ 118,82 | 51,8% → 51,1% | 4,13% → 3,09% | 0,03% → 0,002% |

Cada uma das três, desligada sozinha no mundo A, também baixa o custo: `TYPOLOGY_SPLITTING` R$ 115,69, `COUNTERPARTY_FLAGGED` R$ 122,27, `AMOUNT_SOURCE_DAILY_SUM` R$ 125,93.

A trava do CI no nosso simulador continua passando: 6,6% de 2FA em legítimos (limite 7%), nenhuma reprovação, 100% das sequências de fraude barradas (o fracionamento passa a ser barrado por 2FA em vez de reprovação).

## Alternativas descartadas

- **Manter e só documentar.**
  - **Preço:** cerca de R$ 22 a R$ 35 a mais por 1.000 Pix nos dois mundos, por regras sem fonte.
  - **Ganharia se** houvesse evidência fora do PixSim de que fracionamento é vetor relevante.
- **Subir o corte do `TYPOLOGY_SPLITTING` para R$ 50 mil.**
  - **Preço:** a regra continua sem fonte e quase nunca dispararia.
  - **Ganharia se** o time quisesse manter a tipologia por cobertura.
- **Mandar as três para shadow.**
  - **Preço:** a consulta continua rodando por um sinal que não decide nada.
  - **Ganharia se** quiséssemos acumular disparos em produção.

## Consequências

- O motor tem 15 regras que decidem. A família "Montante" do enunciado fica sem regra própria; o teto por Pix (`LIMIT_SINGLE_AMOUNT`) e o z robusto cobrem parte dela.
- As features `source_sum_last_24h_cents`, `source_small_attempts_last_24h` e `destination_rejected_by_others_last_window` continuam no contexto: os modelos em shadow as leem. Por isso `RULE_FLAGGED_WINDOW_DAYS` e `RULE_SPLITTING_MAX_AMOUNT_CENTS` ficam como janelas de feature.
- O código das três regras e os testes delas estão no histórico do Git, até o commit `0bb5df8`. Voltar com uma delas é restaurar a classe e o teste e medir de novo com `make rule-ablation`.
- `RULE_SET_VERSION` passa a `2026.10.18-pixsim-2`.
