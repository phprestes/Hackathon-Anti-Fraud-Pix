from tests.utils import PayloadGenerator, RequestGenerator
from tests.utils.requisition import ClientRequisition


class TestPixGet:
    def test_get_after_post_returns_same_body(self):
        """Enunciado 3.4: o GET devolve a análise que foi gravada."""
        payload = PayloadGenerator.pix()
        _, posted = RequestGenerator.POST_pix(payload)

        status, body = RequestGenerator.GET_pix(payload["id"])

        assert status == 200
        assert body == posted

    def test_get_unknown_id_returns_not_found(self):
        status, body = RequestGenerator.GET_pix("pix-that-never-existed")

        assert status == 404
        assert body["code"] == "QIT002001"

    def test_get_response_returns_no_internal_identifiers(self):
        """R5: só key sai da API."""
        payload = PayloadGenerator.pix()
        RequestGenerator.POST_pix(payload)

        _, body = RequestGenerator.GET_pix(payload["id"])

        assert set(body.keys()) == {"key", "status", "metadata"}

    def test_get_without_internal_token_returns_forbidden(self):
        response = ClientRequisition.send("GET", "/pix/transaction/qualquer")

        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
