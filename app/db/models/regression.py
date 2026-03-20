from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RegressionAlert(Base):
    __tablename__ = "regression_alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    failure_rate: Mapped[float] = mapped_column(Float, nullable=False)
    window_size: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
