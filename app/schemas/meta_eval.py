from datetime import datetime

from pydantic import BaseModel


class EvaluatorCalibration(BaseModel):
    evaluator: str
    sample_count: int
    agreement_rate: float
    precision: float   # of evaluator's failure flags, how many were correct
    recall: float      # of actual failures, how many did evaluator catch
    f1: float
    false_positive_rate: float  # evaluator flags issue, human says fine
    false_negative_rate: float  # evaluator misses issue human caught


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
