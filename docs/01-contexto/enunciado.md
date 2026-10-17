---
title: Enunciado do hackathon (Antifraude Pix)
summary: Transcrição completa e fiel dos dois PDFs do hackathon (documento do desafio e slides de abertura), sem interpretação.
related: [problema.md, requisitos.md, ../05-motor/motor-de-regras.md]
sources: [referencia/enunciado/desafio-antifraude-pix.pdf, referencia/enunciado/hackathon-antifraude-pix.pdf]
---

# Enunciado: Desafio Antifraude Pix

> [Índice](../README.md) › Contexto › Enunciado
>
> **Responde a:** o que exatamente o hackathon pede, com as palavras do enunciado?

Transcrição dos PDFs originais em [`docs/referencia/enunciado/`](../referencia/enunciado/). A Parte A vem do documento do desafio (8 páginas); a Parte B traz o que só aparece nos slides de abertura (28 páginas). Onde os dois repetem o mesmo conteúdo, ele aparece uma vez só. Interpretação e decisões do time ficam em [problema.md](problema.md) e nas [ADRs](../02-arquitetura/decisoes/README.md), nunca aqui.

---

## Parte A: documento do desafio

**Desafio Antifraude Pix** · Oct 17, 2026 · @Guilherme Bakaukas | QI Tech
Bootcamp QI Tech 2026 · Hackathon · Risk Solutions

> Desafio do hackathon: uma API que recebe um Pix e decide se ele pode sair.

### Datas principais

| Evento | Quando |
|---|---|
| Abertura | Sábado, 17/10, 10:00 |
| Entrega do link do repositório | Domingo, 18/10, até 12:00, no grupo da final, no Slack |
| Apresentações | Domingo, 18/10, 13:00–15:00 |
| Premiações | Domingo, 18/10, 15:00–16:00 |

### 1. O desafio

Cada time constrói o motor antifraude de Pix: uma API que recebe a transação, aplica as regras do time e devolve uma decisão.

| Etapa | O que é |
|---|---|
| Entrada | A transação. Um Pix no formato definido na seção 3: quem paga, quem recebe, quanto, quando e de onde. |
| Regras | O motor de vocês. Regras de antifraude aplicadas sobre as transações Pix recebidas. |
| Saída | A decisão. Um status: `approved`, `rejected` ou `two_factor_required`. O resto, se quiserem, vai em `metadata`. |

### 2. Antifraude no Pix

#### 2.1 O que muda no Pix

| Aspecto | O que significa |
|---|---|
| Tempo | A decisão sai antes do dinheiro sair, em poucos segundos. Não dá para esperar uma consulta externa pesada nem um analista. |
| Histórico | Uma transação sozinha diz pouco. A regra compara com o que esse pagador e esse destino já fizeram antes. |
| Fricção | Bloquear um cliente bom também é prejuízo. A regra boa barra a fraude sem travar quem só quer pagar o aluguel. |

#### 2.2 Exemplos de regras

Exemplos para guiar o raciocínio, não uma lista fechada. Explorem outros sinais que façam sentido para o problema.

| Família | Pergunta |
|---|---|
| Limite | Passou do teto? |
| Velocity | Rápido demais? |
| Montante | Somou demais? |
| Perfil | Está no padrão do cliente? |
| Contraparte | Quem recebe é confiável? |

#### 2.3 As três decisões

| Decisão | Status | Quando |
|---|---|---|
| Aprovar | `approved` | Segue normal, sem fricção para o cliente. |
| Pedir 2FA | `two_factor_required` | Fricção só onde há dúvida: o cliente confirma que é ele mesmo. |
| Reprovar | `rejected` | Bloqueia quando o risco é claro. |

> No Pix não cabe análise manual: o cliente está esperando. Toda decisão sai com um motivo explicável.

### 3. Contrato da API

#### 3.1 Entrada

`POST /pix/transaction`

```json
{
    "id": "pix-000123",
    "amount": 150000,
    "transaction_date": "2026-10-17T22:15:00-03:00",
    "source_account": {
      "branch": "0001",
      "account_number": "88213",
      "opening_date": "2025-03-02T10:00:00-03:00",
      "owner": { "document_number": "123.456.789-09" }
    },
    "destination_account": {
      "participant": "60701190",
      "branch": "3675",
      "account_number": "10442",
      "opening_date": "2026-10-10T09:00:00-03:00",
      "owner": { "document_number": "987.654.321-00" }
    },
    "source": {
      "device_id": "dvc-9f2c71a8",
      "channel": "app",
      "ip": "198.51.100.23",
      "geolocation": { "latitude": -23.56, "longitude": -46.65 }
    }
}
```

#### 3.2 Campos da entrada

| Campo | O que é |
|---|---|
| `id` | ID único do Pix |
| `amount` | Valor em centavos |
| `transaction_date` | Data e hora, com fuso |
| `source_account` | Conta de quem paga |
| `source_account.branch`, `source_account.account_number` | Agência e conta de quem paga |
| `source_account.opening_date` | Data de abertura da conta de quem paga |
| `source_account.owner.document_number` | CPF ou CNPJ de quem paga |
| `destination_account` | Conta de quem recebe |
| `destination_account.participant` | ISPB do banco de destino |
| `destination_account.branch`, `destination_account.account_number` | Agência e conta de quem recebe |
| `destination_account.opening_date` | Data de abertura da conta de quem recebe |
| `destination_account.owner.document_number` | CPF ou CNPJ de quem recebe |
| `source` | De onde saiu o Pix |
| `source.device_id` | ID do aparelho |
| `source.channel`, `source.ip` | Canal e IP |
| `source.geolocation` | Latitude e longitude (opcional) |

#### 3.3 Saída

```json
{
    "key": "b3f1c2e0-7d4a-4c1e-9a52-1f0e6c9d2a77",
    "status": "two_factor_required",
    "metadata": { }
}
```

| Campo | O que é |
|---|---|
| `key` | Identificador da análise |
| `status` | `approved`, `rejected` ou `two_factor_required` |
| `metadata` | Livre |

#### 3.4 Consulta

`GET /pix/transaction/{id}` devolve a análise que foi gravada.

### 4. Escopo

**Entra**

- O POST e o GET do endpoint
- Banco próprio com o histórico de tudo que chegou
- As regras e os testes
- O README
- Ponto de partida: o Base Service

**Fica de fora**

- Onboarding e cadastro de contas
- Front-end
- Outras APIs

**Livre**

A política antifraude é de vocês. Aprofundem no problema e resolvam do jeito que fizer mais sentido, desde que expliquem o porquê.

### 5. Entregáveis

| Entregável | O que entregar |
|---|---|
| Código | Repositório a partir do Base Service, seguindo os padrões de código discutidos durante o bootcamp. |
| README | No modelo abaixo (seção 6). É por ele que entendemos a lógica e o racional por trás das políticas de antifraude. |
| Apresentação | Contem o que fizeram e por quê. No máximo 7 minutos de apresentação + 3 minutos de perguntas da banca. |

> Lembrem-se do processo de RFC: troquem ideias e definam o escopo do projeto. Não precisa entregar o documento.

### 6. Modelo do README

```markdown
# [Nome do grupo]
**Integrantes:** [nomes]

## Como o motor de decisão funciona
[descrição breve sobre como estruturaram o motor]

## Regras
| Regra | Lógica | Parâmetros | Por quê |
|-------|--------|------------|---------|
[racional por trás da escolha das regras]

## Como as regras viram decisão
[ordem, quando pede 2FA]

## Como rodar e testar
```

> A correção começa pelo README: lemos as regras que vocês descreveram e o racional por trás delas. Expliquem o porquê de cada parâmetro que escolheram.

### 7. Critérios de avaliação

Vamos avaliar a qualidade da solução proposta e como chegaram nela.

| # | Critério | O que observamos |
|---|---|---|
| 1 | Profundidade antifraude | Entenderam o problema e calibraram as regras, sem parar no óbvio. |
| 2 | Padrão de código | Alinhamento com o Base Service, camadas corretamente aplicadas, testes bem elaborados. |
| 3 | Modelagem de dados | Estrutura de banco de dados. |
| 4 | Solução funcional | O projeto roda seguindo o README, cada Pix recebido fica gravado e consultável, e as decisões batem com as regras descritas. |
| 5 | Documentação | README completo e bem elaborado. |
| 6 | Apresentação | Qualidade da solução e raciocínio sobre as decisões tomadas. |

Apresentação: até 7 minutos + 3 minutos de perguntas da banca. Formato livre.

### 8. Cronograma

**Sábado, 17/10**

| Horário | Atividade |
|---|---|
| 10:00–10:30 | Abertura |
| 10:30–12:00 | Desafio + tira-dúvidas |
| 12:00–13:00 | Almoço |
| 13:00–19:00 | Mão na massa |
| 19:00–20:00 | Jantar (pizza) |
| 20:00–12:00 | Mão na massa, pela noite, até domingo às 12:00 |

**Domingo, 18/10**

| Horário | Atividade |
|---|---|
| até 12:00 | Entrega do link do repositório no grupo da final, no Slack |
| 12:00–13:00 | Avaliação dos projetos |
| 13:00–15:00 | Apresentações: 7 minutos + 3 minutos de perguntas |
| 15:00–16:00 | Premiações |
| 16:00–18:00 | HH Sobreviventes |

---

## Parte B: o que só aparece nos slides de abertura

**Hackathon: um desafio real da QI Tech para resolver** · Sábado e domingo · 17 e 18/10 · Bootcamp QI Tech 2026 · Risk Solutions

**Quem apresenta o desafio:** Guilherme Bakaukas, Engenharia da Computação Unicamp, Tech Lead de IA.

### 01. Contexto QI Tech

Risk Solutions: antifraude, crédito e compliance para os clientes.

#### O que é

Identificar, analisar e mitigar riscos. Risk Solutions é o conjunto de soluções que ajuda uma empresa a decidir com segurança: quem aceitar, o que aprovar e o que bloquear.

| Pilar | Descrição |
|---|---|
| Fraude | Garantir que a pessoa é quem diz ser e que a transação é legítima. |
| Crédito | Avaliar se vale conceder crédito e em quais condições. |
| Compliance | Cumprir as exigências regulatórias de cadastro e KYC. |

#### O trabalho da BU: três perguntas

| Pergunta | Produto | Descrição |
|---|---|---|
| Quem é essa pessoa? | Onboarding digital e KYC | Validação de identidade no cadastro: documentos, rosto, dispositivo e antecedentes. |
| Essa transação é legítima? | Antifraude Pix e transacional | Análise de cada pagamento antes de ele sair: Pix, TED, boleto e cartão. |
| Vale conceder crédito? | Motor de crédito | Aplicação da política de crédito do cliente para definir limites e condições. |

#### A escala: números da BU

| Número | O quê |
|---|---|
| +20 mi | análises por mês |
| +90 mi | cadastros validados |
| +R$ 98 bi | protegidos contra fraude |
| +120 mi | rostos na base de faces |

### 02. Produtos no fluxo do cliente

Cada produto entra num momento diferente da vida do cliente final.

#### Momento 1 · Cadastro: o onboarding em cinco etapas

| # | Etapa | Descrição |
|---|---|---|
| 01 | Coleta de dados | Nome, CPF, endereço e dados cadastrais. |
| 02 | Documentos | OCR extrai e confere os dados do documento. |
| 03 | Autenticação | Reconhecimento facial, Liveness e Device Scan. |
| 04 | Análise de risco | Background Check e cruzamento com bases. |
| 05 | Decisão | Aprovado ou reprovado, com dossiê de compliance. |

#### O mapa: produtos por momento

| Momento | Quando | Produtos |
|---|---|---|
| 01 · Cadastro | Quando a pessoa entra | Onboarding digital e KYC; OCR de documentos; Reconhecimento facial e Liveness; Device Scan; Background Check |
| 02 · Contratação | Quando a pessoa pede algo | Motor de crédito; Open Finance; QI Sign (assinatura eletrônica) |
| 03 · Transação | Cada vez que o dinheiro se move | Antifraude Pix e transacional; Cadastro de dispositivos Pix |

### 03. Motor de regras

A peça que junta os sinais de todos os produtos e devolve uma decisão.

#### Como o motor decide

| Etapa | Nome | Descrição |
|---|---|---|
| Entrada | Sinais | Dados do cadastro, resultado do rosto, dispositivo, antecedentes, histórico de crédito e da transação. |
| Regras | Critérios do cliente | No code: cada cliente define as próprias regras para aprovar ou recusar cadastros, crédito ou compras. |
| Saída | Decisão | Aprovado, reprovado ou em análise, com o motivo registrado no dossiê. |

### Antifraude Pix

> Desafio do hackathon: uma API que recebe o pedido de Pix e responde: aprova, pede 2FA ou reprova.

### 04. Antifraude transacional

Como um Pix é analisado antes de sair. O conteúdo ("O que muda no Pix", "Exemplos de regras" numerados de 01 a 05 e "As três decisões") é o mesmo das seções 2.1 a 2.3 da Parte A.

### 05. O desafio

Construam o motor antifraude de Pix. O conteúdo (entrada, regras e saída; payload de entrada; campos; payload de saída, com o destaque "Só três campos"; escopo; entregáveis; modelo do README; critérios de avaliação) é o mesmo das seções 1 e 3 a 7 da Parte A.

**A apresentação:** "Vamos avaliar a qualidade da solução proposta e como chegaram nela." Até 7 minutos de apresentação + 3 de perguntas · formato livre.

**Agenda:** igual à seção 8 da Parte A. Os slides escrevem "20:00 → Mão na massa, até domingo 12:00".

**Encerramento:** Risk Solutions. Perguntas? Bora construir.
