from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AnnotationRecord(Base):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    annotator_id: Mapped[str] = mapped_column(String(100), nullable=False)
    annotations: Mapped[list] = mapped_column(JSON, default=lambda: [])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AgreementRecord(Base):
    __tablename__ = "agreement_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cohen_kappa: Mapped[float | None] = mapped_column(Float, nullable=True)
    annotator_count: Mapped[int] = mapped_column(default=0)
    routing_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    label_distribution: Mapped[dict] = mapped_column(JSON, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
