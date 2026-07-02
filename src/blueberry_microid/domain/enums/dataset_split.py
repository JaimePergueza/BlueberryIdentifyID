from enum import Enum


class DatasetSplit(str, Enum):
    """A reproducible train/validation/test partition assignment.

    Not a microbiological category — purely a dataset-engineering label.
    """

    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
