import copy
import re
from uuid import UUID

from tests.utils import INTERNAL_TOKEN, PayloadGenerator, RandomGenerator, RequestGenerator
from tests.utils.requisition import ClientRequisition


def _id_keys(value, found=None):
    found = [] if found is None else found
    if isinstance(value, dict):
        for key, inner in value.items():
            if key == "id" or key.endswith("_id"):
                found.append(key)
            _id_keys(inner, found)
    elif isinstance(value, list):
        for item in value:
            _id_keys(item, found)
    return found


class TestPixPost:
    def test_post_valid_payload_returns_created(self):
        """Enunciado 3.3: saída exatamente {key, status, metadata}."""
        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix())

        assert status == 201
        assert set(body.keys()) == {"key", "status", "metadata"}
        assert str(UUID(body["key"])) == body["key"]
        assert body["status"] == "approved"
        assert body["metadata"]["reasons"] == []

    def test_post_response_returns_no_internal_identifiers(self):
        """R5: só key sai da API; nada de id nem chaves terminadas em _id."""
        _, body = RequestGenerator.POST_pix(PayloadGenerator.pix())

        assert _id_keys(body) == []

    def test_post_same_body_twice_returns_ok_with_same_key(self):
        """ADR 0012: retry idempotente devolve a análise original."""
        payload = PayloadGenerator.pix()
        first_status, first = RequestGenerator.POST_pix(payload)
        second_status, second = RequestGenerator.POST_pix(payload)

        assert first_status == 201
        assert second_status == 200
        assert second["key"] == first["key"]
        assert second == first

    def test_post_same_id_different_amount_returns_conflict(self):
        """ADR 0012: mesmo id com corpo diferente é 409 QIT002002."""
        payload = PayloadGenerator.pix(amount=15000)
        RequestGenerator.POST_pix(payload)

        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(pix_id=payload["id"], amount=99999))

        assert status == 409
        assert body["code"] == "QIT002002"

    def test_post_without_geolocation_returns_created(self):
        """Enunciado 3.2: geolocation é opcional."""
        payload = PayloadGenerator.pix()
        assert "geolocation" not in payload["source"]

        status, _ = RequestGenerator.POST_pix(payload)

        assert status == 201

    def test_post_with_geolocation_returns_created(self):
        payload = PayloadGenerator.pix(geolocation={"latitude": -23.56, "longitude": -46.65})

        status, _ = RequestGenerator.POST_pix(payload)

        assert status == 201

    def test_post_geolocation_without_longitude_returns_bad_request(self):
        """Geolocation presente exige latitude e longitude."""
        payload = PayloadGenerator.pix(geolocation={"latitude": -23.56, "longitude": -46.65})
        del payload["source"]["geolocation"]["longitude"]

        status, body = RequestGenerator.POST_pix(payload)

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_unknown_field_at_root_returns_bad_request(self):
        """Schema fechado: campo desconhecido na raiz."""
        payload = PayloadGenerator.pix()
        payload["surprise"] = 1

        status, body = RequestGenerator.POST_pix(payload)

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_unknown_field_in_source_account_returns_bad_request(self):
        """Schema fechado: campo desconhecido em objeto aninhado."""
        payload = PayloadGenerator.pix()
        payload["source_account"]["surprise"] = 1

        status, body = RequestGenerator.POST_pix(payload)

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_amount_zero_returns_bad_request(self):
        """ADR 0010: amount >= 1 centavo."""
        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(amount=0))

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_amount_decimal_returns_bad_request(self):
        """ADR 0010: dinheiro é inteiro em centavos, nunca float."""
        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(amount=150000.5))

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_amount_string_returns_bad_request(self):
        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(amount="15000"))

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_document_without_mask_returns_bad_request(self):
        """Enunciado: documentos mascarados (CPF/CNPJ)."""
        unmasked = re.sub(r"\D", "", RandomGenerator.generate_cpf())

        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(payer_document=unmasked))

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_masked_cnpj_returns_created(self):
        """Enunciado 3.2: document_number pode ser CNPJ."""
        payload = PayloadGenerator.pix(payer_document=RandomGenerator.generate_cnpj())

        status, _ = RequestGenerator.POST_pix(payload)

        assert status == 201

    def test_post_date_without_timezone_returns_bad_request(self):
        """ADR 0007: transaction_date precisa de fuso."""
        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(at="2026-10-17T14:00:00"))

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_impossible_calendar_date_returns_bad_request(self):
        """Data com formato certo mas inexistente não pode virar 500."""
        status, body = RequestGenerator.POST_pix(PayloadGenerator.pix(at="2026-02-30T14:00:00-03:00"))

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_missing_required_field_returns_bad_request(self):
        payload = PayloadGenerator.pix()
        broken = copy.deepcopy(payload)
        del broken["source"]["device_id"]

        status, body = RequestGenerator.POST_pix(broken)

        assert status == 400
        assert body["code"] == "QIT000001"

    def test_post_without_internal_token_returns_forbidden(self):
        response = ClientRequisition.send("POST", "/pix/transaction", payload=PayloadGenerator.pix())

        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

    def test_post_with_wrong_internal_token_returns_forbidden(self):
        response = ClientRequisition.send(
            "POST",
            "/pix/transaction",
            payload=PayloadGenerator.pix(),
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN + "x"},
        )

        assert response.response_status == 403
