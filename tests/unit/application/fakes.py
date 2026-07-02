"""In-memory test doubles for the application ports.

Used by the Phase 2 use-case unit tests so they exercise real business logic
without touching a database or the filesystem. `PillowImageValidator` is
used directly instead of being faked here: it is pure, deterministic
in-memory computation (no filesystem/network I/O), so faking it would only
hide real validation bugs.
"""

import copy
from types import TracebackType
from typing import Optional
from uuid import UUID

from blueberry_microid.application.exceptions import (
    AnalysisRunNotFoundError,
    DuplicateFinalHumanReviewError,
    DuplicatePredictionError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.inference_engine import InferenceEnginePort, InferenceOutput
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus


class InMemorySampleRepository(SampleRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, Sample] = {}

    def add(self, sample: Sample) -> Sample:
        self._by_id[sample.id] = sample
        return sample

    def get_by_id(self, sample_id: UUID) -> Optional[Sample]:
        return self._by_id.get(sample_id)

    def get_by_sample_code(self, sample_code: str) -> Optional[Sample]:
        return next((s for s in self._by_id.values() if s.sample_code == sample_code), None)


class InMemoryPetriImageRepository(PetriImageRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PetriImage] = {}

    def add(self, petri_image: PetriImage) -> PetriImage:
        self._by_id[petri_image.id] = petri_image
        return petri_image

    def get_by_id(self, petri_image_id: UUID) -> Optional[PetriImage]:
        return self._by_id.get(petri_image_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[PetriImage]:
        return [image for image in self._by_id.values() if image.sample_id == sample_id]


class InMemoryMicroImageRepository(MicroImageRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, MicroImage] = {}

    def add(self, micro_image: MicroImage) -> MicroImage:
        self._by_id[micro_image.id] = micro_image
        return micro_image

    def get_by_id(self, micro_image_id: UUID) -> Optional[MicroImage]:
        return self._by_id.get(micro_image_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[MicroImage]:
        return [image for image in self._by_id.values() if image.sample_id == sample_id]


class InMemoryModelVersionRepository(ModelVersionRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ModelVersion] = {}

    def add(self, model_version: ModelVersion) -> ModelVersion:
        self._by_id[model_version.id] = model_version
        return model_version

    def get_by_id(self, model_version_id: UUID) -> Optional[ModelVersion]:
        return self._by_id.get(model_version_id)

    def list_all(self) -> list[ModelVersion]:
        return sorted(self._by_id.values(), key=lambda model_version: model_version.created_at)


class InMemoryAnalysisRunRepository(AnalysisRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, AnalysisRun] = {}

    def add(self, analysis_run: AnalysisRun) -> AnalysisRun:
        self._by_id[analysis_run.id] = analysis_run
        return analysis_run

    def update(self, analysis_run: AnalysisRun) -> AnalysisRun:
        if analysis_run.id not in self._by_id:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run.id}' does not exist")
        self._by_id[analysis_run.id] = analysis_run
        return analysis_run

    def claim_for_processing(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        run = self._by_id.get(analysis_run_id)
        if run is None or run.status != AnalysisStatus.PENDING:
            return None
        run.mark_processing()
        return run

    def get_by_id(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return self._by_id.get(analysis_run_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[AnalysisRun]:
        return [run for run in self._by_id.values() if run.sample_id == sample_id]


class InMemoryPredictionRepository(PredictionRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, Prediction] = {}

    def add(self, prediction: Prediction) -> Prediction:
        if any(existing.analysis_run_id == prediction.analysis_run_id for existing in self._by_id.values()):
            raise DuplicatePredictionError(
                f"analysis_run '{prediction.analysis_run_id}' already has a prediction"
            )
        self._by_id[prediction.id] = prediction
        return prediction

    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[Prediction]:
        return next((p for p in self._by_id.values() if p.analysis_run_id == analysis_run_id), None)

    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        return self._by_id.get(prediction_id)


class InMemoryHumanReviewRepository(HumanReviewRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, HumanReview] = {}

    def add(self, human_review: HumanReview) -> HumanReview:
        if human_review.is_final and any(
            review.analysis_run_id == human_review.analysis_run_id and review.is_final
            for review in self._by_id.values()
        ):
            raise DuplicateFinalHumanReviewError(
                f"analysis_run '{human_review.analysis_run_id}' already has a final human review"
            )
        self._by_id[human_review.id] = human_review
        return human_review

    def get_by_id(self, human_review_id: UUID) -> Optional[HumanReview]:
        return self._by_id.get(human_review_id)

    def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[HumanReview]:
        return sorted(
            [review for review in self._by_id.values() if review.analysis_run_id == analysis_run_id],
            key=lambda review: (review.created_at, review.id),
        )

    def get_final_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[HumanReview]:
        return next(
            (
                review
                for review in self.list_by_analysis_run_id(analysis_run_id)
                if review.is_final
            ),
            None,
        )

    def unset_final_reviews_for_analysis_run(self, analysis_run_id: UUID) -> int:
        count = 0
        for review in self._by_id.values():
            if review.analysis_run_id == analysis_run_id and review.is_final:
                review.is_final = False
                count += 1
        return count

    def snapshot_state(self) -> dict[UUID, HumanReview]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, HumanReview]) -> None:
        self._by_id = copy.deepcopy(state)


class FakeUnitOfWork(UnitOfWorkPort):
    """In-memory stand-in for `UnitOfWorkPort`.

    Exposes the *same* repository instances passed in (rather than
    snapshot/rollback semantics): good enough to unit-test
    `ProcessAnalysisRunUseCase`'s call sequence and final state without a
    database. Real cross-repository atomicity (a failed write leaving
    nothing behind) is verified separately in
    tests/integration/db/ against the real `SqlAlchemyUnitOfWork` and
    SQLite, where an actual transaction exists to roll back.
    """

    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
        human_review_repository: Optional[HumanReviewRepositoryPort] = None,
    ) -> None:
        self.analysis_run_repository = analysis_run_repository
        self.prediction_repository = prediction_repository
        self.human_review_repository = human_review_repository
        self.entered = False
        self.committed = False
        self._human_review_snapshot = None

    def __enter__(self) -> "FakeUnitOfWork":
        self.entered = True
        if hasattr(self.human_review_repository, "snapshot_state"):
            self._human_review_snapshot = self.human_review_repository.snapshot_state()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if exc_type is not None and self._human_review_snapshot is not None:
            self.human_review_repository.restore_state(self._human_review_snapshot)
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class FakeInferenceEngine(InferenceEnginePort):
    """Returns a fixed, caller-configured InferenceOutput — no hashing, no
    real logic — so use-case tests can control the scenario precisely.
    """

    def __init__(self, output: InferenceOutput) -> None:
        self._output = output

    def process(self, **_kwargs) -> InferenceOutput:
        return self._output


class FailingInferenceEngine(InferenceEnginePort):
    """Always raises, to test ProcessAnalysisRunUseCase's failure handling."""

    def process(self, **_kwargs) -> InferenceOutput:
        raise RuntimeError("simulated inference engine crash")


class FailingAddPredictionRepository(PredictionRepositoryPort):
    """Always raises a generic error on add() — simulates a Prediction
    insert failing for a reason *other* than the duplicate-key constraint
    (e.g. a transient DB error), which ProcessAnalysisRunUseCase must still
    recover from by marking the AnalysisRun `failed`.
    """

    def add(self, prediction: Prediction) -> Prediction:
        raise RuntimeError("simulated prediction insert failure")

    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[Prediction]:
        return None

    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        return None


class FailingAddHumanReviewRepository(HumanReviewRepositoryPort):
    """Delegates reads/updates but always fails when adding a new review."""

    def __init__(self, delegate: HumanReviewRepositoryPort) -> None:
        self._delegate = delegate

    def add(self, human_review: HumanReview) -> HumanReview:
        raise RuntimeError("simulated human review insert failure")

    def get_by_id(self, human_review_id: UUID) -> Optional[HumanReview]:
        return self._delegate.get_by_id(human_review_id)

    def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[HumanReview]:
        return self._delegate.list_by_analysis_run_id(analysis_run_id)

    def get_final_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[HumanReview]:
        return self._delegate.get_final_by_analysis_run_id(analysis_run_id)

    def unset_final_reviews_for_analysis_run(self, analysis_run_id: UUID) -> int:
        return self._delegate.unset_final_reviews_for_analysis_run(analysis_run_id)

    def snapshot_state(self):
        return self._delegate.snapshot_state()

    def restore_state(self, state) -> None:
        self._delegate.restore_state(state)


class UpdateFailingNTimesAnalysisRunRepository(AnalysisRunRepositoryPort):
    """Wraps a real AnalysisRunRepositoryPort; the first `fail_call_count`
    calls to `update()` raise, after which it delegates normally.

    Lets tests simulate "the final status write fails" (fail_call_count=1,
    so the recovery `mark_failed` write that follows succeeds) or "even the
    recovery write fails" (fail_call_count=2 or more).
    """

    def __init__(self, delegate: AnalysisRunRepositoryPort, fail_call_count: int = 1) -> None:
        self._delegate = delegate
        self._fail_call_count = fail_call_count
        self._update_calls = 0

    def add(self, analysis_run: AnalysisRun) -> AnalysisRun:
        return self._delegate.add(analysis_run)

    def update(self, analysis_run: AnalysisRun) -> AnalysisRun:
        self._update_calls += 1
        if self._update_calls <= self._fail_call_count:
            raise RuntimeError(f"simulated database failure on update() call #{self._update_calls}")
        return self._delegate.update(analysis_run)

    def claim_for_processing(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return self._delegate.claim_for_processing(analysis_run_id)

    def get_by_id(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return self._delegate.get_by_id(analysis_run_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[AnalysisRun]:
        return self._delegate.list_by_sample_id(sample_id)


class InMemoryImageStorage(ImageStoragePort):
    """Keeps saved bytes in a dict instead of writing to disk."""

    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}
        self.deleted_paths: list[str] = []

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        path = f"memory://{category.value}/{len(self.saved)}-{original_file_name}"
        self.saved[path] = content
        return path

    def delete(self, path: str) -> None:
        self.deleted_paths.append(path)
        self.saved.pop(path, None)


class AlwaysFailingImageStorage(ImageStoragePort):
    """Fails every save/delete call, to test the "cleanup also fails" path."""

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        raise RuntimeError("simulated storage save failure")

    def delete(self, path: str) -> None:
        raise RuntimeError("simulated storage delete failure")


class FailingDeleteImageStorage(ImageStoragePort):
    """Saves successfully but always fails to delete."""

    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        path = f"memory://{category.value}/{len(self.saved)}-{original_file_name}"
        self.saved[path] = content
        return path

    def delete(self, path: str) -> None:
        raise RuntimeError("simulated storage delete failure")


class FailingPetriImageRepository(PetriImageRepositoryPort):
    """Always raises on add(), to test the orphan-file compensation path."""

    def add(self, petri_image: PetriImage) -> PetriImage:
        raise RuntimeError("simulated database failure")

    def get_by_id(self, petri_image_id: UUID) -> Optional[PetriImage]:
        return None

    def list_by_sample_id(self, sample_id: UUID) -> list[PetriImage]:
        return []


class FailingMicroImageRepository(MicroImageRepositoryPort):
    """Always raises on add(), to test the orphan-file compensation path."""

    def add(self, micro_image: MicroImage) -> MicroImage:
        raise RuntimeError("simulated database failure")

    def get_by_id(self, micro_image_id: UUID) -> Optional[MicroImage]:
        return None

    def list_by_sample_id(self, sample_id: UUID) -> list[MicroImage]:
        return []
