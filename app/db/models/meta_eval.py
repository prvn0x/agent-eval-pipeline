from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class MetaEvalReport(Base):
    __tablename__ = "meta_eval_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversations_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_agreement: Mapped[float] = mapped_column(Float, nullable=False)
    evaluator_calibration: Mapped[list] = mapped_column(JSON, default=lambda: [])
    blind_spots: Mapped[list] = mapped_column(JSON, default=lambda: [])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
