import pytest

from blueberry_microid.application.dto.analysis_run_dto import CreateAnalysisRunRequest
from blueberry_microid.application.use_cases.inference.create_analysis_run import CreateAnalysisRunUseCase
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.exceptions.errors import CrossSampleAnalysisError
from tests.unit.application.fakes import (
    InMemoryAnalysisRunRepository,
    InMemoryMicroImageRepository,
    InMemoryModelVersionRepository,
    InMemoryPetriImageRepository,
    InMemorySampleRepository,
)


def _build_use_case():
    sample_repository = InMemorySampleRepository()
    petri_repository = InMemoryPetriImageRepository()
    micro_repository = InMemoryMicroImageRepository()
    model_version_repository = InMemoryModelVersionRepository()
    analysis_run_repository = InMemoryAnalysisRunRepository()
    use_case = CreateAnalysisRunUseCase(
        sample_repository, petri_repository, micro_repository, model_version_repository, analysis_run_repository
    )
    return use_case, sample_repository, petri_repository, micro_repository, model_version_repository


def _petri_image(sample_id):
    return PetriImage(
        sample_id=sample_id, file_path="/petri/a.jpg", file_name="a.jpg", mime_type="image/jpeg", file_size_bytes=10
    )


def _micro_image(sample_id):
    return MicroImage(
        sample_id=sample_id, file_path="/micro/a.jpg", file_name="a.jpg", mime_type="image/jpeg", file_size_bytes=10
    )


def test_create_analysis_run_with_petri_and_micro_from_same_sample():
    use_case, sample_repository, petri_repository, micro_repository, model_version_repository = _build_use_case()
    sample = sample_repository.add(Sample(sample_code="S-400"))
    petri_image = petri_repository.add(_petri_image(sample.id))
    micro_image = micro_repository.add(_micro_image(sample.id))
    model_version = model_version_repository.add(ModelVersion(name="stub", version="0.1.0", model_type=ModelType.MOCK))

    dto = use_case.execute(
        CreateAnalysisRunRequest(
            sample_id=sample.id,
            petri_image_id=petri_image.id,
            micro_image_id=micro_image.id,
            model_version_id=model_version.id,
        )
    )

    assert dto.status == AnalysisStatus.PENDING
    assert dto.sample_id == sample.id


def test_create_analysis_run_rejects_petri_and_micro_from_different_samples():
    use_case, sample_repository, petri_repository, micro_repository, model_version_repository = _build_use_case()
    sample_a = sample_repository.add(Sample(sample_code="S-401"))
    sample_b = sample_repository.add(Sample(sample_code="S-402"))
    petri_image = petri_repository.add(_petri_image(sample_a.id))
    micro_image = micro_repository.add(_micro_image(sample_b.id))
    model_version = model_version_repository.add(ModelVersion(name="stub", version="0.1.0", model_type=ModelType.MOCK))

    with pytest.raises(CrossSampleAnalysisError):
        use_case.execute(
            CreateAnalysisRunRequest(
                sample_id=sample_a.id,
                petri_image_id=petri_image.id,
                micro_image_id=micro_image.id,
                model_version_id=model_version.id,
            )
        )
