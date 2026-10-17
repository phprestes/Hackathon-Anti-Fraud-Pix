from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from models.base import Base
from models.analysis_status import AnalysisStatus
from models.pix_analysis import PixAnalysis


class PixAnalysisReason(Base):
    __tablename__ = "pix_analysis_reason"

    id = Column(Integer, primary_key=True)
    pix_analysis_id = Column(Integer, ForeignKey(PixAnalysis.id), nullable=False)
    rule_code = Column(String(60), nullable=False)
    decision_status_id = Column(Integer, ForeignKey(AnalysisStatus.id), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    pix_analysis = relationship("PixAnalysis", back_populates="reasons")
    decision_status = relationship("AnalysisStatus", foreign_keys=[decision_status_id], lazy="selectin")
