"""Shared SQLAlchemy Enum column types, backed by the domain enums.

Defined once and imported wherever needed so the same Postgres ENUM type
(e.g. `predicted_label`, reused by both `predictions.predicted_label` and
`human_reviews.corrected_label`) is only declared a single time.
"""

from sqlalchemy import Enum

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.dataset_curation_run_status import DatasetCurationRunStatus
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


def _values(enum_cls: type) -> list:
    return [member.value for member in enum_cls]


model_type_enum = Enum(ModelType, name="model_type", values_callable=_values)
analysis_status_enum = Enum(AnalysisStatus, name="analysis_status", values_callable=_values)
predicted_label_enum = Enum(PredictedLabel, name="predicted_label", values_callable=_values)
review_decision_enum = Enum(ReviewDecision, name="review_decision", values_callable=_values)
dataset_split_enum = Enum(DatasetSplit, name="dataset_split", values_callable=_values)
dataset_curation_status_enum = Enum(
    DatasetCurationStatus, name="dataset_curation_status", values_callable=_values
)
dataset_curation_run_status_enum = Enum(
    DatasetCurationRunStatus, name="dataset_curation_run_status", values_callable=_values
)
