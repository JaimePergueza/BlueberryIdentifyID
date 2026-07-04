from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.detection_training_artifact_record_repository import (
    DetectionTrainingArtifactRecordRepositoryPort,
)
from blueberry_microid.domain.entities.detection_training_artifact_record import DetectionTrainingArtifactRecord
from blueberry_microid.infrastructure.db.models.detection_training_artifact_record import (
    DetectionTrainingArtifactRecordModel,
)
from blueberry_microid.infrastructure.db.repositories.mappers import detection_training_artifact_record_to_entity


class SqlAlchemyDetectionTrainingArtifactRecordRepository(DetectionTrainingArtifactRecordRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(
        self, records: list[DetectionTrainingArtifactRecord]
    ) -> list[DetectionTrainingArtifactRecord]:
        models = [
            DetectionTrainingArtifactRecordModel(
                id=record.id,
                artifact_policy_id=record.artifact_policy_id,
                detection_training_run_id=record.detection_training_run_id,
                artifact_kind=record.artifact_kind.value,
                artifact_state=record.artifact_state.value,
                location_type=record.location_type.value,
                artifact_path=record.artifact_path,
                relative_path=record.relative_path,
                external_uri=record.external_uri,
                file_extension=record.file_extension,
                size_bytes=record.size_bytes,
                checksum_sha256=record.checksum_sha256,
                artifact_metadata=record.metadata,
                created_at=record.created_at,
            )
            for record in records
        ]
        self._session.add_all(models)
        self._commit_or_flush()
        for model in models:
            self._session.refresh(model)
        return [detection_training_artifact_record_to_entity(model) for model in models]

    def list_by_artifact_policy_id(self, artifact_policy_id: UUID) -> list[DetectionTrainingArtifactRecord]:
        statement = (
            select(DetectionTrainingArtifactRecordModel)
            .where(DetectionTrainingArtifactRecordModel.artifact_policy_id == artifact_policy_id)
            .order_by(
                DetectionTrainingArtifactRecordModel.artifact_kind.asc(),
                DetectionTrainingArtifactRecordModel.created_at.asc(),
                DetectionTrainingArtifactRecordModel.id.asc(),
            )
        )
        return [
            detection_training_artifact_record_to_entity(model)
            for model in self._session.execute(statement).scalars()
        ]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
