"""Unit tests for AnalyzeTwoUploadedImagesUseCase (Fase 40.1 persistent flow)."""

from types import TracebackType
from typing import Optional
from uuid import UUID

import pytest

from blueberry_microid.application.dto.two_image_upload_dto import TwoImageUploadRequest, TwoImageUploadResult
from blueberry_microid.application.exceptions import (
    DuplicateModelVersionError,
    ImageTooLargeError,
    InvalidImageError,
)
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.image_validator import ImageValidationResult, ImageValidatorPort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.use_cases.analysis.analyze_two_uploaded_images import (
    AnalyzeTwoUploadedImagesUseCase,
)
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    PreliminaryTwoImageAnalysisEngine,
)
from tests.unit.application.image_helpers import make_valid_jpeg_bytes


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeValidator(ImageValidatorPort):
    def __init__(self, *, raise_error: bool = False) -> None:
        self._raise = raise_error

    def validate(self, *, file_name: str, mime_type: str, content: bytes) -> ImageValidationResult:
        if self._raise:
            raise InvalidImageError("fake invalid image")
        return ImageValidationResult(width=32, height=24)


class _FakeStorage(ImageStoragePort):
    def __init__(self, *, fail_on_category: ImageCategory | None = None) -> None:
        self._fail_on = fail_on_category
        self.saved: list[str] = []
        self.deleted: list[str] = []

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        if category == self._fail_on:
            raise OSError("fake storage failure")
        path = f"/fake/{category.value}/{original_file_name}"
        self.saved.append(path)
        return path

    def delete(self, path: str) -> None:
        self.deleted.append(path)


class _FakeSampleRepository(SampleRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[UUID, Sample] = {}

    def add(self, sample: Sample) -> Sample:
        self._store[sample.id] = sample
        return sample

    def get_by_id(self, sample_id: UUID) -> Optional[Sample]:
        return self._store.get(sample_id)

    def get_by_sample_code(self, sample_code: str) -> Optional[Sample]:
        return next((s for s in self._store.values() if s.sample_code == sample_code), None)


class _FakePetriImageRepository(PetriImageRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[UUID, PetriImage] = {}

    def add(self, petri_image: PetriImage) -> PetriImage:
        self._store[petri_image.id] = petri_image
        return petri_image

    def get_by_id(self, petri_image_id: UUID) -> Optional[PetriImage]:
        return self._store.get(petri_image_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[PetriImage]:
        return [p for p in self._store.values() if p.sample_id == sample_id]


class _FakeMicroImageRepository(MicroImageRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[UUID, MicroImage] = {}

    def add(self, micro_image: MicroImage) -> MicroImage:
        self._store[micro_image.id] = micro_image
        return micro_image

    def get_by_id(self, micro_image_id: UUID) -> Optional[MicroImage]:
        return self._store.get(micro_image_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[MicroImage]:
        return [m for m in self._store.values() if m.sample_id == sample_id]


class _FakeModelVersionRepository(ModelVersionRepositoryPort):
    def __init__(self, *, raise_duplicate: bool = False) -> None:
        self._store: list[ModelVersion] = []
        self._raise_duplicate = raise_duplicate

    def add(self, model_version: ModelVersion) -> ModelVersion:
        if self._raise_duplicate:
            self._raise_duplicate = False
            raise DuplicateModelVersionError("duplicate")
        self._store.append(model_version)
        return model_version

    def get_by_id(self, model_version_id: UUID) -> Optional[ModelVersion]:
        return next((mv for mv in self._store if mv.id == model_version_id), None)

    def list_all(self) -> list[ModelVersion]:
        return list(self._store)


class _FakeAnalysisRunRepository(AnalysisRunRepositoryPort):
    def __init__(self) -> None:
        self.added: list[AnalysisRun] = []

    def add(self, analysis_run: AnalysisRun) -> AnalysisRun:
        self.added.append(analysis_run)
        return analysis_run

    def update(self, analysis_run: AnalysisRun) -> AnalysisRun:
        return analysis_run

    def claim_for_processing(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return None

    def get_by_id(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return next((r for r in self.added if r.id == analysis_run_id), None)

    def list_by_sample_id(self, sample_id: UUID) -> list[AnalysisRun]:
        return [r for r in self.added if r.sample_id == sample_id]

    def list_all(self) -> list[AnalysisRun]:
        return list(self.added)


class _FakePredictionRepository(PredictionRepositoryPort):
    def __init__(self) -> None:
        self.added: list[Prediction] = []

    def add(self, prediction: Prediction) -> Prediction:
        self.added.append(prediction)
        return prediction

    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[Prediction]:
        return next((p for p in self.added if p.analysis_run_id == analysis_run_id), None)

    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        return next((p for p in self.added if p.id == prediction_id), None)


class _FakeUnitOfWork(UnitOfWorkPort):
    def __init__(self) -> None:
        self.analysis_run_repository = _FakeAnalysisRunRepository()
        self.prediction_repository = _FakePredictionRepository()
        self.committed = False

    def __enter__(self) -> "_FakeUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


def _make_use_case(
    validator=None,
    storage=None,
    sample_repo=None,
    petri_repo=None,
    micro_repo=None,
    mv_repo=None,
    uow=None,
    max_bytes=None,
):
    uow = uow or _FakeUnitOfWork()
    return AnalyzeTwoUploadedImagesUseCase(
        image_validator=validator or _FakeValidator(),
        upload_storage=storage or _FakeStorage(),
        engine=PreliminaryTwoImageAnalysisEngine(),
        sample_repository=sample_repo or _FakeSampleRepository(),
        petri_image_repository=petri_repo or _FakePetriImageRepository(),
        micro_image_repository=micro_repo or _FakeMicroImageRepository(),
        model_version_repository=mv_repo or _FakeModelVersionRepository(),
        unit_of_work=uow,
        max_upload_size_bytes=max_bytes,
    ), uow


def _make_request(**kwargs):
    jpeg = make_valid_jpeg_bytes()
    defaults = dict(
        petri_file_name="petri.jpg",
        petri_mime_type="image/jpeg",
        petri_content=jpeg,
        micro_file_name="micro.jpg",
        micro_mime_type="image/jpeg",
        micro_content=jpeg,
    )
    defaults.update(kwargs)
    return TwoImageUploadRequest(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_result_with_real_ids():
    use_case, _ = _make_use_case()
    result = use_case.execute(_make_request())
    assert isinstance(result, TwoImageUploadResult)
    assert isinstance(result.analysis_run_id, UUID)
    assert isinstance(result.sample_id, UUID)
    assert isinstance(result.petri_image_id, UUID)
    assert isinstance(result.micro_image_id, UUID)


def test_requires_human_review_always_true():
    use_case, _ = _make_use_case()
    result = use_case.execute(_make_request())
    assert result.requires_human_review is True


def test_persists_analysis_run_and_prediction():
    use_case, uow = _make_use_case()
    result = use_case.execute(_make_request())
    assert uow.committed
    assert len(uow.analysis_run_repository.added) == 1
    assert uow.analysis_run_repository.added[0].id == result.analysis_run_id
    assert len(uow.prediction_repository.added) == 1
    pred = uow.prediction_repository.added[0]
    assert pred.analysis_run_id == result.analysis_run_id
    assert pred.requires_human_review is True


def test_class_probabilities_sum_to_one():
    use_case, _ = _make_use_case()
    result = use_case.execute(_make_request())
    total = sum(result.class_probabilities.values())
    assert abs(total - 1.0) < 0.01


def test_stores_both_images_in_upload_storage():
    storage = _FakeStorage()
    use_case, _ = _make_use_case(storage=storage)
    use_case.execute(_make_request())
    assert len(storage.saved) == 2
    categories = {p.split("/")[2] for p in storage.saved}
    assert "petri" in categories
    assert "micro" in categories


def test_rejects_image_exceeding_max_size():
    use_case, _ = _make_use_case(max_bytes=5)
    with pytest.raises(ImageTooLargeError):
        use_case.execute(_make_request())


def test_rejects_invalid_petri_image():
    use_case, _ = _make_use_case(validator=_FakeValidator(raise_error=True))
    with pytest.raises(InvalidImageError):
        use_case.execute(_make_request())


def test_cleans_up_petri_if_micro_storage_fails():
    storage = _FakeStorage(fail_on_category=ImageCategory.MICRO)
    use_case, _ = _make_use_case(storage=storage)
    with pytest.raises(OSError):
        use_case.execute(_make_request())
    assert len(storage.deleted) == 1
    assert "petri" in storage.deleted[0]


def test_auto_generates_sample_code_when_not_provided():
    sample_repo = _FakeSampleRepository()
    use_case, _ = _make_use_case(sample_repo=sample_repo)
    use_case.execute(_make_request())
    samples = list(sample_repo._store.values())
    assert len(samples) == 1
    assert samples[0].sample_code.startswith("AUTO-")


def test_uses_provided_sample_code():
    sample_repo = _FakeSampleRepository()
    use_case, _ = _make_use_case(sample_repo=sample_repo)
    use_case.execute(_make_request(sample_code="LAB-001"))
    samples = list(sample_repo._store.values())
    assert samples[0].sample_code == "LAB-001"


def test_reuses_existing_model_version_on_duplicate():
    existing_mv = ModelVersion(
        name="PreliminaryTwoImageEngine",
        version="0.1.0",
        model_type=ModelType.MOCK,
    )
    mv_repo = _FakeModelVersionRepository(raise_duplicate=True)
    mv_repo._store.append(existing_mv)
    use_case, uow = _make_use_case(mv_repo=mv_repo)
    result = use_case.execute(_make_request())
    assert result.analysis_run_id is not None
    run = uow.analysis_run_repository.added[0]
    assert run.model_version_id == existing_mv.id


def test_unique_run_ids_per_call():
    use_case, _ = _make_use_case()
    req = _make_request()
    r1 = use_case.execute(req)
    r2 = use_case.execute(req)
    assert r1.analysis_run_id != r2.analysis_run_id
