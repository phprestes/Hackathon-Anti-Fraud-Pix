---
title: Glossário
summary: Definição curta de cada termo de antifraude, Pix e arquitetura usado na documentação.
related: [README.md, 05-motor/regras.md, 04-dados/modelo.md]
sources: [Desafio Antifraude Pix, slides do hackathon, Projeto fase 1 (glossário)]
---

# Glossário

> [Índice](README.md) › Glossário
>
> **Responde a:** o que significa este termo no projeto?

| Termo | Definição no projeto |
|---|---|
| **2FA** | Segundo fator de autenticação. A API só responde `two_factor_required`; o fluxo de confirmação é de outro sistema. |
| **ADR** | Registro de uma decisão de arquitetura: contexto, decisão, alternativas com preço, consequências ([índice](02-arquitetura/decisoes/README.md)). |
| **Agregado (de histórico)** | Número calculado no banco sobre Pix anteriores (contagem, soma, média) numa janela de tempo. Vai para o `RuleContext`. |
| **Análise** | O resultado de rodar o motor num Pix: `key`, `status`, `metadata`. Tabela `pix_analysis`. |
| **Append-only** | Mudança vira linha nova; nada é apagado nem editado (R4). |
| **Backtest** | O mesmo motor rodado em lote sobre um arquivo de eventos rotulados, sem HTTP e sem banco (`scripts/backtest/backtest.py`, `InMemoryHistory`). Mede fricção, captura e custo. |
| **Champion/challenger** | O modelo em uso (campeão) e o candidato retreinado (desafiante). O desafiante só vira campeão se custar menos numa semana de sombra ([ADR 0032](02-arquitetura/decisoes/0032-retroalimentacao-pelo-med-no-backtest.md)). |
| **Conta laranja (mula)** | Conta, muitas vezes recém-aberta, usada para receber e repassar dinheiro de golpe. Alvo das regras de contraparte. |
| **Contraparte** | Quem recebe o Pix (`destination_account`). |
| **Disparo** | Resultado de uma regra que encontrou risco: código, decisão e motivo. Tabela `pix_analysis_reason`. |
| **Fan-in** | Muitos pagadores diferentes mandando para o mesmo destino em pouco tempo. |
| **Fricção** | Qualquer passo extra imposto ao cliente (2FA, bloqueio). Custo da regra que dispara em cliente bom. |
| **id × key** | `id` é o SERIAL interno, nunca exposto. `key` é o UUID da análise. O `id` do Pix é de quem chama e serve de chave de consulta ([ADR 0011](02-arquitetura/decisoes/0011-uuid-key-publica.md)). |
| **Idempotência** | Repetir o mesmo Pix (mesmo `id`, mesmo corpo) devolve a análise original sem reanalisar ([ADR 0012](02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)). |
| **ISPB** | Código de 8 dígitos que identifica a instituição no sistema de pagamentos. É o `destination_account.participant`. |
| **Janela** | Intervalo `[transaction_date − N, transaction_date)` usado por regras de velocity e montante ([ADR 0007](02-arquitetura/decisoes/0007-relogio-da-transacao.md)). |
| **MED** | Mecanismo Especial de Devolução do Pix: regras para devolver um Pix quando há fundada suspeita de fraude (Regulamento do Pix, cap. XI, seção II, arts. 41-B a 41-D). Fonte do rótulo atrasado ([Res. BCB 1/2020](https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Pix_Regulation/Resolution_BCB_1.pdf), tradução oficial em inglês). |
| **Motor de regras** | A peça que junta sinais e devolve decisão com motivo ([motor](05-motor/motor-de-regras.md)). |
| **P@k** | Precisão nos k Pix mais bem ranqueados do dia: uma mesa de k analistas olhando os k piores. Inflada pela superamostragem de fraude do PixSim. |
| **Paridade** | Prova de que API (SQL) e backtest (memória) decidem igual, Pix a Pix: status, regras e as 33 features (`make parity`). |
| **PixSim** | Simulador open source de Pix fraudulento de terceiros (Zeimarani et al., 2026), calibrado com dados abertos do BCB. É a única fonte de valor estatístico do projeto ([ADR 0029](02-arquitetura/decisoes/0029-pixsim-como-referencia.md)). |
| **QIT code** | Código único de cada erro da API (`QIT000001`…). Decisão `rejected` não é erro. |
| **Regra** | Uma classe em `src/rules/` que olha um sinal e diz se dispara ([catálogo](05-motor/regras.md)). |
| **`RuleContext`** | Objeto imutável com os agregados de histórico, montado pelo controller e lido pelas regras. |
| **Rótulo atrasado** | A fraude só é confirmada dias depois (mediana de 2 dias no PixSim, p90 de 19,8), pelo reporte ao MED. O treino usa só o que já foi reportado ([ADR 0031](02-arquitetura/decisoes/0031-modelos-treinados-no-pixsim-e-rotulos-atrasados.md)). |
| **Severidade** | Ordem das decisões: `rejected` (2) > `two_factor_required` (1) > `approved` (0). A maior vence. |
| **Shadow mode** | Modelo que calcula e grava em `metadata.shadow` o que decidiria, mas nunca muda a decisão ([ADR 0022](02-arquitetura/decisoes/0022-shadow-mode.md)). |
| **Sinal** | Qualquer dado que ajuda a decidir: do payload (valor, hora, idade da conta, aparelho) ou do histórico. |
| **Tomada de conta (ATO)** | Golpista usando a conta da vítima, em geral com aparelho novo e rajada de Pix. |
| **Velocity** | Quantidade de eventos por unidade de tempo ("rápido demais?"). |
| **Viés de seleção** | O motor só aprende com o desfecho dos Pix que deixou passar: fraude barrada some do rótulo e parece legítima, e o 2FA parece mais inocente do que é ([validação](05-motor/validacao-pixsim.md)). |
