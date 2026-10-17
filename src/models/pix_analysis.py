from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import Base
from models.analysis_status import AnalysisStatus
from models.pix_transaction import PixTransaction


class PixAnalysis(Base):
    __tablename__ = "pix_analysis"

    id = Column(Integer, primary_key=True)
    analysis_key = Column(CHAR(36), nullable=False)
    pix_transaction_id = Column(Integer, ForeignKey(PixTransaction.id), nullable=False)
    status_id = Column(Integer, ForeignKey(AnalysisStatus.id), nullable=False)
    # "metadata" is reserved on declarative classes, so the attribute is renamed.
    analysis_metadata = Column("metadata", JSONB, nullable=False)
    rule_set_version = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("analysis_key"), UniqueConstraint("pix_transaction_id"))

    status = relationship("AnalysisStatus", foreign_keys=[status_id], lazy="selectin")
    pix_transaction = relationship("PixTransaction", foreign_keys=[pix_transaction_id], lazy="selectin")
    reasons = relationship("PixAnalysisReason", back_populates="pix_analysis", order_by="PixAnalysisReason.id")
