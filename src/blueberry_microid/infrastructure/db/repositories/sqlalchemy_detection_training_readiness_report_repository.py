from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_readiness_report import (
    DetectionTrainingReadinessReport,
)
from blueberry_microid.infrastructure.db.models.detection_training_readiness_report import (
    DetectionTrainingReadinessReportModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_readiness_report_to_entity


class SqlAlchemyDetectionTrainingReadinessReportRepository(DetectionTrainingReadinessReportRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, report: DetectionTrainingReadinessReport) -> DetectionTrainingReadinessReport:
        model = DetectionTrainingReadinessReportModel(
            id=report.id,
            detection_training_run_id=report.detection_training_run_id,
            annotation_bundle_run_id=report.annotation_bundle_run_id,
            annotation_quality_gate_run_id=report.annotation_quality_gate_run_id,
            dataset_release_id=report.dataset_release_id,
            petri_annotation_export_run_id=report.petri_annotation_export_run_id,
            decision=report.decision.value,
            status=report.status.value,
            is_ready=report.is_ready,
            config=report.config,
            data_summary=report.data_summary,
            split_summary=report.split_summary,
            quality_summary=report.quality_summary,
            environment_summary=report.environment_summary,
            contract_summary=report.contract_summary,
            risk_summary=report.risk_summary,
            recommendation_summary=report.recommendation_summary,
            error_count=report.error_count,
            warning_count=report.warning_count,
            info_count=report.info_count,
            created_at=report.created_at,
            completed_at=report.completed_at,
            created_by=report.created_by,
            notes=report.notes,
            error_message=report.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return detection_training_readiness_report_to_entity(model)

    def get_by_id(self, report_id: UUID) -> Optional[DetectionTrainingReadinessReport]:
        model = self._session.get(DetectionTrainingReadinessReportModel, report_id)
        return detection_training_readiness_report_to_entity(model) if model is not None else None

    def list_all(self) -> list[DetectionTrainingReadinessReport]:
        return self._list(select(DetectionTrainingReadinessReportModel))

    def list_by_detection_training_run_id(
        self, detection_training_run_id: UUID
    ) -> list[DetectionTrainingReadinessReport]:
        return self._list(
            select(DetectionTrainingReadinessReportModel).where(
                DetectionTrainingReadinessReportModel.detection_training_run_id == detection_training_run_id
            )
        )

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingReadinessReport]:
        return self._list(
            select(DetectionTrainingReadinessReportModel).where(
                DetectionTrainingReadinessReportModel.dataset_release_id == dataset_release_id
            )
        )

    def list_by_annotation_bundle_run_id(
        self, annotation_bundle_run_id: UUID
    ) -> list[DetectionTrainingReadinessReport]:
        return self._list(
            select(DetectionTrainingReadinessReportModel).where(
                DetectionTrainingReadinessReportModel.annotation_bundle_run_id == annotation_bundle_run_id
            )
        )

    def list_by_annotation_quality_gate_run_id(
        self, annotation_quality_gate_run_id: UUID
    ) -> list[DetectionTrainingReadinessReport]:
        return self._list(
            select(DetectionTrainingReadinessReportModel).where(
                DetectionTrainingReadinessReportModel.annotation_quality_gate_run_id
                == annotation_quality_gate_run_id
            )
        )

    def _list(self, statement) -> list[DetectionTrainingReadinessReport]:
        statement = statement.order_by(
            DetectionTrainingReadinessReportModel.created_at.asc(),
            DetectionTrainingReadinessReportModel.id.asc(),
        )
        return [
            detection_training_readiness_report_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
