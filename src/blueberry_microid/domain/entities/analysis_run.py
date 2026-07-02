from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.exceptions.errors import (
    CrossSampleAnalysisError,
    InvalidAnalysisRunTransitionError,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AnalysisRun:
    """A single, explicit execution of the multimodal inference pipeline.

    Always references exactly one PetriImage and one MicroImage — never "all
    images" of a Sample implicitly. `status` tracks workflow progress only;
    `needs_review` is not a microbiological class.
    """

    sample_id: UUID
    petri_image_id: UUID
    micro_image_id: UUID
    model_version_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: AnalysisStatus = AnalysisStatus.PENDING
    created_at: datetime = field(default_factory=_utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    @classmethod
    def create(
        cls,
        *,
        petri_image: PetriImage,
        micro_image: MicroImage,
        model_version_id: UUID,
    ) -> "AnalysisRun":
        """Build an AnalysisRun, enforcing that both images belong to the same Sample."""
        if petri_image.sample_id != micro_image.sample_id:
            raise CrossSampleAnalysisError(
                "PetriImage and MicroImage must belong to the same Sample "
                f"(petri_image.sample_id={petri_image.sample_id}, "
                f"micro_image.sample_id={micro_image.sample_id})"
            )
        return cls(
            sample_id=petri_image.sample_id,
            petri_image_id=petri_image.id,
            micro_image_id=micro_image.id,
            model_version_id=model_version_id,
        )

    def mark_processing(self) -> None:
        """Start processing. Only legal from `pending` — this is the
        idempotency guard: an AnalysisRun that already moved past `pending`
        (whatever its current status) cannot be picked up again. Retrying
        means creating a new AnalysisRun, not reusing this one.

        This in-memory check alone cannot prevent two concurrent callers
        from both loading the same `pending` row and both succeeding here
        with their own copy — that race can only be closed at the database
        level. `ProcessAnalysisRunUseCase` therefore does not call this
        method directly; it uses `AnalysisRunRepositoryPort.claim_for_
        processing`, an atomic conditional UPDATE that enforces the same
        `pending -> processing` rule as a single database operation. This
        method remains part of the entity's public contract for direct
        domain-level use and testing.
        """
        if self.status != AnalysisStatus.PENDING:
            raise InvalidAnalysisRunTransitionError(
                f"cannot start processing: AnalysisRun '{self.id}' is '{self.status.value}', expected 'pending'"
            )
        self.status = AnalysisStatus.PROCESSING
        self.started_at = _utcnow()

    def mark_completed(self) -> None:
        """Finish successfully with no review required. Only legal from `processing`."""
        self._require_processing(target="completed")
        self.status = AnalysisStatus.COMPLETED
        self.completed_at = _utcnow()

    def mark_needs_review(self) -> None:
        """Finish successfully but flag for human review. Only legal from `processing`."""
        self._require_processing(target="needs_review")
        self.status = AnalysisStatus.NEEDS_REVIEW
        self.completed_at = _utcnow()

    def mark_failed(self, error_message: str) -> None:
        """Finish unsuccessfully. Only legal from `processing`."""
        self._require_processing(target="failed")
        self.status = AnalysisStatus.FAILED
        self.completed_at = _utcnow()
        self.error_message = error_message

    def _require_processing(self, *, target: str) -> None:
        if self.status != AnalysisStatus.PROCESSING:
            raise InvalidAnalysisRunTransitionError(
                f"cannot mark AnalysisRun '{self.id}' as '{target}': "
                f"current status is '{self.status.value}', expected 'processing'"
            )
