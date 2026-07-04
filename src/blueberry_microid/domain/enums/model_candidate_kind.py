from enum import Enum


class ModelCandidateKind(str, Enum):
    SMOKE_YOLO = "smoke_yolo"
    EXPERIMENTAL_YOLO = "experimental_yolo"
    CLASSICAL_BASELINE = "classical_baseline"
    OTHER = "other"
