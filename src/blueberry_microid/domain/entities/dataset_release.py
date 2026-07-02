from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from blueberry_microid.domain.exceptions.errors import InvalidSplitRatiosError

_RATIO_SUM_TOLERANCE = 1e-6


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_split_ratios(train_ratio: float, validation_ratio: float, test_ratio: float) -> None:
    """Shared invariant between `DatasetRelease` and `DatasetSplitter`.

    Each ratio must be in [0, 1] and the three must sum to 1.0 (within
    floating-point tolerance). Defined once so both the entity's own
    `__post_init__` and the splitter (which must validate *before* it even
    has enough information to construct a `DatasetRelease`) apply exactly
    the same rule.
    """
    for name, value in (
        ("train_ratio", train_ratio),
        ("validation_ratio", validation_ratio),
        ("test_ratio", test_ratio),
    ):
        if value < 0 or value > 1:
            raise InvalidSplitRatiosError(f"{name} must be between 0 and 1, got {value}")
    total = train_ratio + validation_ratio + test_ratio
    if abs(total - 1.0) > _RATIO_SUM_TOLERANCE:
        raise InvalidSplitRatiosError(
            f"train_ratio + validation_ratio + test_ratio must sum to 1.0, got {total}"
        )


@dataclass(frozen=True)
class DatasetRelease:
    """A reproducible train/validation/test partition of a DatasetSnapshot.

    Never copies image bytes and never mutates the DatasetSnapshot or its
    DatasetItems — it only records how each already-curated item was
    assigned to a split, deterministically, given `random_seed`. Partitioning
    happens at the Sample level (see `DatasetSplitter`), never at the
    individual DatasetItem/image level, to prevent leakage of a Sample's
    evidence across splits.
    """

    dataset_snapshot_id: UUID
    name: str
    version: str
    split_strategy: str
    random_seed: int
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    id: UUID = field(default_factory=uuid4)
    item_count: int = 0
    train_count: int = 0
    validation_count: int = 0
    test_count: int = 0
    label_distribution: Optional[dict[str, int]] = None
    split_distribution: Optional[dict[str, dict[str, int]]] = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        validate_split_ratios(self.train_ratio, self.validation_ratio, self.test_ratio)
