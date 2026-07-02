from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from blueberry_microid.application.exceptions import AnalysisRunNotFoundError
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
from blueberry_microid.infrastructure.db.repositories.mappers import analysis_run_to_entity


class SqlAlchemyAnalysisRunRepository(AnalysisRunRepositoryPort):
    """SQLAlchemy-backed AnalysisRunRepositoryPort.

    `auto_commit=False` is used only when this repository is constructed
    inside a `UnitOfWorkPort` transaction (see
    `infrastructure/db/session/sqlalchemy_unit_of_work.py`), so its writes
    become part of a larger atomic commit instead of being persisted on
    their own. Every other caller keeps the default (`True`), matching the
    "each repository commits its own write" convention used everywhere else
    in this codebase.
    """

    def __init__(self, session: Session, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    def add(self, analysis_run: AnalysisRun) -> AnalysisRun:
        model = AnalysisRunModel(
            id=analysis_run.id,
            sample_id=analysis_run.sample_id,
            petri_image_id=analysis_run.petri_image_id,
            micro_image_id=analysis_run.micro_image_id,
            model_version_id=analysis_run.model_version_id,
            status=analysis_run.status,
            created_at=analysis_run.created_at,
            started_at=analysis_run.started_at,
            completed_at=analysis_run.completed_at,
            error_message=analysis_run.error_message,
        )
        self._session.add(model)
        self._commit_or_flush()
        self._session.refresh(model)
        return analysis_run_to_entity(model)

    def update(self, analysis_run: AnalysisRun) -> AnalysisRun:
        model = self._session.get(AnalysisRunModel, analysis_run.id)
        if model is None:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run.id}' does not exist")
        model.status = analysis_run.status
        model.started_at = analysis_run.started_at
        model.completed_at = analysis_run.completed_at
        model.error_message = analysis_run.error_message
        self._commit_or_flush()
        self._session.refresh(model)
        return analysis_run_to_entity(model)

    def claim_for_processing(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        statement = (
            update(AnalysisRunModel)
            .where(AnalysisRunModel.id == analysis_run_id, AnalysisRunModel.status == AnalysisStatus.PENDING)
            .values(status=AnalysisStatus.PROCESSING, started_at=func.now())
        )
        result = self._session.execute(statement)
        self._commit_or_flush()

        if result.rowcount == 0:
            return None

        # This was a Core-level bulk UPDATE, which bypasses the ORM's
        # identity map: if `analysis_run_id` was already loaded earlier in
        # this session (e.g. by a get_by_id() existence check just before
        # this call), that cached instance still shows the pre-claim values.
        # Expiring forces the re-fetch below to hit the database.
        self._session.expire_all()
        model = self._session.get(AnalysisRunModel, analysis_run_id)
        return analysis_run_to_entity(model)

    def get_by_id(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        model = self._session.get(AnalysisRunModel, analysis_run_id)
        return analysis_run_to_entity(model) if model is not None else None

    def list_by_sample_id(self, sample_id: UUID) -> list[AnalysisRun]:
        statement = select(AnalysisRunModel).where(AnalysisRunModel.sample_id == sample_id)
        models = self._session.execute(statement).scalars().all()
        return [analysis_run_to_entity(model) for model in models]

    def list_all(self) -> list[AnalysisRun]:
        statement = select(AnalysisRunModel).order_by(AnalysisRunModel.created_at.asc(), AnalysisRunModel.id.asc())
        models = self._session.execute(statement).scalars().all()
        return [analysis_run_to_entity(model) for model in models]

    def _commit_or_flush(self) -> None:
        if self._auto_commit:
            self._session.commit()
        else:
            self._session.flush()
