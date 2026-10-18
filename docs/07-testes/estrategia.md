---
title: Estratégia de testes
summary: Testes black box por HTTP (R1), TDD por regra, histórico montado pela API com datas escolhidas, helpers de tests/utils e como rodar.
related: [../01-contexto/requisitos.md, ../05-motor/regras.md, ../06-operacao/rodando-localmente.md]
sources: [bootcamp-base-api tests/, Aula 3 tarde (TDD), Projeto fase 1 (estratégia)]
---

# Estratégia de testes

> [Índice](../README.md) › Testes › Estratégia
>
> **Responde a:** que tipo de teste escrevemos? como provar uma regra de velocity sem esperar o relógio? onde fica cada helper?

## Black box

O teste fala com a API só por HTTP e confere status e corpo. Nada em `tests/` importa `src/` nem lê o banco (R1). A única exceção herdada é `tests/utils/db_utils.py`, que só **zera** o banco entre testes; o cenário nasce sempre por `POST`.

Consequência para o motor: uma regra é provada mandando Pix pela API, nunca chamando `evaluate()` direto.

## TDD por regra

1. A linha da regra está no [catálogo](../05-motor/regras.md) com parâmetro e decisão.
2. **Dois testes no mínimo**: um no limite que **não** dispara (`approved`) e um logo depois do limite que dispara (`status` e `metadata.reasons[].rule`).
3. Ver o vermelho pelo motivo certo, implementar, ver o verde.
4. A linha entra na [matriz regra → teste](../01-contexto/requisitos.md#matriz-regra--teste).

## Cenários à mão e o simulador como fixture

Os testes são **cenários escritos à mão**: cada um monta o histórico mínimo para uma regra e confere a decisão (113 testes, um arquivo por regra ou por rota em `tests/integration/`). Eles provam que o motor cumpre o catálogo; não medem fricção nem captura. O simulador de tráfego (`scripts/simulate.py`) é uma **fixture do CI, sem valor estatístico**: alimenta a paridade API × backtest (`make parity`) e a trava de regressão (`make calibrate-check`), e suas fraudes são nossas. Fricção, captura, custo e a contribuição de cada regra vêm do PixSim ([validação](../05-motor/validacao-pixsim.md), [ADR 0029](../02-arquitetura/decisoes/0029-pixsim-como-referencia.md)).

## Montando histórico sem relógio

Como o relógio das regras é o `transaction_date` ([ADR 0007](../02-arquitetura/decisoes/0007-relogio-da-transacao.md)), o teste monta o passado mandando Pix com datas escolhidas:

```python
class TestVelocitySourceCount:
    def test_post_pix_fifth_in_ten_minutes_returns_two_factor(self):
        """VELOCITY_SOURCE_COUNT: 5º Pix do mesmo pagador em 10 min pede 2FA."""
        payer = RandomGenerator.document_number()
        base = datetime(2026, 10, 17, 14, 0, tzinfo=BRT)
        for minute in range(4):
            RequestGenerator.POST_pix(PayloadGenerator.pix(payer=payer, at=base + timedelta(minutes=minute)))

        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(payer=payer, at=base + timedelta(minutes=5)))

        assert status == 201
        assert body["status"] == "two_factor_required"
        assert "VELOCITY_SOURCE_COUNT" in [r["rule"] for r in body["metadata"]["reasons"]]
```

Cada teste gera documentos e aparelhos aleatórios, para que o histórico de um teste não dispare regra em outro.

## O que todo teste de rota confere

- `POST` grava e o `GET /pix/transaction/{id}` devolve o mesmo corpo (critério 4).
- Repetir o `POST` com o mesmo corpo devolve 200 e **não** aumenta a velocity ([ADR 0012](../02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)).
- Campo desconhecido, `amount` decimal ou zero → 400 `QIT000001`.

## Helpers (`tests/utils/`, herdados)

| Arquivo | Papel |
|---|---|
| `request_generator.py` | Uma função por rota (`POST_…`, `GET_…`), já com `INTERNAL-TOKEN` |
| `payload_generator.py` | Corpos válidos com valores aleatórios; o teste sobrescreve só o que importa |
| `object_generator.py` | Cria cenários completos pela API |
| `random_generator.py` | CPF válido, strings, números |
| `db_utils.py` | Zera o banco; nunca monta cenário |

## Nomes

`test_<ação>_<cenário>_returns_<status>` para erros de API e `test_post_pix_<cenário>_returns_<decisão>` para regras. A docstring cita o código da regra ou a exigência (E/R).

## Como rodar

```bash
make all      # sobe api, db e worker, espera healthy, cria .venv 3.11 e roda pytest -v
make test     # só os testes (api já de pé)
```
