from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ImprovementSuggestion(Base):
    __tablename__ = "improvement_suggestions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_version: Mapped[str] = mapped_column(String, nullable=False, index=True)
    pattern_type: Mapped[str] = mapped_column(String, nullable=False)
    pattern_summary: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)  # prompt | tool | training
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
