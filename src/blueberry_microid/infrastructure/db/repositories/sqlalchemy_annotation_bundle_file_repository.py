from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.infrastructure.db.models.annotation_bundle_file import AnnotationBundleFileModel
from blueberry_microid.infrastructure.db.repositories.mappers import annotation_bundle_file_to_entity


class SqlAlchemyAnnotationBundleFileRepository(AnnotationBundleFileRepositoryPort):
    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add_many(self, files: list[AnnotationBundleFile]) -> list[AnnotationBundleFile]:
        self._session.add_all(
            [
                AnnotationBundleFileModel(
                    id=file.id,
                    bundle_run_id=file.bundle_run_id,
                    file_role=file.file_role.value,
                    file_path=file.file_path,
                    relative_path=file.relative_path,
                    content_type=file.content_type,
                    size_bytes=file.size_bytes,
                    checksum_sha256=file.checksum_sha256,
                    created_at=file.created_at,
                )
                for file in files
            ]
        )
        self._commit_or_flush()
        return files

    def list_by_bundle_run_id(self, bundle_run_id: UUID) -> list[AnnotationBundleFile]:
        statement = (
            select(AnnotationBundleFileModel)
            .where(AnnotationBundleFileModel.bundle_run_id == bundle_run_id)
            .order_by(AnnotationBundleFileModel.relative_path.asc(), AnnotationBundleFileModel.id.asc())
        )
        return [annotation_bundle_file_to_entity(model) for model in self._session.execute(statement).scalars()]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
