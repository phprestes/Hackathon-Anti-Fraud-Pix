from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PixTransactionController
from utils.schema_handler import SchemaHandler


class PixTransactionResource:
    @SchemaHandler.validate("post_pix_transaction.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = PixTransactionController()
        pix_analysis, is_replay = controller.analyze(payload)

        return JSONResponse(
            content=jsonable_encoder(pix_analysis),
            status_code=http_status.HTTP_200_OK if is_replay else http_status.HTTP_201_CREATED,
        )

    def on_get_by_id(self, pix_id: str) -> JSONResponse:
        controller = PixTransactionController()
        pix_analysis = controller.get_by_pix_id(pix_id)

        return JSONResponse(
            content=jsonable_encoder(pix_analysis),
            status_code=http_status.HTTP_200_OK,
        )
