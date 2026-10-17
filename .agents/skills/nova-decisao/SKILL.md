---
name: nova-decisao
description: Use ao tomar uma decisão de arquitetura, de modelagem, de política do motor ou de processo que alguém vai questionar depois, ou ao mudar o status de um ADR existente.
---

# Nova decisão (ADR)

Uma decisão por arquivo. Não existe RFC ([ADR 0015](../../../docs/02-arquitetura/decisoes/0015-changelog-e-adrs-no-lugar-da-rfc.md)).

1. Copie um ADR de [docs/02-arquitetura/decisoes/](../../../docs/02-arquitetura/decisoes/README.md) com o próximo número: `NNNN-titulo-curto.md`.
2. Front-matter `title`, `summary` (uma frase com a decisão), `related`, `sources`. Logo depois, a trilha `> [Índice] › [Decisões] › NNNN` e `**Status:** proposta`.
3. Seções, no presente e curtas:
   - **Contexto:** o problema e a restrição, citando o enunciado quando houver.
   - **Decisão:** o que fazemos, em itens.
   - **Alternativas descartadas:** cada uma com **Preço** e **Ganharia se**.
   - **Consequências:** o que muda para quem trabalha no código.
4. Linha na tabela do [índice de decisões](../../../docs/02-arquitetura/decisoes/README.md) e no [`llms.txt`](../../../llms.txt).
5. Decisão muda regra de trabalho? Atualize o [`AGENTS.md`](../../../AGENTS.md).
6. **Mudança de status:** `proposta` → `aceita` quando o código entra; decisão revertida vira `substituída por NNNN` e o arquivo fica (R4). Atualize o índice.
7. Skill [registrar-mudanca](../registrar-mudanca/SKILL.md).
