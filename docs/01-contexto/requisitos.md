---
title: Requisitos e critérios de avaliação
summary: O que o enunciado exige, as regras herdadas do bootcamp que continuam valendo e onde o projeto atende cada critério da banca.
related: [enunciado.md, problema.md, ../07-testes/estrategia.md]
sources: [Desafio Antifraude Pix (seções 3 a 7), Projeto da fase 1 (R1–R8)]
---

# Requisitos

> [Índice](../README.md) › Contexto › Requisitos
>
> **Responde a:** o que o enunciado exige? o que a banca observa? quais regras do bootcamp continuam valendo?

## Exigências do enunciado (E1–E8)

| # | Exigência | Onde o projeto atende |
|---|---|---|
| E1 | `POST /pix/transaction` recebe o payload da seção 3.1 do [enunciado](enunciado.md) | [rotas](../03-api/rotas.md) |
| E2 | A saída tem `key`, `status` (`approved`, `rejected`, `two_factor_required`) e `metadata` livre | [rotas](../03-api/rotas.md), [ADR 0003](../02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md) |
| E3 | `GET /pix/transaction/{id}` devolve a análise gravada | [rotas](../03-api/rotas.md) |
| E4 | Banco próprio com o histórico de tudo que chegou | [modelo](../04-dados/modelo.md), [ADR 0009](../02-arquitetura/decisoes/0009-historico-append-only.md) |
| E5 | Regras antifraude e testes | [regras](../05-motor/regras.md), [estratégia de testes](../07-testes/estrategia.md) |
| E6 | Toda decisão sai com um motivo explicável | [decisão](../05-motor/decisao.md) |
| E7 | Repositório a partir do Base Service, nos padrões do bootcamp | [ADR 0001](../02-arquitetura/decisoes/0001-partir-do-base-service.md), [camadas](../02-arquitetura/camadas.md) |
| E8 | README no modelo da seção 6 do enunciado, com o porquê de cada parâmetro | [README](../../README.md) |

## Regras herdadas do bootcamp (R1–R6)

Vieram da fase 1 e do Base Service. Continuam valendo porque a banca avalia "alinhamento com o Base Service" (critério 2).

| # | Regra | Como o projeto atende |
|---|---|---|
| R1 | Teste nunca importa de `src/` nem lê o banco; o cenário nasce pela API | Testes black box por HTTP ([estratégia](../07-testes/estrategia.md)) |
| R2 | Um comando sobe tudo numa máquina Linux limpa | `make all` ([rodando localmente](../06-operacao/rodando-localmente.md)) |
| R3 | Toda recusa tem corpo `{title, description, translation, code}` com código `QIT` único | [erros](../03-api/erros.md) |
| R4 | Nada que entrou deixa de existir (append-only) | [ADR 0009](../02-arquitetura/decisoes/0009-historico-append-only.md) |
| R5 | Nenhum identificador gerado pelo banco sai da API | [ADR 0011](../02-arquitetura/decisoes/0011-uuid-key-publica.md) |
| R6 | Dinheiro é `BIGINT` em centavos, nunca float | [ADR 0010](../02-arquitetura/decisoes/0010-dinheiro-em-centavos.md) |

## Critérios da banca → onde mostrar

| # | Critério | Evidência no repositório |
|---|---|---|
| 1 | Profundidade antifraude | [regras.md](../05-motor/regras.md): cada regra com sinal, parâmetro e porquê; tabela "Por quê" do README |
| 2 | Padrão de código | [camadas](../02-arquitetura/camadas.md), `make lint`, testes black box com os dois caminhos de cada `if` |
| 3 | Modelagem de dados | [modelo](../04-dados/modelo.md) e `database/database.sql` |
| 4 | Solução funcional | `make all` do clone ao verde; teste que grava e consulta cada Pix; teste por regra descrita |
| 5 | Documentação | README no modelo + `docs/` + [ADRs](../02-arquitetura/decisoes/README.md) + [CHANGELOG](../../CHANGELOG.md) |
| 6 | Apresentação | ADRs com alternativas descartadas e preço de cada uma |

## Matriz regra → teste

Preenchida conforme cada regra antifraude ganha código. Cada `if` tem pelo menos um teste que passa pela regra e um que é barrado por ela.

| Regra | Teste que passa (approved) | Teste que dispara | Arquivo |
|---|---|---|---|
| *(nenhuma regra implementada ainda)* | | | |
