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
| **Conta laranja (mula)** | Conta, muitas vezes recém-aberta, usada para receber e repassar dinheiro de golpe. Alvo das regras de contraparte. |
| **Contraparte** | Quem recebe o Pix (`destination_account`). |
| **Disparo** | Resultado de uma regra que encontrou risco: código, decisão e motivo. Tabela `pix_analysis_reason`. |
| **Fan-in** | Muitos pagadores diferentes mandando para o mesmo destino em pouco tempo. |
| **Fricção** | Qualquer passo extra imposto ao cliente (2FA, bloqueio). Custo da regra que dispara em cliente bom. |
| **id × key** | `id` é o SERIAL interno, nunca exposto. `key` é o UUID da análise. O `id` do Pix é de quem chama e serve de chave de consulta ([ADR 0011](02-arquitetura/decisoes/0011-uuid-key-publica.md)). |
| **Idempotência** | Repetir o mesmo Pix (mesmo `id`, mesmo corpo) devolve a análise original sem reanalisar ([ADR 0012](02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)). |
| **ISPB** | Código de 8 dígitos que identifica a instituição no sistema de pagamentos. É o `destination_account.participant`. |
| **Janela** | Intervalo `[transaction_date − N, transaction_date)` usado por regras de velocity e montante ([ADR 0007](02-arquitetura/decisoes/0007-relogio-da-transacao.md)). |
| **Motor de regras** | A peça que junta sinais e devolve decisão com motivo ([motor](05-motor/motor-de-regras.md)). |
| **QIT code** | Código único de cada erro da API (`QIT000001`…). Decisão `rejected` não é erro. |
| **Regra** | Uma classe em `src/rules/` que olha um sinal e diz se dispara ([catálogo](05-motor/regras.md)). |
| **`RuleContext`** | Objeto imutável com os agregados de histórico, montado pelo controller e lido pelas regras. |
| **Severidade** | Ordem das decisões: `rejected` (2) > `two_factor_required` (1) > `approved` (0). A maior vence. |
| **Sinal** | Qualquer dado que ajuda a decidir: do payload (valor, hora, idade da conta, aparelho) ou do histórico. |
| **Tomada de conta (ATO)** | Golpista usando a conta da vítima, em geral com aparelho novo e rajada de Pix. |
| **Velocity** | Quantidade de eventos por unidade de tempo ("rápido demais?"). |
