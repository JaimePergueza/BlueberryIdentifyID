from enum import Enum


class PetriAnnotationBboxSource(str, Enum):
    CORRECTED = "corrected"
    ORIGINAL = "original"
