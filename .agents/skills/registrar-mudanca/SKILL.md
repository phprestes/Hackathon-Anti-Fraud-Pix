---
name: registrar-mudanca
description: Use ao terminar qualquer tarefa que alterou arquivos do repositório (código, teste, docs, infra, parâmetro de regra). Registra a mudança no CHANGELOG.md com tipo, arquivos, porquê e autor.
---

# Registrar mudança no CHANGELOG

Formato e motivo: [ADR 0015](../../../docs/02-arquitetura/decisoes/0015-changelog-e-adrs-no-lugar-da-rfc.md).

1. Abra [`CHANGELOG.md`](../../../CHANGELOG.md), seção `## [Não lançado]`.
2. Ache a subseção `### AAAA-MM-DD` de hoje. Se não existir, crie no topo da seção, com o cabeçalho da tabela:

   ```markdown
   | Tipo | Mudança | Arquivos | Por quê | Autor |
   |---|---|---|---|---|
   ```

3. Uma linha por mudança lógica (não por arquivo):
   - **Tipo:** `Adicionado`, `Alterado`, `Calibrado`, `Corrigido`, `Removido`, `Movido`, `Documentado`.
   - **Mudança:** o que mudou, em uma frase. Calibragem: `RULE_X: 5 → 8`.
   - **Arquivos:** caminhos principais entre crases; pasta inteira com `/` no fim.
   - **Por quê:** link para o ADR, a linha do catálogo de regras ou o doc que explica. Sem link, uma frase curta.
   - **Autor:** nome da pessoa, ou `agente (<ferramenta>)` quando um agente fez — ex.: `agente (Claude Code)`.
4. Linhas novas entram **no fim** da tabela do dia, para a leitura seguir a ordem em que aconteceu.
5. Não reescreva linhas antigas. Se uma mudança foi desfeita, registre uma linha nova `Removido` ou `Alterado`.
6. No fim do hackathon, `[Não lançado]` vira `[1.0.0] - 2026-10-18` e uma seção `[Não lançado]` vazia é criada acima.

Conferência rápida: `grep "agente" CHANGELOG.md` lista tudo o que agentes mudaram.
