from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    coherence: Mapped[float | None] = mapped_column(Float, nullable=True)

    tool_evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    issues_detected: Mapped[list] = mapped_column(JSON, default=lambda: [])
    improvement_suggestions: Mapped[list] = mapped_column(JSON, default=lambda: [])
    evaluator_scores: Mapped[dict] = mapped_column(JSON, default=lambda: {})

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
