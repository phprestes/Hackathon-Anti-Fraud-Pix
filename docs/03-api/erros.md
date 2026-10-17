---
title: Catálogo de erros
summary: Todo código QIT que a API devolve, com status HTTP, quando sai e a classe correspondente; próximo código livre.
related: [rotas.md, ../02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md]
sources: [bootcamp-base-api src/errors]
---

# Catálogo de erros

> [Índice](../README.md) › API › Erros
>
> **Responde a:** qual código sai em cada recusa? qual classe levanta? qual é o próximo código livre?

O corpo de todo erro é `{title, description, translation, code}`. Os códigos são únicos: o boot falha se houver dois iguais (`error_verification`, em `src/errors/base_error.py`).

**Uma decisão `rejected` não é erro**: sai como 201 com `status: "rejected"` ([ADR 0003](../02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md)). Este catálogo é só para o que impede a análise.

## Faixas

| Faixa | Uso | Onde |
|---|---|---|
| `QIT000xxx` | Genéricos da infraestrutura | `src/errors/base_error.py` (herdado) |
| `QIT001xxx` | Exemplo `sample_entity` do Base Service | `src/errors/custom_errors.py`; saem com o exemplo e não são reutilizados |
| `QIT002xxx` | Domínio do Pix | `src/errors/custom_errors.py` |

## Genéricos (herdados)

| Código | HTTP | Classe | Quando |
|---|---|---|---|
| `QIT000001` | 400 | `InvalidSchema` | Corpo ou query fora do schema |
| `QIT000002` | 403 | `ForbiddenNotInternal` | `INTERNAL-TOKEN` ausente ou errado |
| `QIT000010` | 400 | `InvalidParameter` | Parâmetros que se contradizem |
| `QIT000404` | 404 | `NotFoundResource` | Rota inexistente |
| `QIT000405` | 405 | `MethodNotAllowed` | Método não aceito |
| `QIT000500` | 500 | `InternalError` | Exceção não tratada |

## Domínio do Pix (planejados)

| Código | HTTP | Classe | Quando | Estado |
|---|---|---|---|---|
| `QIT002001` | 404 | `NotFoundPixTransaction` | `GET /pix/transaction/{id}` com `id` nunca recebido | a implementar |
| `QIT002002` | 409 | `PixIdConflict` | `id` já analisado, com corpo diferente ([ADR 0012](../02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)) | a implementar |

**Próximo código livre: `QIT002003`.** Atualize esta linha a cada erro novo.
