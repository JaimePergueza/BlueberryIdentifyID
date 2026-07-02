from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from blueberry_microid.application.dto.prediction_dto import PredictionDTO
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus


@dataclass(frozen=True, slots=True)
class CreateAnalysisRunRequest:
    """Input for CreateAnalysisRunUseCase.

    All four references are resolved and cross-checked by the use case; this
    request never triggers inference, prediction, or Celery — it only
    prepares a `pending` AnalysisRun row.
    """

    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    model_version_id: UUID


@dataclass(frozen=True, slots=True)
class AnalysisRunDTO:
    """Output representation of an AnalysisRun, decoupled from the ORM model."""

    id: UUID
    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    model_version_id: UUID
    status: AnalysisStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

    @classmethod
    def from_entity(cls, analysis_run: AnalysisRun) -> "AnalysisRunDTO":
        return cls(
            id=analysis_run.id,
            sample_id=analysis_run.sample_id,
            petri_image_id=analysis_run.petri_image_id,
            micro_image_id=analysis_run.micro_image_id,
            model_version_id=analysis_run.model_version_id,
            status=analysis_run.status,
            created_at=analysis_run.created_at,
            started_at=analysis_run.started_at,
            completed_at=analysis_run.completed_at,
            error_message=analysis_run.error_message,
        )


@dataclass(frozen=True, slots=True)
class ProcessAnalysisRunResult:
    """Output of ProcessAnalysisRunUseCase.

    Returned only for successful processing. `prediction` remains optional
    at the DTO boundary for schema compatibility, but controlled processing
    failures now raise application errors after marking the AnalysisRun
    `failed`; they are not represented as a successful result.
    """

    analysis_run: AnalysisRunDTO
    prediction: Optional[PredictionDTO]
