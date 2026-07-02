from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.interfaces.api.v1.schemas.prediction import PredictionRead


class AnalysisRunCreate(BaseModel):
    """Payload to trigger one explicit multimodal analysis run.

    Must reference exactly one PetriImage and one MicroImage. The use case
    layer is responsible for rejecting the request if they do not belong to
    the same Sample (see `AnalysisRun.create` in the domain layer).
    """

    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    model_version_id: UUID


class AnalysisRunRead(BaseModel):
    """Representation of an AnalysisRun returned by the API.

    `status` reflects pipeline progress only, not a microbiological outcome.
    """

    model_config = ConfigDict(from_attributes=True)

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


class AnalysisRunProcessRead(BaseModel):
    """Response of `POST /analysis-runs/{id}/process`.

    `disclaimer` is always present and non-empty: today the only
    `InferenceEnginePort` implementation is `MockInferenceEngine`, a
    deterministic simulation with no real image analysis and no diagnostic
    or taxonomic validity — this field says so directly in the response
    body, not only in external documentation.
    """

    analysis_run: AnalysisRunRead
    prediction: Optional[PredictionRead]
    disclaimer: str
