"""PostgreSQL-only coverage for the joined AnalysisRun history query adapter."""

from uuid import uuid4

import pytest

from blueberry_microid.application.dto.analysis_history_dto import AnalysisHistoryFilters
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
from blueberry_microid.infrastructure.db.models.model_version import ModelVersionModel
from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
from blueberry_microid.infrastructure.db.models.sample import SampleModel
from blueberry_microid.infrastructure.db.queries.sqlalchemy_analysis_history_query import (
    SqlAlchemyAnalysisHistoryQuery,
)

pytestmark = pytest.mark.postgres


def _create_run(pg_session, sample_code: str, *, with_prediction: bool = True) -> AnalysisRunModel:
    sample = SampleModel(id=uuid4(), sample_code=sample_code)
    model_version = ModelVersionModel(
        id=uuid4(), name=f"history-model-{sample_code}", version="1.0.0", model_type=ModelType.CLASSICAL
    )
    petri = PetriImageModel(
        id=uuid4(), sample_id=sample.id, file_path="internal/petri.jpg", file_name="petri.jpg",
        mime_type="image/jpeg", file_size_bytes=10,
    )
    micro = MicroImageModel(
        id=uuid4(), sample_id=sample.id, file_path="internal/micro.jpg", file_name="micro.jpg",
        mime_type="image/jpeg", file_size_bytes=10,
    )
    run = AnalysisRunModel(
        id=uuid4(), sample_id=sample.id, petri_image_id=petri.id, micro_image_id=micro.id,
        model_version_id=model_version.id, status=AnalysisStatus.NEEDS_REVIEW,
    )
    pg_session.add_all([sample, model_version, petri, micro, run])
    if with_prediction:
        pg_session.add(
            PredictionModel(
                id=uuid4(), analysis_run_id=run.id,
                predicted_label=PredictedLabel.SUSPICIOUS_GROWTH,
                confidence_score=0.7, requires_human_review=True,
            )
        )
    pg_session.commit()
    return run


def _add_review(
    pg_session,
    run: AnalysisRunModel,
    decision: ReviewDecision,
    *,
    is_final: bool,
    corrected_label: PredictedLabel | None = None,
) -> HumanReviewModel:
    review = HumanReviewModel(
        id=uuid4(), analysis_run_id=run.id, reviewer_name="Dr. Postgres",
        review_decision=decision, corrected_label=corrected_label, is_final=is_final,
    )
    pg_session.add(review)
    pg_session.commit()
    return review


def test_outer_joins_keep_run_without_prediction_or_review(pg_session):
    run = _create_run(pg_session, "PG-NO-PREDICTION", with_prediction=False)

    detail = SqlAlchemyAnalysisHistoryQuery(pg_session).get_detail(run.id)

    assert detail is not None
    assert detail.prediction is None
    assert detail.human_review is None
    assert detail.final_status == "pending_human_review"


def test_outer_join_keeps_run_without_human_review(pg_session):
    run = _create_run(pg_session, "PG-NO-REVIEW")

    item = SqlAlchemyAnalysisHistoryQuery(pg_session).list_page(AnalysisHistoryFilters()).items[0]

    assert item.analysis_run_id == run.id
    assert item.review_status == "pending"
    assert item.final_label is None


def test_query_selects_only_current_final_human_review(pg_session):
    run = _create_run(pg_session, "PG-FINAL-ONLY")
    _add_review(
        pg_session, run, ReviewDecision.CORRECTED, is_final=False,
        corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
    )
    final = _add_review(pg_session, run, ReviewDecision.CONFIRMED, is_final=True)

    item = SqlAlchemyAnalysisHistoryQuery(pg_session).list_page(AnalysisHistoryFilters()).items[0]

    assert item.final_review_id == final.id
    assert item.review_decision == ReviewDecision.CONFIRMED
    assert item.final_label == PredictedLabel.SUSPICIOUS_GROWTH


def test_enum_filters_apply_to_history_query(pg_session):
    run = _create_run(pg_session, "PG-ENUM")

    page = SqlAlchemyAnalysisHistoryQuery(pg_session).list_page(
        AnalysisHistoryFilters(
            status=AnalysisStatus.NEEDS_REVIEW,
            preliminary_label=PredictedLabel.SUSPICIOUS_GROWTH,
        )
    )

    assert [item.analysis_run_id for item in page.items] == [run.id]


@pytest.mark.parametrize(
    ("decision", "corrected_label", "expected_label", "expected_status"),
    [
        (ReviewDecision.CONFIRMED, None, PredictedLabel.SUSPICIOUS_GROWTH, "human_confirmed"),
        (ReviewDecision.CORRECTED, PredictedLabel.NO_EVIDENT_GROWTH, PredictedLabel.NO_EVIDENT_GROWTH, "human_corrected"),
        (ReviewDecision.MARKED_INCONCLUSIVE, None, PredictedLabel.INCONCLUSIVE, "inconclusive"),
    ],
)
def test_derived_final_label_filter_matches_resolver(
    pg_session, decision, corrected_label, expected_label, expected_status
):
    run = _create_run(pg_session, f"PG-FINAL-{decision.value}")
    _add_review(pg_session, run, decision, is_final=True, corrected_label=corrected_label)

    page = SqlAlchemyAnalysisHistoryQuery(pg_session).list_page(
        AnalysisHistoryFilters(final_label=expected_label)
    )

    assert [item.analysis_run_id for item in page.items] == [run.id]
    assert page.items[0].final_label == expected_label
    assert page.items[0].final_status == expected_status


def test_total_count_does_not_duplicate_run_for_historical_reviews(pg_session):
    run = _create_run(pg_session, "PG-NO-DUPLICATES")
    _add_review(
        pg_session, run, ReviewDecision.CORRECTED, is_final=False,
        corrected_label=PredictedLabel.NO_EVIDENT_GROWTH,
    )
    _add_review(pg_session, run, ReviewDecision.MARKED_INCONCLUSIVE, is_final=False)
    _add_review(pg_session, run, ReviewDecision.CONFIRMED, is_final=True)

    page = SqlAlchemyAnalysisHistoryQuery(pg_session).list_page(AnalysisHistoryFilters())

    assert page.total == 1
    assert len(page.items) == 1
