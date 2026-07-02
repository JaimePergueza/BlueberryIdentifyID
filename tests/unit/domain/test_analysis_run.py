from uuid import uuid4

import pytest

from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.exceptions.errors import CrossSampleAnalysisError, InvalidAnalysisRunTransitionError


def _petri_image(sample_id):
    return PetriImage(
        sample_id=sample_id,
        file_path="/storage/petri/a.jpg",
        file_name="a.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024,
    )


def _micro_image(sample_id):
    return MicroImage(
        sample_id=sample_id,
        file_path="/storage/micro/a.jpg",
        file_name="a.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024,
    )


def test_analysis_run_created_when_images_belong_to_same_sample():
    sample = Sample(sample_code="S-010")
    petri_image = _petri_image(sample.id)
    micro_image = _micro_image(sample.id)

    run = AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=uuid4())

    assert run.sample_id == sample.id
    assert run.petri_image_id == petri_image.id
    assert run.micro_image_id == micro_image.id
    assert run.status == AnalysisStatus.PENDING


def test_analysis_run_rejects_images_from_different_samples():
    sample_a = Sample(sample_code="S-011")
    sample_b = Sample(sample_code="S-012")
    petri_image = _petri_image(sample_a.id)
    micro_image = _micro_image(sample_b.id)

    with pytest.raises(CrossSampleAnalysisError):
        AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=uuid4())


def _pending_run() -> AnalysisRun:
    sample = Sample(sample_code="S-013")
    return AnalysisRun.create(
        petri_image=_petri_image(sample.id), micro_image=_micro_image(sample.id), model_version_id=uuid4()
    )


def test_mark_processing_sets_started_at():
    run = _pending_run()

    run.mark_processing()

    assert run.status == AnalysisStatus.PROCESSING
    assert run.started_at is not None


def test_mark_processing_twice_is_rejected():
    run = _pending_run()
    run.mark_processing()

    with pytest.raises(InvalidAnalysisRunTransitionError):
        run.mark_processing()


def test_mark_completed_requires_processing_first():
    run = _pending_run()

    with pytest.raises(InvalidAnalysisRunTransitionError):
        run.mark_completed()


def test_mark_completed_sets_completed_at():
    run = _pending_run()
    run.mark_processing()

    run.mark_completed()

    assert run.status == AnalysisStatus.COMPLETED
    assert run.completed_at is not None


def test_mark_needs_review_sets_completed_at():
    run = _pending_run()
    run.mark_processing()

    run.mark_needs_review()

    assert run.status == AnalysisStatus.NEEDS_REVIEW
    assert run.completed_at is not None


def test_mark_failed_sets_error_message_and_completed_at():
    run = _pending_run()
    run.mark_processing()

    run.mark_failed("boom")

    assert run.status == AnalysisStatus.FAILED
    assert run.error_message == "boom"
    assert run.completed_at is not None


def test_cannot_reprocess_a_completed_run():
    run = _pending_run()
    run.mark_processing()
    run.mark_completed()

    with pytest.raises(InvalidAnalysisRunTransitionError):
        run.mark_processing()


def test_cannot_reprocess_a_failed_run():
    run = _pending_run()
    run.mark_processing()
    run.mark_failed("boom")

    with pytest.raises(InvalidAnalysisRunTransitionError):
        run.mark_processing()
