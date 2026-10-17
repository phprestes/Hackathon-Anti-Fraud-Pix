---
title: O problema
summary: O que o motor antifraude Pix faz, por que é difícil, que garantias dá e o que fica fora do escopo.
related: [enunciado.md, requisitos.md, ../05-motor/motor-de-regras.md]
sources: [Desafio Antifraude Pix (seções 1, 2 e 4), slides do hackathon (Risk Solutions)]
---

# O problema

> [Índice](../README.md) › Contexto › Problema
>
> **Responde a:** o que o sistema faz? por que é difícil? o que não entra?

## O que o sistema faz

Uma API recebe um Pix **antes de ele sair** e responde uma de três decisões, sempre com o motivo:

| Status | Significado para o cliente |
|---|---|
| `approved` | O Pix segue sem fricção. |
| `two_factor_required` | Há dúvida: o cliente confirma que é ele (2FA). |
| `rejected` | O risco é claro: o Pix não sai. |

Cada Pix recebido fica gravado, com a análise, e pode ser consultado depois pelo `id` dele. Quem chama são sistemas internos, identificados pelo `INTERNAL-TOKEN`. O sistema não tem interface de usuário. O texto original está no [enunciado](enunciado.md).

## Por que é difícil

| Tensão | Consequência no desenho |
|---|---|
| **Tempo.** A decisão sai em poucos segundos, com o cliente esperando. Não cabe analista nem consulta externa pesada. | Tudo o que a regra precisa está no payload ou no nosso banco. Nenhuma chamada HTTP no caminho da decisão ([ADR 0002](../02-arquitetura/decisoes/0002-monolito-sincrono-sem-dependencia-externa.md)). |
| **Histórico.** Um Pix sozinho diz pouco: o sinal está na comparação com o passado do pagador, do destino e do aparelho. | Todo Pix recebido é gravado, inclusive os reprovados, com índices para as janelas de tempo ([ADR 0009](../02-arquitetura/decisoes/0009-historico-append-only.md)). |
| **Fricção.** Bloquear cliente bom também é prejuízo. | Existe o meio-termo `two_factor_required`, e cada parâmetro de regra é calibrado e justificado ([regras](../05-motor/regras.md)). |
| **Explicabilidade.** Toda decisão sai com um motivo. | Todas as regras rodam e cada disparo vira um motivo no `metadata` ([ADR 0006](../02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md)). |

## As garantias

| Garantia | O que acontece se falhar |
|---|---|
| **Todo Pix recebido fica gravado e consultável**, aprovado ou não | O histórico perde exatamente as tentativas de fraude, que são o sinal das regras de velocity. A banca também confere isso (critério 4). |
| **Mesmo Pix enviado duas vezes não gera duas análises** | O retry de quem chamou conta como uma segunda transação e infla a velocity do próprio cliente. |
| **A decisão é reproduzível**: o mesmo histórico e o mesmo Pix dão a mesma decisão | O teste fica instável, e a explicação da decisão deixa de valer depois do fato. |
| **Dinheiro é exato** (inteiro em centavos) | Somatórios de montante acumulam erro de arredondamento. |
| **Nenhuma decisão sai sem motivo** | O cliente reprovado não sabe por quê, e o time não consegue calibrar a regra. |

## Fora do escopo

Do enunciado: onboarding e cadastro de contas, front-end e outras APIs. Também ficam de fora, por decisão do time:

- Mover o dinheiro. O motor só decide; quem liquida o Pix é outro sistema.
- Fluxo do 2FA. A API responde `two_factor_required` e não acompanha a confirmação.
- Regras configuráveis sem código ("no code", dos slides). As regras são código, com parâmetros por ambiente ([ADR 0004](../02-arquitetura/decisoes/0004-motor-de-regras-em-codigo.md)).
- Modelos de machine learning e consultas a bases externas (listas restritivas, DICT).
