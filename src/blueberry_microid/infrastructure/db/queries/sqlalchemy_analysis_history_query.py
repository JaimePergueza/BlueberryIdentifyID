"""SQLAlchemy implementation of the AnalysisRun history read port.

The adapter deliberately projects only the fields required by the API.  It
does not hydrate ORM relationship graphs, so list/detail reads are each a
single joined query (plus a separate stable count query for pagination).
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, case, func, literal, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, aliased

from blueberry_microid.application.dto.analysis_history_dto import (
    AnalysisHistoryFilters,
    AnalysisHistoryItemDTO,
    AnalysisHistoryPageDTO,
    AnalysisRunDetailDTO,
    AnalysisRunDetailSummaryDTO,
    HumanReviewDetailDTO,
    MicroImageDetailDTO,
    ModelVersionDetailDTO,
    PetriImageDetailDTO,
    PredictionDetailDTO,
    SampleDetailDTO,
)
from blueberry_microid.application.ports.analysis_history_query import AnalysisHistoryQueryPort
from blueberry_microid.application.services.final_analysis_resolver import (
    FINAL_STATUS_PENDING,
    FinalLabelResolution,
    resolve_final_label,
)
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
from blueberry_microid.infrastructure.db.models.model_version import ModelVersionModel
from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
from blueberry_microid.infrastructure.db.models.sample import SampleModel
from blueberry_microid.infrastructure.db.models.enums import predicted_label_enum


class SqlAlchemyAnalysisHistoryQuery(AnalysisHistoryQueryPort):
    """Read model backed by one joined SQLAlchemy query per result shape."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_page(self, filters: AnalysisHistoryFilters) -> AnalysisHistoryPageDTO:
        final_review = aliased(HumanReviewModel, name="final_review")
        final_label = self._final_label_expression(final_review)

        count_statement = self._apply_filters(
            self._base_select(final_review, func.count(func.distinct(AnalysisRunModel.id))),
            filters,
            final_review,
            final_label,
        )
        total = int(self._session.scalar(count_statement) or 0)

        statement = self._base_select(
            final_review,
            AnalysisRunModel.id.label("analysis_run_id"),
            AnalysisRunModel.sample_id.label("sample_id"),
            SampleModel.sample_code.label("sample_code"),
            AnalysisRunModel.petri_image_id.label("petri_image_id"),
            AnalysisRunModel.micro_image_id.label("micro_image_id"),
            AnalysisRunModel.model_version_id.label("model_version_id"),
            ModelVersionModel.name.label("model_name"),
            ModelVersionModel.version.label("model_version"),
            ModelVersionModel.model_type.label("model_type"),
            AnalysisRunModel.status.label("analysis_status"),
            AnalysisRunModel.created_at.label("analysis_created_at"),
            AnalysisRunModel.completed_at.label("analysis_completed_at"),
            PredictionModel.id.label("prediction_id"),
            PredictionModel.predicted_label.label("preliminary_label"),
            PredictionModel.confidence_score.label("confidence_score"),
            final_review.id.label("final_review_id"),
            final_review.reviewer_name.label("final_reviewer_name"),
            final_review.review_decision.label("final_review_decision"),
            final_review.corrected_label.label("final_corrected_label"),
            final_review.comments.label("final_review_comments"),
            final_review.is_final.label("final_review_is_final"),
            final_review.created_at.label("final_review_created_at"),
        )
        statement = self._apply_filters(statement, filters, final_review, final_label)
        statement = statement.order_by(AnalysisRunModel.created_at.desc(), AnalysisRunModel.id.desc())
        statement = statement.limit(filters.page_size).offset((filters.page - 1) * filters.page_size)
        rows = self._session.execute(statement).mappings().all()

        return AnalysisHistoryPageDTO.create(
            items=tuple(self._history_item_from_row(row) for row in rows),
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    def get_detail(self, analysis_run_id: UUID) -> Optional[AnalysisRunDetailDTO]:
        final_review = aliased(HumanReviewModel, name="final_review")
        statement = self._base_select(
            final_review,
            AnalysisRunModel.id.label("analysis_run_id"),
            AnalysisRunModel.status.label("analysis_status"),
            AnalysisRunModel.created_at.label("analysis_created_at"),
            AnalysisRunModel.started_at.label("analysis_started_at"),
            AnalysisRunModel.completed_at.label("analysis_completed_at"),
            AnalysisRunModel.error_message.label("analysis_error_message"),
            SampleModel.id.label("sample_id"),
            SampleModel.sample_code.label("sample_code"),
            SampleModel.product.label("sample_product"),
            SampleModel.lot_code.label("sample_lot_code"),
            SampleModel.origin.label("sample_origin"),
            SampleModel.collection_date.label("sample_collection_date"),
            SampleModel.notes.label("sample_notes"),
            SampleModel.created_at.label("sample_created_at"),
            PetriImageModel.id.label("petri_image_id"),
            PetriImageModel.file_name.label("petri_file_name"),
            PetriImageModel.mime_type.label("petri_mime_type"),
            PetriImageModel.file_size_bytes.label("petri_file_size_bytes"),
            PetriImageModel.width.label("petri_width"),
            PetriImageModel.height.label("petri_height"),
            PetriImageModel.captured_at.label("petri_captured_at"),
            PetriImageModel.culture_medium.label("petri_culture_medium"),
            PetriImageModel.incubation_temperature_c.label("petri_incubation_temperature_c"),
            PetriImageModel.incubation_time_hours.label("petri_incubation_time_hours"),
            PetriImageModel.seeding_date.label("petri_seeding_date"),
            PetriImageModel.observed_colony_color.label("petri_observed_colony_color"),
            PetriImageModel.observed_colony_shape.label("petri_observed_colony_shape"),
            PetriImageModel.observed_colony_margin.label("petri_observed_colony_margin"),
            PetriImageModel.observed_colony_texture.label("petri_observed_colony_texture"),
            PetriImageModel.notes.label("petri_notes"),
            MicroImageModel.id.label("micro_image_id"),
            MicroImageModel.file_name.label("micro_file_name"),
            MicroImageModel.mime_type.label("micro_mime_type"),
            MicroImageModel.file_size_bytes.label("micro_file_size_bytes"),
            MicroImageModel.width.label("micro_width"),
            MicroImageModel.height.label("micro_height"),
            MicroImageModel.captured_at.label("micro_captured_at"),
            MicroImageModel.magnification.label("micro_magnification"),
            MicroImageModel.microscope_type.label("micro_microscope_type"),
            MicroImageModel.staining_method.label("micro_staining_method"),
            MicroImageModel.preparation_method.label("micro_preparation_method"),
            MicroImageModel.observed_structures.label("micro_observed_structures"),
            MicroImageModel.notes.label("micro_notes"),
            ModelVersionModel.id.label("model_version_id"),
            ModelVersionModel.name.label("model_name"),
            ModelVersionModel.version.label("model_version"),
            ModelVersionModel.model_type.label("model_type"),
            ModelVersionModel.description.label("model_description"),
            PredictionModel.id.label("prediction_id"),
            PredictionModel.predicted_label.label("preliminary_label"),
            PredictionModel.confidence_score.label("confidence_score"),
            PredictionModel.class_probabilities.label("class_probabilities"),
            PredictionModel.technical_observation.label("technical_observation"),
            PredictionModel.requires_human_review.label("prediction_requires_human_review"),
            PredictionModel.explanation.label("explanation"),
            PredictionModel.feature_summary.label("feature_summary"),
            PredictionModel.quality_summary.label("quality_summary"),
            PredictionModel.decision_trace.label("decision_trace"),
            PredictionModel.warnings.label("prediction_warnings"),
            PredictionModel.created_at.label("prediction_created_at"),
            final_review.id.label("final_review_id"),
            final_review.reviewer_name.label("final_reviewer_name"),
            final_review.review_decision.label("final_review_decision"),
            final_review.corrected_label.label("final_corrected_label"),
            final_review.comments.label("final_review_comments"),
            final_review.is_final.label("final_review_is_final"),
            final_review.created_at.label("final_review_created_at"),
        ).where(AnalysisRunModel.id == analysis_run_id)
        row = self._session.execute(statement).mappings().one_or_none()
        return self._detail_from_row(row) if row is not None else None

    @staticmethod
    def _base_select(final_review, *columns):
        return (
            select(*columns)
            .select_from(AnalysisRunModel)
            .join(SampleModel, SampleModel.id == AnalysisRunModel.sample_id)
            .join(PetriImageModel, PetriImageModel.id == AnalysisRunModel.petri_image_id)
            .join(MicroImageModel, MicroImageModel.id == AnalysisRunModel.micro_image_id)
            .join(ModelVersionModel, ModelVersionModel.id == AnalysisRunModel.model_version_id)
            .outerjoin(PredictionModel, PredictionModel.analysis_run_id == AnalysisRunModel.id)
            .outerjoin(
                final_review,
                and_(
                    final_review.analysis_run_id == AnalysisRunModel.id,
                    final_review.is_final.is_(True),
                ),
            )
        )

    @staticmethod
    def _final_label_expression(final_review):
        """SQL equivalent used exclusively to filter by the resolved label.

        DTO mapping below still delegates result resolution to
        ``resolve_final_label``.  Tests cover this CASE expression against the
        pure resolver for every review decision.
        """
        return case(
            (final_review.id.is_(None), None),
            (
                final_review.review_decision == ReviewDecision.CONFIRMED,
                PredictionModel.predicted_label,
            ),
            (
                final_review.review_decision == ReviewDecision.CORRECTED,
                final_review.corrected_label,
            ),
            (
                final_review.review_decision == ReviewDecision.MARKED_INCONCLUSIVE,
                literal(PredictedLabel.INCONCLUSIVE, type_=predicted_label_enum),
            ),
            else_=None,
        )

    @staticmethod
    def _apply_filters(statement, filters, final_review, final_label):
        if filters.sample_code is not None:
            sample_code = f"%{filters.sample_code.lower()}%"
            statement = statement.where(func.lower(SampleModel.sample_code).like(sample_code))
        if filters.status is not None:
            statement = statement.where(AnalysisRunModel.status == filters.status)
        if filters.review_status == "pending":
            statement = statement.where(final_review.id.is_(None))
        elif filters.review_status == "reviewed":
            statement = statement.where(final_review.id.is_not(None))
        if filters.preliminary_label is not None:
            statement = statement.where(PredictionModel.predicted_label == filters.preliminary_label)
        if filters.final_label is not None:
            statement = statement.where(final_label == filters.final_label)
        if filters.created_from is not None:
            statement = statement.where(AnalysisRunModel.created_at >= filters.created_from)
        if filters.created_to is not None:
            statement = statement.where(AnalysisRunModel.created_at <= filters.created_to)
        return statement

    @staticmethod
    def _prediction_from_row(row: RowMapping) -> Optional[Prediction]:
        prediction_id = row["prediction_id"]
        if prediction_id is None:
            return None
        return Prediction(
            id=prediction_id,
            analysis_run_id=row["analysis_run_id"],
            predicted_label=row["preliminary_label"],
            confidence_score=row.get("confidence_score"),
            requires_human_review=bool(row.get("prediction_requires_human_review", False)),
            created_at=row.get("prediction_created_at") or row["analysis_created_at"],
        )

    @staticmethod
    def _review_from_row(row: RowMapping) -> Optional[HumanReview]:
        review_id = row["final_review_id"]
        if review_id is None:
            return None
        return HumanReview(
            id=review_id,
            analysis_run_id=row["analysis_run_id"],
            reviewer_name=row["final_reviewer_name"],
            review_decision=row["final_review_decision"],
            corrected_label=row["final_corrected_label"],
            comments=row["final_review_comments"],
            is_final=bool(row["final_review_is_final"]),
            created_at=row["final_review_created_at"],
        )

    def _resolution_from_row(self, row: RowMapping) -> FinalLabelResolution:
        prediction = self._prediction_from_row(row)
        if prediction is None:
            # An unprocessed run has no preliminary output to confirm or
            # correct.  Keeping it visible is the reason this read model uses
            # an outer join; its final state is the same pending state that the
            # resolver assigns before any final review exists.
            return FinalLabelResolution(
                final_label=None,
                status=FINAL_STATUS_PENDING,
                human_review_completed=False,
            )
        return resolve_final_label(prediction, self._review_from_row(row))

    def _history_item_from_row(self, row: RowMapping) -> AnalysisHistoryItemDTO:
        resolution = self._resolution_from_row(row)
        review = self._review_from_row(row)
        return AnalysisHistoryItemDTO(
            analysis_run_id=row["analysis_run_id"],
            sample_id=row["sample_id"],
            sample_code=row["sample_code"],
            petri_image_id=row["petri_image_id"],
            micro_image_id=row["micro_image_id"],
            model_version_id=row["model_version_id"],
            model_name=row["model_name"],
            model_version=row["model_version"],
            model_type=row["model_type"],
            analysis_status=row["analysis_status"],
            created_at=row["analysis_created_at"],
            completed_at=row["analysis_completed_at"],
            preliminary_label=row["preliminary_label"],
            confidence_score=row["confidence_score"],
            requires_human_review=not resolution.human_review_completed,
            review_status="reviewed" if review is not None else "pending",
            final_review_id=row["final_review_id"],
            review_decision=row["final_review_decision"],
            reviewer_name=row["final_reviewer_name"],
            reviewed_at=row["final_review_created_at"],
            final_label=resolution.final_label,
            final_status=resolution.status,
        )

    def _detail_from_row(self, row: RowMapping) -> AnalysisRunDetailDTO:
        prediction = self._prediction_from_row(row)
        review = self._review_from_row(row)
        resolution = self._resolution_from_row(row)

        return AnalysisRunDetailDTO(
            analysis_run=AnalysisRunDetailSummaryDTO(
                id=row["analysis_run_id"],
                status=row["analysis_status"],
                created_at=row["analysis_created_at"],
                started_at=row["analysis_started_at"],
                completed_at=row["analysis_completed_at"],
                error_message=row["analysis_error_message"],
            ),
            sample=SampleDetailDTO(
                id=row["sample_id"],
                sample_code=row["sample_code"],
                product=row["sample_product"],
                lot_code=row["sample_lot_code"],
                origin=row["sample_origin"],
                collection_date=row["sample_collection_date"],
                notes=row["sample_notes"],
                created_at=row["sample_created_at"],
            ),
            petri_image=PetriImageDetailDTO(
                id=row["petri_image_id"],
                file_name=row["petri_file_name"],
                mime_type=row["petri_mime_type"],
                file_size_bytes=row["petri_file_size_bytes"],
                width=row["petri_width"],
                height=row["petri_height"],
                captured_at=row["petri_captured_at"],
                culture_medium=row["petri_culture_medium"],
                incubation_temperature_c=row["petri_incubation_temperature_c"],
                incubation_time_hours=row["petri_incubation_time_hours"],
                seeding_date=row["petri_seeding_date"],
                observed_colony_color=row["petri_observed_colony_color"],
                observed_colony_shape=row["petri_observed_colony_shape"],
                observed_colony_margin=row["petri_observed_colony_margin"],
                observed_colony_texture=row["petri_observed_colony_texture"],
                notes=row["petri_notes"],
            ),
            micro_image=MicroImageDetailDTO(
                id=row["micro_image_id"],
                file_name=row["micro_file_name"],
                mime_type=row["micro_mime_type"],
                file_size_bytes=row["micro_file_size_bytes"],
                width=row["micro_width"],
                height=row["micro_height"],
                captured_at=row["micro_captured_at"],
                magnification=row["micro_magnification"],
                microscope_type=row["micro_microscope_type"],
                staining_method=row["micro_staining_method"],
                preparation_method=row["micro_preparation_method"],
                observed_structures=row["micro_observed_structures"],
                notes=row["micro_notes"],
            ),
            model_version=ModelVersionDetailDTO(
                id=row["model_version_id"],
                name=row["model_name"],
                version=row["model_version"],
                model_type=row["model_type"],
                description=row["model_description"],
            ),
            prediction=(
                PredictionDetailDTO(
                    id=prediction.id,
                    predicted_label=prediction.predicted_label,
                    confidence_score=row["confidence_score"],
                    class_probabilities=row["class_probabilities"],
                    technical_observation=row["technical_observation"],
                    requires_human_review=prediction.requires_human_review,
                    explanation=row["explanation"],
                    feature_summary=row["feature_summary"],
                    quality_summary=row["quality_summary"],
                    decision_trace=row["decision_trace"],
                    warnings=row["prediction_warnings"],
                    created_at=prediction.created_at,
                )
                if prediction is not None
                else None
            ),
            human_review=(
                HumanReviewDetailDTO(
                    id=review.id,
                    reviewer_name=review.reviewer_name,
                    review_decision=review.review_decision,
                    corrected_label=review.corrected_label,
                    comments=review.comments,
                    is_final=review.is_final,
                    created_at=review.created_at,
                )
                if review is not None
                else None
            ),
            final_label=resolution.final_label,
            final_status=resolution.status,
            human_review_completed=resolution.human_review_completed,
            requires_human_review=not resolution.human_review_completed,
        )
