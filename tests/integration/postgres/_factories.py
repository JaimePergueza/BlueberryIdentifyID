"""Helpers to build the FK chain (sample -> images -> analysis_run) directly
via the ORM models, for the PostgreSQL schema/constraint tests.

These deliberately use the ORM *models* (not the domain entities), so a test
can construct rows that a domain entity would reject (e.g. an out-of-range
confidence_score) in order to prove the *database* constraint is what stops
them.
"""

from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.infrastructure.db.models import (
    AnalysisRunModel,
    MicroImageModel,
    ModelVersionModel,
    PetriImageModel,
    SampleModel,
)


def create_sample(session, sample_code: str = "S-PG-1") -> SampleModel:
    sample = SampleModel(sample_code=sample_code)
    session.add(sample)
    session.flush()
    return sample


def create_model_version(session, name: str = "pg-mock", version: str = "0.1.0") -> ModelVersionModel:
    model_version = ModelVersionModel(name=name, version=version, model_type=ModelType.MOCK)
    session.add(model_version)
    session.flush()
    return model_version


def create_petri_image(session, sample_id) -> PetriImageModel:
    image = PetriImageModel(
        sample_id=sample_id,
        file_path="/pg/petri.jpg",
        file_name="petri.jpg",
        mime_type="image/jpeg",
        file_size_bytes=10,
    )
    session.add(image)
    session.flush()
    return image


def create_micro_image(session, sample_id) -> MicroImageModel:
    image = MicroImageModel(
        sample_id=sample_id,
        file_path="/pg/micro.png",
        file_name="micro.png",
        mime_type="image/png",
        file_size_bytes=10,
    )
    session.add(image)
    session.flush()
    return image


def create_analysis_run(session, sample_code: str = "S-PG-1") -> AnalysisRunModel:
    """Create a full, valid analysis_run row and its dependencies."""
    sample = create_sample(session, sample_code=sample_code)
    petri = create_petri_image(session, sample.id)
    micro = create_micro_image(session, sample.id)
    model_version = create_model_version(session, name=f"pg-mock-{sample_code}")
    run = AnalysisRunModel(
        sample_id=sample.id,
        petri_image_id=petri.id,
        micro_image_id=micro.id,
        model_version_id=model_version.id,
    )
    session.add(run)
    session.flush()
    return run
