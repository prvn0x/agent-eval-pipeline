from datetime import datetime

from pydantic import BaseModel


class EvaluatorCalibration(BaseModel):
    evaluator: str
    sample_count: int
    agreement_rate: float
    false_positive_rate: float  # evaluator flags fail, human says pass
    false_negative_rate: float  # evaluator says pass, human flags issues


class BlindSpot(BaseModel):
    issue_type: str
    human_flagged_count: int
    evaluator_missed_count: int


class MetaEvalResponse(BaseModel):
    conversations_analyzed: int
    overall_agreement: float
    evaluator_calibration: list[EvaluatorCalibration]
    blind_spots: list[BlindSpot]
    run_at: datetime
