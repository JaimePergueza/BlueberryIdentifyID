from uuid import uuid4

from blueberry_microid.application.dto.dataset_curation_dto import DatasetCurationPolicy
from blueberry_microid.application.services.dataset_curation_evaluator import DatasetCurationEvaluator
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision


def _candidate(decision=ReviewDecision.CONFIRMED, corrected_label=None):
    sample_id = uuid4()
    petri = PetriImage(
        sample_id=sample_id,
        file_path="/safe/petri.jpg",
        file_name="petri.jpg",
        mime_type="image/jpeg",
        file_size_bytes=10,
    )
    micro = MicroImage(
        sample_id=sample_id,
        file_path="/safe/micro.jpg",
        file_name="micro.jpg",
        mime_type="image/jpeg",
        file_size_bytes=10,
    )
    run = AnalysisRun(
        sample_id=sample_id,
        petri_image_id=petri.id,
        micro_image_id=micro.id,
        model_version_id=uuid4(),
        status=AnalysisStatus.COMPLETED,
    )
    prediction = Prediction(
        analysis_run_id=run.id,
        predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
        feature_summary={"petri": {"area": 1}},
        quality_summary={"petri_is_sharp": True},
    )
    review = HumanReview(
        analysis_run_id=run.id,
        reviewer_name="expert",
        review_decision=decision,
        corrected_label=corrected_label,
    )
    return run, prediction, review, petri, micro


def test_confirmed_review_is_included_with_prediction_label():
    run, prediction, review, petri, micro = _candidate()

    result = DatasetCurationEvaluator().evaluate(
        analysis_run=run,
        prediction=prediction,
        final_review=review,
        petri_image=petri,
        micro_image=micro,
        policy=DatasetCurationPolicy(),
    )

    assert result.curation_status == DatasetCurationStatus.INCLUDED
    assert result.final_label == PredictedLabel.SUSPICIOUS_GROWTH
    assert result.provenance["prediction_is_ground_truth"] is False


def test_corrected_review_uses_corrected_label():
    run, prediction, review, petri, micro = _candidate(
        decision=ReviewDecision.CORRECTED,
        corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
    )

    result = DatasetCurationEvaluator().evaluate(
        analysis_run=run,
        prediction=prediction,
        final_review=review,
        petri_image=petri,
        micro_image=micro,
        policy=DatasetCurationPolicy(),
    )

    assert result.curation_status == DatasetCurationStatus.INCLUDED
    assert result.final_label == PredictedLabel.NO_EVIDENT_GROWTH


def test_missing_final_review_is_excluded():
    run, prediction, _, petri, micro = _candidate()

    result = DatasetCurationEvaluator().evaluate(
        analysis_run=run,
        prediction=prediction,
        final_review=None,
        petri_image=petri,
        micro_image=micro,
        policy=DatasetCurationPolicy(),
    )

    assert result.curation_status == DatasetCurationStatus.EXCLUDED_PENDING_REVIEW
    assert result.final_label is None


def test_rejected_invalid_sample_is_excluded():
    run, prediction, review, petri, micro = _candidate(decision=ReviewDecision.REJECTED_INVALID_SAMPLE)

    result = DatasetCurationEvaluator().evaluate(
        analysis_run=run,
        prediction=prediction,
        final_review=review,
        petri_image=petri,
        micro_image=micro,
        policy=DatasetCurationPolicy(),
    )

    assert result.curation_status == DatasetCurationStatus.EXCLUDED_INVALID_SAMPLE
    assert result.final_label is None

