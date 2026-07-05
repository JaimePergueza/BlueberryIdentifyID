from enum import Enum


class DatasetReleaseKind(str, Enum):
    SPLIT_RELEASE = "split_release"
    SNAPSHOT_RELEASE = "snapshot_release"
