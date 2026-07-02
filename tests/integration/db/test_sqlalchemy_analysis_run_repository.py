import uuid

from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_micro_image_repository import (
    SqlAlchemyMicroImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_model_version_repository import (
    SqlAlchemyModelVersionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_image_repository import (
    SqlAlchemyPetriImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository


def test_add_get_and_list_by_sample(db_session):
    sample = SqlAlchemySampleRepository(db_session).add(Sample(sample_code="S-800"))
    petri_image = SqlAlchemyPetriImageRepository(db_session).add(
        PetriImage(
            sample_id=sample.id, file_path="/petri/a.jpg", file_name="a.jpg", mime_type="image/jpeg",
            file_size_bytes=10,
        )
    )
    micro_image = SqlAlchemyMicroImageRepository(db_session).add(
        MicroImage(
            sample_id=sample.id, file_path="/micro/a.jpg", file_name="a.jpg", mime_type="image/jpeg",
            file_size_bytes=10,
        )
    )
    model_version = SqlAlchemyModelVersionRepository(db_session).add(
        ModelVersion(name="stub-engine", version="0.1.0", model_type=ModelType.MOCK)
    )

    repository = SqlAlchemyAnalysisRunRepository(db_session)
    analysis_run = AnalysisRun.create(
        petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id
    )

    created = repository.add(analysis_run)
    fetched = repository.get_by_id(created.id)
    listed = repository.list_by_sample_id(sample.id)

    assert fetched is not None
    assert fetched.status == AnalysisStatus.PENDING
    assert len(listed) == 1
    assert listed[0].id == created.id


def _build_pending_run(db_session):
    sample = SqlAlchemySampleRepository(db_session).add(Sample(sample_code="S-CLAIM"))
    petri_image = SqlAlchemyPetriImageRepository(db_session).add(
        PetriImage(sample_id=sample.id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    micro_image = SqlAlchemyMicroImageRepository(db_session).add(
        MicroImage(sample_id=sample.id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1)
    )
    model_version = SqlAlchemyModelVersionRepository(db_session).add(
        ModelVersion(name="stub-claim", version="0.1.0", model_type=ModelType.MOCK)
    )
    repository = SqlAlchemyAnalysisRunRepository(db_session)
    run = repository.add(
        AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    )
    return run, repository


def test_claim_for_processing_succeeds_from_pending(db_session):
    run, repository = _build_pending_run(db_session)

    claimed = repository.claim_for_processing(run.id)

    assert claimed is not None
    assert claimed.status == AnalysisStatus.PROCESSING
    assert claimed.started_at is not None
    # The DB row itself must reflect the claim, not just the returned entity.
    assert repository.get_by_id(run.id).status == AnalysisStatus.PROCESSING


def test_claim_for_processing_only_succeeds_once(db_session):
    """This is the concurrency guarantee: a second attempt to claim the same
    AnalysisRun (simulating a racing caller) must find it no longer
    `pending` and get nothing back — never a second successful claim.
    """
    run, repository = _build_pending_run(db_session)

    first_claim = repository.claim_for_processing(run.id)
    second_claim = repository.claim_for_processing(run.id)

    assert first_claim is not None
    assert second_claim is None
    # Still exactly `processing` — the second (failed) attempt must not
    # have reset started_at or otherwise touched the row.
    assert repository.get_by_id(run.id).status == AnalysisStatus.PROCESSING


def test_claim_for_processing_fails_for_nonexistent_run(db_session):
    repository = SqlAlchemyAnalysisRunRepository(db_session)

    assert repository.claim_for_processing(uuid.uuid4()) is None


def test_claim_for_processing_fails_when_already_completed(db_session):
    run, repository = _build_pending_run(db_session)
    run.mark_processing()
    repository.update(run)
    run.mark_completed()
    repository.update(run)

    assert repository.claim_for_processing(run.id) is None
    assert repository.get_by_id(run.id).status == AnalysisStatus.COMPLETED
