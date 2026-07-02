from uuid import uuid4

from blueberry_microid.application.dto.dataset_dto import CreateDatasetSnapshotRequest
from blueberry_microid.application.services.dataset_manifest_exporter import DatasetManifestExporter
from blueberry_microid.application.use_cases.dataset.create_dataset_snapshot import CreateDatasetSnapshotUseCase
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetItemRepository,
    InMemoryDatasetSnapshotRepository,
    InMemoryHumanReviewRepository,
    InMemoryMicroImageRepository,
    InMemoryPetriImageRepository,
    InMemoryPredictionRepository,
    InMemorySampleRepository,
)


def _make_context():
    sample_repo = InMemorySampleRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    analysis_repo = InMemoryAnalysisRunRepository()
    prediction_repo = InMemoryPredictionRepository()
    review_repo = InMemoryHumanReviewRepository()
    snapshot_repo = InMemoryDatasetSnapshotRepository()
    item_repo = InMemoryDatasetItemRepository()
    uow = FakeUnitOfWork(
        analysis_repo,
        prediction_repo,
        review_repo,
        dataset_snapshot_repository=snapshot_repo,
        dataset_item_repository=item_repo,
    )
    use_case = CreateDatasetSnapshotUseCase(
        analysis_repo,
        prediction_repo,
        review_repo,
        petri_repo,
        micro_repo,
        uow,
    )
    return {
        "sample_repo": sample_repo,
        "petri_repo": petri_repo,
        "micro_repo": micro_repo,
        "analysis_repo": analysis_repo,
        "prediction_repo": prediction_repo,
        "review_repo": review_repo,
        "snapshot_repo": snapshot_repo,
        "item_repo": item_repo,
        "use_case": use_case,
    }


def _add_reviewed_run(
    ctx,
    *,
    sample_code: str = "BB-001",
    run_status: AnalysisStatus = AnalysisStatus.COMPLETED,
    prediction_label: PredictedLabel = PredictedLabel.SUSPICIOUS_GROWTH,
    review_decision: ReviewDecision | None = ReviewDecision.CONFIRMED,
    corrected_label: PredictedLabel | None = None,
):
    sample = Sample(sample_code=sample_code)
    ctx["sample_repo"].add(sample)
    petri = PetriImage(
        sample_id=sample.id,
        file_path=f"petri/{sample_code}.jpg",
        file_name=f"{sample_code}-petri.jpg",
        mime_type="image/jpeg",
        file_size_bytes=12,
        width=100,
        height=80,
        culture_medium="PDA",
    )
    micro = MicroImage(
        sample_id=sample.id,
        file_path=f"micro/{sample_code}.png",
        file_name=f"{sample_code}-micro.png",
        mime_type="image/png",
        file_size_bytes=10,
        width=50,
        height=40,
        magnification="400x",
    )
    ctx["petri_repo"].add(petri)
    ctx["micro_repo"].add(micro)
    run = AnalysisRun(
        sample_id=sample.id,
        petri_image_id=petri.id,
        micro_image_id=micro.id,
        model_version_id=uuid4(),
        status=run_status,
    )
    ctx["analysis_repo"].add(run)
    prediction = Prediction(analysis_run_id=run.id, predicted_label=prediction_label, confidence_score=0.42)
    ctx["prediction_repo"].add(prediction)
    review = None
    if review_decision is not None:
        review = HumanReview(
            analysis_run_id=run.id,
            reviewer_name="expert",
            review_decision=review_decision,
            corrected_label=corrected_label,
            is_final=True,
        )
        ctx["review_repo"].add(review)
    return sample, petri, micro, run, prediction, review


def _create_snapshot(ctx, **kwargs):
    return ctx["use_case"].execute(CreateDatasetSnapshotRequest(name="curated", version=str(uuid4()), **kwargs))


def test_analysis_run_without_final_human_review_is_excluded():
    ctx = _make_context()
    _add_reviewed_run(ctx, review_decision=None)

    snapshot = _create_snapshot(ctx)

    assert snapshot.item_count == 0
    assert ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id) == []


def test_confirmed_review_uses_prediction_label_as_ground_truth():
    ctx = _make_context()
    _add_reviewed_run(ctx, prediction_label=PredictedLabel.PROBABLE_FUNGAL_GROWTH)

    snapshot = _create_snapshot(ctx)
    item = ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id)[0]

    assert item.ground_truth_label == PredictedLabel.PROBABLE_FUNGAL_GROWTH
    assert item.source_review_decision == ReviewDecision.CONFIRMED


def test_corrected_review_uses_corrected_label_as_ground_truth():
    ctx = _make_context()
    _add_reviewed_run(
        ctx,
        prediction_label=PredictedLabel.SUSPICIOUS_GROWTH,
        review_decision=ReviewDecision.CORRECTED,
        corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
    )

    snapshot = _create_snapshot(ctx)
    item = ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id)[0]

    assert item.ground_truth_label == PredictedLabel.NO_EVIDENT_GROWTH


def test_marked_inconclusive_is_excluded_by_default():
    ctx = _make_context()
    _add_reviewed_run(ctx, review_decision=ReviewDecision.MARKED_INCONCLUSIVE)

    snapshot = _create_snapshot(ctx)

    assert snapshot.item_count == 0
    assert ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id) == []


def test_marked_inconclusive_is_included_when_requested():
    ctx = _make_context()
    _add_reviewed_run(ctx, review_decision=ReviewDecision.MARKED_INCONCLUSIVE)

    snapshot = _create_snapshot(ctx, include_inconclusive=True)
    item = ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id)[0]

    assert snapshot.item_count == 1
    assert item.ground_truth_label == PredictedLabel.INCONCLUSIVE


def test_rejected_invalid_sample_is_excluded_by_default():
    ctx = _make_context()
    _add_reviewed_run(ctx, review_decision=ReviewDecision.REJECTED_INVALID_SAMPLE)

    snapshot = _create_snapshot(ctx)

    assert snapshot.item_count == 0
    assert ctx["item_repo"].list_by_dataset_snapshot_id(snapshot.id) == []


def test_prediction_and_human_review_are_not_modified():
    ctx = _make_context()
    _, _, _, run, prediction, review = _add_reviewed_run(ctx)
    original_prediction_label = prediction.predicted_label
    original_review_decision = review.review_decision

    _create_snapshot(ctx)

    assert ctx["prediction_repo"].get_by_analysis_run_id(run.id).predicted_label == original_prediction_label
    assert ctx["review_repo"].get_final_by_analysis_run_id(run.id).review_decision == original_review_decision


def test_dataset_snapshot_calculates_item_count_and_label_distribution():
    ctx = _make_context()
    _add_reviewed_run(ctx, sample_code="BB-001", prediction_label=PredictedLabel.SUSPICIOUS_GROWTH)
    _add_reviewed_run(ctx, sample_code="BB-002", prediction_label=PredictedLabel.SUSPICIOUS_GROWTH)
    _add_reviewed_run(ctx, sample_code="BB-003", prediction_label=PredictedLabel.NO_EVIDENT_GROWTH)

    snapshot = _create_snapshot(ctx)

    assert snapshot.item_count == 3
    assert snapshot.label_distribution == {
        "no_evident_growth": 1,
        "suspicious_growth": 2,
    }


def test_manifest_contains_no_binaries_no_secrets_and_is_deterministic():
    ctx = _make_context()
    _add_reviewed_run(ctx, sample_code="BB-002", prediction_label=PredictedLabel.SUSPICIOUS_GROWTH)
    _add_reviewed_run(ctx, sample_code="BB-001", prediction_label=PredictedLabel.NO_EVIDENT_GROWTH)
    snapshot = _create_snapshot(ctx)
    exporter = DatasetManifestExporter(
        ctx["snapshot_repo"],
        ctx["item_repo"],
        ctx["sample_repo"],
        ctx["petri_repo"],
        ctx["micro_repo"],
        ctx["prediction_repo"],
    )

    manifest_a = exporter.export(snapshot.id)
    manifest_b = exporter.export(snapshot.id)

    assert manifest_a == manifest_b
    assert [item["analysis_run_id"] for item in manifest_a["items"]] == sorted(
        item["analysis_run_id"] for item in manifest_a["items"]
    )
    assert "binary" not in str(manifest_a).lower()
    assert "secret" not in str(manifest_a).lower()
    assert "species" not in str(manifest_a).lower()
    assert "genus" not in str(manifest_a).lower()

