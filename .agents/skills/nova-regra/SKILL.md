---
name: nova-regra
description: Use ao criar, mudar ou calibrar uma regra antifraude do motor (limite, velocity, montante, perfil, contraparte). Guia catálogo, TDD, classe em src/rules/, parâmetro e documentação.
---

# Nova regra antifraude

Contrato e arquitetura: [motor de regras](../../../docs/05-motor/motor-de-regras.md), ADRs [0004](../../../docs/02-arquitetura/decisoes/0004-motor-de-regras-em-codigo.md) a [0008](../../../docs/02-arquitetura/decisoes/0008-parametros-de-regra-por-ambiente.md).

1. **Catálogo primeiro.** Escreva ou ajuste a linha em [docs/05-motor/regras.md](../../../docs/05-motor/regras.md): código `<FAMILIA>_<SINAL>`, lógica, parâmetros com unidade, decisão, **fonte verificada** (normativo do BCB com artigo, ou literatura com autor, ano e link; o que não der para verificar fica marcado "não verificado") e **evidência no PixSim** (disparo, precisão e ablação: `make rule-ablation`). Sem porquê, pare e pergunte ao time: não invente calibragem. Parâmetro só muda com evidência do PixSim, nunca do simulador local (fixture do CI).
2. **Teste vermelho** em `tests/integration/pix/rules/test_<codigo_minusculo>.py`:
   - um teste no limite que **não** dispara (`approved`, regra ausente de `metadata.reasons`);
   - um teste logo depois do limite que dispara (`status` e `rule` em `metadata.reasons`);
   - se a regra tem dois degraus, um teste por degrau.
   Monte o histórico com `POST /pix/transaction` e `transaction_date` escolhido ([estratégia](../../../docs/07-testes/estrategia.md)). Documentos e aparelhos aleatórios por teste. Rode `make test` e confira que falha pelo motivo certo.
3. **Sinal de histórico novo?** Consulta agregada em `src/repositories/pix_transaction_repository.py`, campo novo em `src/rules/rule_context.py`, preenchido no controller. A consulta usa `transaction_date` como "agora" e exclui o próprio Pix.
4. **Parâmetro** em `src/constants.py`: `RULE_<…>_<UNIDADE> = int(os.environ.get("RULE_<…>", "<padrão>"))`.
5. **Classe** `src/rules/<familia>_<sinal>_rule.py`, herdando `BaseRule`. Parâmetros pelo construtor. Sem banco, ambiente ou `datetime.now()`. `reason` em português, com o número que disparou.
6. **Registre** em `ACTIVE_RULES` (`src/rules/__init__.py`).
7. **Documente:** estado da linha no catálogo vira `ativa`; atualize a tabela "Regras" do [README](../../../README.md); acrescente a linha na [matriz regra → teste](../../../docs/01-contexto/requisitos.md#matriz-regra--teste).
8. **Registre a mudança** com a skill [registrar-mudanca](../registrar-mudanca/SKILL.md). Calibragem de parâmetro sempre entra, com valor antigo → novo.
9. **Verde e limpo:** `make reset check`.
