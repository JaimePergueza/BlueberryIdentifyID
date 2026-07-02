from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional

from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort


class UnitOfWorkPort(ABC):
    """Application-level transaction boundary, independent of SQLAlchemy.

    First real consumer: `ProcessAnalysisRunUseCase` (Fase 4), which must
    create a `Prediction` and move its `AnalysisRun` to a final status
    (`completed`/`needs_review`) as a single atomic write — if either half
    fails, neither should persist. `analysis_run_repository` and
    `prediction_repository` are only valid for use inside a `with` block
    (populated by `__enter__`); they are bound to the transaction's own
    session and must not auto-commit individually — only `commit()` on this
    object should make their writes durable.

    Since Fase 5, `human_review_repository` is also exposed so a new final
    HumanReview can demote the previous final review and insert the new one
    in a single commit.
    """

    analysis_run_repository: AnalysisRunRepositoryPort
    dataset_item_repository: DatasetItemRepositoryPort
    dataset_release_repository: DatasetReleaseRepositoryPort
    dataset_snapshot_repository: DatasetSnapshotRepositoryPort
    dataset_split_item_repository: DatasetSplitItemRepositoryPort
    human_review_repository: HumanReviewRepositoryPort
    prediction_repository: PredictionRepositoryPort

    @abstractmethod
    def __enter__(self) -> "UnitOfWorkPort":
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
