from enum import Enum


class PetriAnnotationExportDecisionFilter(str, Enum):
    VALID_ONLY = "valid_only"
    VALID_AND_UNCERTAIN = "valid_and_uncertain"
    ALL_FINAL_REVIEWS = "all_final_reviews"
