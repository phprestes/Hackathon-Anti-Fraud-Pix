---
name: novo-erro
description: Use quando a API precisa recusar um pedido com um código QIT novo (formato, conflito, inexistente). Não use para decisão antifraude — rejected não é erro.
---

# Novo erro

Antes: a recusa impede a análise? Se é "o Pix é arriscado", não é erro, é regra com `rejected` ([ADR 0003](../../../docs/02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md)); use a skill [nova-regra](../nova-regra/SKILL.md).

1. Abra [docs/03-api/erros.md](../../../docs/03-api/erros.md) e pegue o próximo código livre da faixa `QIT002xxx`.
2. Escreva o teste que espera o `status` HTTP e `response["code"]` com esse código.
3. Crie a classe em `src/errors/custom_errors.py`, copiando o formato das vizinhas: `code` como atributo de classe, `title` e `description` em inglês, `translation` em português.
4. Status: 400 formato; 404 inexistente; 409 conflito de estado (ex.: `id` repetido com outro corpo); 422 valor que não pode existir.
5. Levante o erro no controller, nunca no resource.
6. Linha no catálogo e próximo código livre atualizado. Rota afetada? Atualize [rotas.md](../../../docs/03-api/rotas.md).
7. Skill [registrar-mudanca](../registrar-mudanca/SKILL.md).
8. `make reset check`. Código duplicado derruba o boot.
