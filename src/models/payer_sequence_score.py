from sqlalchemy import Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base


class PayerSequenceScore(Base):
    __tablename__ = "payer_sequence_score"

    id = Column(Integer, primary_key=True)
    document_number = Column(String(18), nullable=False)
    model = Column(String(30), nullable=False)
    score = Column(Numeric(6, 5), nullable=False)
    features = Column(JSONB, nullable=False)
    computed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
