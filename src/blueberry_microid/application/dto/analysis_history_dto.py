"""Read-only DTOs for the analysis history and consolidated detail API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Literal, Optional, TypeAlias
from uuid import UUID

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision

ReviewStatus: TypeAlias = Literal["pending", "reviewed"]
JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


@dataclass(frozen=True, slots=True)
class AnalysisHistoryFilters:
    """Validated filters shared by the list use case and query adapter."""

    page: int = 1
    page_size: int = 20
    sample_code: Optional[str] = None
    status: Optional[AnalysisStatus] = None
    review_status: Optional[ReviewStatus] = None
    preliminary_label: Optional[PredictedLabel] = None
    final_label: Optional[PredictedLabel] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be at least 1")
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if self.created_from is not None and self.created_to is not None:
            if self.created_from > self.created_to:
                raise ValueError("created_from must be earlier than or equal to created_to")
        if self.sample_code is not None:
            normalized = self.sample_code.strip()
            object.__setattr__(self, "sample_code", normalized or None)


@dataclass(frozen=True, slots=True)
class AnalysisHistoryItemDTO:
    """Compact, safe summary displayed in an analysis-history row."""

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


@dataclass(frozen=True, slots=True)
class AnalysisHistoryPageDTO:
    """Stable page of history results."""

    items: tuple[AnalysisHistoryItemDTO, ...]
    page: int
    page_size: int
    total: int
    total_pages: int

    @staticmethod
    def total_pages_for(total: int, page_size: int) -> int:
        if total < 0:
            raise ValueError("total cannot be negative")
        if page_size < 1:
            raise ValueError("page_size must be at least 1")
        return ceil(total / page_size) if total else 0

    @classmethod
    def create(
        cls,
        *,
        items: tuple[AnalysisHistoryItemDTO, ...],
        page: int,
        page_size: int,
        total: int,
    ) -> "AnalysisHistoryPageDTO":
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=cls.total_pages_for(total, page_size),
        )


@dataclass(frozen=True, slots=True)
class AnalysisRunDetailSummaryDTO:
    id: UUID
    status: AnalysisStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


@dataclass(frozen=True, slots=True)
class SampleDetailDTO:
    id: UUID
    sample_code: str
    product: str
    lot_code: Optional[str]
    origin: Optional[str]
    collection_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PetriImageDetailDTO:
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


@dataclass(frozen=True, slots=True)
class MicroImageDetailDTO:
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


@dataclass(frozen=True, slots=True)
class ModelVersionDetailDTO:
    id: UUID
    name: str
    version: str
    model_type: ModelType
    description: Optional[str]


@dataclass(frozen=True, slots=True)
class PredictionDetailDTO:
    id: UUID
    predicted_label: PredictedLabel
    confidence_score: Optional[float]
    class_probabilities: Optional[dict[str, float]]
    technical_observation: Optional[str]
    requires_human_review: bool
    explanation: Optional[str]
    feature_summary: Optional[dict[str, JSONValue]]
    quality_summary: Optional[dict[str, JSONValue]]
    decision_trace: Optional[list[JSONValue]]
    warnings: Optional[list[str]]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class HumanReviewDetailDTO:
    id: UUID
    reviewer_name: str
    review_decision: ReviewDecision
    corrected_label: Optional[PredictedLabel]
    comments: Optional[str]
    is_final: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AnalysisRunDetailDTO:
    """Consolidated traceability view with no internal storage paths."""

    analysis_run: AnalysisRunDetailSummaryDTO
    sample: SampleDetailDTO
    petri_image: PetriImageDetailDTO
    micro_image: MicroImageDetailDTO
    model_version: ModelVersionDetailDTO
    prediction: Optional[PredictionDetailDTO]
    human_review: Optional[HumanReviewDetailDTO]
    final_label: Optional[PredictedLabel]
    final_status: str
    human_review_completed: bool
    requires_human_review: bool
