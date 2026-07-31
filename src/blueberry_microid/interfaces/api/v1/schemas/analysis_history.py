"""HTTP contracts for the AnalysisRun history and detail read endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.application.dto.analysis_history_dto import ReviewStatus
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


class AnalysisHistoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_run_id: UUID
    sample_id: UUID
    sample_code: str
    petri_image_id: UUID
    micro_image_id: UUID
    model_version_id: UUID
    model_name: str
    model_version: str
    model_type: ModelType
    analysis_status: AnalysisStatus
    created_at: datetime
    completed_at: Optional[datetime]
    preliminary_label: Optional[PredictedLabel]
    confidence_score: Optional[float]
    requires_human_review: bool
    review_status: ReviewStatus
    final_review_id: Optional[UUID]
    review_decision: Optional[ReviewDecision]
    reviewer_name: Optional[str]
    reviewed_at: Optional[datetime]
    final_label: Optional[PredictedLabel]
    final_status: str


class AnalysisHistoryPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AnalysisHistoryItemRead]
    page: int
    page_size: int
    total: int
    total_pages: int


class AnalysisRunDetailSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: AnalysisStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class SampleDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_code: str
    product: str
    lot_code: Optional[str]
    origin: Optional[str]
    collection_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime


class PetriImageDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    mime_type: str
    file_size_bytes: int
    width: Optional[int]
    height: Optional[int]
    captured_at: Optional[datetime]
    culture_medium: Optional[str]
    incubation_temperature_c: Optional[float]
    incubation_time_hours: Optional[float]
    seeding_date: Optional[datetime]
    observed_colony_color: Optional[str]
    observed_colony_shape: Optional[str]
    observed_colony_margin: Optional[str]
    observed_colony_texture: Optional[str]
    notes: Optional[str]


class MicroImageDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    mime_type: str
    file_size_bytes: int
    width: Optional[int]
    height: Optional[int]
    captured_at: Optional[datetime]
    magnification: Optional[str]
    microscope_type: Optional[str]
    staining_method: Optional[str]
    preparation_method: Optional[str]
    observed_structures: Optional[str]
    notes: Optional[str]


class ModelVersionDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    model_type: ModelType
    description: Optional[str]


class PredictionDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    predicted_label: PredictedLabel
    confidence_score: Optional[float]
    class_probabilities: Optional[dict[str, float]]
    technical_observation: Optional[str]
    requires_human_review: bool
    explanation: Optional[str]
    feature_summary: Optional[dict[str, object]]
    quality_summary: Optional[dict[str, object]]
    decision_trace: Optional[list[object]]
    warnings: Optional[list[str]]
    created_at: datetime


class HumanReviewDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reviewer_name: str
    review_decision: ReviewDecision
    corrected_label: Optional[PredictedLabel]
    comments: Optional[str]
    is_final: bool
    created_at: datetime


class AnalysisRunDetailRead(BaseModel):
    """Safe consolidated traceability response; it intentionally has no path fields."""

    model_config = ConfigDict(from_attributes=True)

    analysis_run: AnalysisRunDetailSummaryRead
    sample: SampleDetailRead
    petri_image: PetriImageDetailRead
    micro_image: MicroImageDetailRead
    model_version: ModelVersionDetailRead
    prediction: Optional[PredictionDetailRead]
    human_review: Optional[HumanReviewDetailRead]
    final_label: Optional[PredictedLabel]
    final_status: str
    human_review_completed: bool
    requires_human_review: bool
