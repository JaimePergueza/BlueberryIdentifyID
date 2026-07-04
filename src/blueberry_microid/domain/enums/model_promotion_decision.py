from enum import Enum


class ModelPromotionDecision(str, Enum):
    SMOKE_ONLY = "smoke_only"
    NOT_EVALUABLE = "not_evaluable"
    NOT_PROMOTABLE = "not_promotable"
    PROMOTABLE_WITH_WARNINGS = "promotable_with_warnings"
    PROMOTABLE = "promotable"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    FAILED_EVALUATION = "failed_evaluation"
