from datetime import datetime

from pydantic import BaseModel


class RegressionAlertItem(BaseModel):
    id: str
    agent_version: str
    failure_rate: float
    window_size: int
    threshold: float
    created_at: datetime


class RegressionAlertsResponse(BaseModel):
    total: int
    alerts: list[RegressionAlertItem]
