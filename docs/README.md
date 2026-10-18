---
title: Índice da documentação
summary: Mapa de todos os documentos do projeto, cada um com a pergunta que responde. Comece por aqui.
related: [../README.md, ../llms.txt, ../AGENTS.md, ../CHANGELOG.md]
sources: [Desafio Antifraude Pix, bootcamp-base-api, Projeto fase 1]
---

# Documentação: Motor Antifraude Pix (Hackathon QI Tech 2026)

> **Repositório AI-friendly:** agentes começam pelo [`AGENTS.md`](../AGENTS.md); o porquê está em [trabalhando com IA](trabalhando-com-ia.md).
>
> **Como navegar:** cada documento trata de um assunto, abre com front-matter (`title`, `summary`, `related`, `sources`) e com a linha *Responde a*. Links relativos; diagramas em Mermaid. Não há RFC: as decisões estão nas [ADRs](02-arquitetura/decisoes/README.md) e as mudanças no [CHANGELOG](../CHANGELOG.md) ([ADR 0015](02-arquitetura/decisoes/0015-changelog-e-adrs-no-lugar-da-rfc.md)).

## Leitura mínima (10 minutos)

1. [Enunciado](01-contexto/enunciado.md): o que foi pedido, nas palavras da QI Tech.
2. [Problema](01-contexto/problema.md): por que é difícil e que garantias damos.
3. [Motor de regras](05-motor/motor-de-regras.md) e [catálogo de regras](05-motor/regras.md): como decidimos.
4. [Decisões](02-arquitetura/decisoes/README.md): por que é assim.

## Mapa completo

| Documento | Responde a |
|---|---|
| [glossario.md](glossario.md) | O que significa cada termo (velocity, fan-in, conta laranja, ISPB…)? |
| **01 · Contexto** | |
| [enunciado.md](01-contexto/enunciado.md) | O que exatamente o hackathon pede? (transcrição dos dois PDFs) |
| [problema.md](01-contexto/problema.md) | O que o sistema faz, por que é difícil, o que fica fora? |
| [requisitos.md](01-contexto/requisitos.md) | O que o enunciado exige (E1–E8), quais regras herdadas valem (R1–R6), onde mostrar cada critério da banca? |
| **02 · Arquitetura** | |
| [visao-geral.md](02-arquitetura/visao-geral.md) | Quais serviços sobem (api, db, worker), por onde passa um Pix, o que veio da base? |
| [c4.md](02-arquitetura/c4.md) | Diagramas C4 (imagens e fontes PlantUML): contexto, containers, componentes da API, do motor e do worker, e backtest sem HTTP e sem banco |
| [camadas.md](02-arquitetura/camadas.md) | Em qual pasta mora cada coisa, inclusive uma regra antifraude? |
| [decisoes/](02-arquitetura/decisoes/README.md) | Por que cada escolha, e o que foi descartado? (33 ADRs) |
| **03 · API** | |
| [rotas.md](03-api/rotas.md) | Quais rotas existem, com entrada, saídas e idempotência? Formato do `metadata` |
| [erros.md](03-api/erros.md) | Qual código QIT sai em cada recusa? Próximo código livre |
| **04 · Dados** | |
| [modelo.md](04-dados/modelo.md) | Quais tabelas, índices e invariantes, e por quê? |
| **05 · Motor** | |
| [motor-de-regras.md](05-motor/motor-de-regras.md) | Como o motor está estruturado e de onde vem o histórico? |
| [regras.md](05-motor/regras.md) | Quais regras, com que parâmetros, em que fonte (BCB, literatura) e com que efeito medido no PixSim? |
| [decisao.md](05-motor/decisao.md) | Como os disparos viram uma decisão; quando sai 2FA? |
| [calibracao.md](05-motor/calibracao.md) | Por que cada parâmetro tem o valor que tem? Quanta fricção, captura e custo no PixSim? |
| [analises.md](05-motor/analises.md) | Os dados se comportam como as regras supõem? Distribuição de valores, dispersão das contagens, drift (PSI) e sensibilidade de limiar |
| [validacao-pixsim.md](05-motor/validacao-pixsim.md) | Como o motor se sai num simulador de terceiros (PixSim, calibrado com dados do BCB)? O que se mantém e o que cai fora do nosso gerador? Quanto cada regra contribui (ablação)? |
| **06 · Operação** | |
| [rodando-localmente.md](06-operacao/rodando-localmente.md) | Como subir, testar, resetar; variáveis e armadilhas |
| **07 · Testes** | |
| [estrategia.md](07-testes/estrategia.md) | Como testar uma regra de velocity por HTTP, sem esperar o relógio? |
| **Processo** | |
| [contribuindo.md](contribuindo.md) | Clean Code, nomes, commits, CHANGELOG, checklist de PR |
| [trabalhando-com-ia.md](trabalhando-com-ia.md) | Como usar agentes aqui e saber o que eles mudaram? |
| [plano-de-implementacao.md](plano-de-implementacao.md) | (Histórico) O que da pesquisa entra até o prazo, em que ordem, e o que cortar se atrasar? |
| [plano-de-implementacao-2.md](plano-de-implementacao-2.md) | (Histórico) Segunda rodada: backtest em lote, modelos em shadow (LogReg, LightGBM, Isolation Forest), cold path com grafo, GraphSAGE e HMM, calibração automática e CI |
| [plano-de-implementacao-3.md](plano-de-implementacao-3.md) | (Histórico) Validação externa no PixSim, custo assimétrico e P@k, peer group, rótulos atrasados e stacking |
| [plano-de-implementacao-4.md](plano-de-implementacao-4.md) | (Histórico) PixSim como referência das métricas e retroalimentação pelo MED no backtest |
| [relatorio/relatorio.md](relatorio/relatorio.md) | Relatório técnico: problema, fundamentos, arquitetura, metodologia, resultados no PixSim e limitações (PDF por `make pdf`) |
| [../CHANGELOG.md](../CHANGELOG.md) | O que mudou, quando, por quê e quem (pessoa ou agente)? |
| **Referência** | |
| [referencia/enunciado/](referencia/enunciado/) | PDFs originais do desafio e dos slides |
| [referencia/base-service-readme.md](referencia/base-service-readme.md) | README original do Base Service (exemplo `sample_entity`, troubleshooting) |
| [referencia/como-o-projeto-e-organizado.md](referencia/como-o-projeto-e-organizado.md) | Guia original das pastas do Base Service |
| [pesquisa/Pesquisa QITech.pdf](<pesquisa/Pesquisa QITech.pdf>) | Pesquisa do time que originou o plano (literatura e indústria) |

## Datas

| Data | Marco |
|---|---|
| Sábado 17/10, 10:00 | Abertura |
| **Domingo 18/10, até 12:00** | Entrega do link do repositório no grupo da final, no Slack |
| Domingo 18/10, 13:00–15:00 | Apresentações: 7 min + 3 min de perguntas |
