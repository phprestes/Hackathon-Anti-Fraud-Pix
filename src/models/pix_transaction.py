from sqlalchemy import BigInteger, CHAR, Column, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import INET, JSONB, TIMESTAMP
from models.base import Base


class PixTransaction(Base):
    __tablename__ = "pix_transaction"

    id = Column(Integer, primary_key=True)
    pix_id = Column(String(100), nullable=False)
    amount = Column(BigInteger, nullable=False)
    transaction_date = Column(TIMESTAMP(timezone=True), nullable=False)
    source_branch = Column(String(10), nullable=False)
    source_account_number = Column(String(20), nullable=False)
    source_opening_date = Column(TIMESTAMP(timezone=True), nullable=False)
    source_document_number = Column(String(18), nullable=False)
    destination_participant = Column(CHAR(8), nullable=False)
    destination_branch = Column(String(10), nullable=False)
    destination_account_number = Column(String(20), nullable=False)
    destination_opening_date = Column(TIMESTAMP(timezone=True), nullable=False)
    destination_document_number = Column(String(18), nullable=False)
    device_id = Column(String(100), nullable=False)
    channel = Column(String(30), nullable=False)
    ip = Column(INET, nullable=False)
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("pix_id"),)
