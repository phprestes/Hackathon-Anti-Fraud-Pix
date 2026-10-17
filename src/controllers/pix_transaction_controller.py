import json

from sqlalchemy.exc import IntegrityError

from constants import RULE_SET_VERSION
from controllers.base_controller import BaseController
from dtos import PixAnalysisDTO
from errors import InvalidSchema, NotFoundPixTransaction, PixIdConflict
from models import AnalysisStatus
from repositories import PixTransactionRepository


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class PixTransactionController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.pix_transaction_repository = PixTransactionRepository(self.context)

    def analyze(self, payload: dict) -> tuple[dict, bool]:
        """Returns (dto, is_replay)."""
        existing = self._find_replay(payload)
        if existing is not None:
            return existing, True

        metadata = {"reasons": [], "rule_set_version": RULE_SET_VERSION}

        try:
            pix_analysis = self.pix_transaction_repository.create(
                payload=payload,
                status_enumerator=AnalysisStatus.APPROVED,
                metadata=metadata,
                rule_set_version=RULE_SET_VERSION,
                reasons=[],
            )
            pix_analysis_dto = PixAnalysisDTO.obj_to_dict(pix_analysis)
            self.session.commit()
        except IntegrityError:
            # Lost the race on pix_id UNIQUE: the winner's row is the answer.
            self.session.rollback()
            existing = self._find_replay(payload)
            if existing is None:
                raise
            return existing, True
        except ValueError as error:
            self.session.rollback()
            raise InvalidSchema(f"Invalid date: {error}")

        return pix_analysis_dto, False

    def get_by_pix_id(self, pix_id: str) -> dict:
        pix_analysis = self.pix_transaction_repository.get_by_pix_id(pix_id)

        if pix_analysis is None:
            raise NotFoundPixTransaction(pix_id)

        return PixAnalysisDTO.obj_to_dict(pix_analysis)

    def _find_replay(self, payload: dict) -> dict | None:
        pix_analysis = self.pix_transaction_repository.get_by_pix_id(payload["id"])

        if pix_analysis is None:
            return None

        if _canonical(pix_analysis.pix_transaction.payload) != _canonical(payload):
            raise PixIdConflict(payload["id"])

        return PixAnalysisDTO.obj_to_dict(pix_analysis)
