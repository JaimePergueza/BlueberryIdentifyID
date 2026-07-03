from enum import Enum


class ImageModality(str, Enum):
    """Which of the two image sources per Sample an audit finding refers to."""

    PETRI = "petri"
    MICRO = "micro"
