from enum import Enum


class DatasetCurationStatus(str, Enum):
    INCLUDED = "included"
    EXCLUDED_PENDING_REVIEW = "excluded_pending_review"
    EXCLUDED_INVALID_SAMPLE = "excluded_invalid_sample"
    EXCLUDED_MISSING_PREDICTION = "excluded_missing_prediction"
    EXCLUDED_MISSING_IMAGES = "excluded_missing_images"
    EXCLUDED_INVALID_LABEL = "excluded_invalid_label"
    EXCLUDED_DUPLICATE = "excluded_duplicate"
    EXCLUDED_POLICY = "excluded_policy"

