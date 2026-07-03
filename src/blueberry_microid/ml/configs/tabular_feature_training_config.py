from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional
from uuid import UUID

from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType

_FUSION_STRATEGIES = {"petri_only", "micro_only", "concatenate"}


@dataclass(frozen=True, slots=True)
class TabularFeatureTrainingConfig:
    """Configuration for classical tabular baselines over ImageFeatureVector.

    This config never refers to raw image loading, tensors, or deep-learning
    models. The feature_extraction_run_id selects already-persisted features.
    """

    feature_extraction_run_id: UUID
    model_type: BaselineModelType = BaselineModelType.LOGISTIC_REGRESSION_TABULAR
    use_petri_features: bool = True
    use_micro_features: bool = True
    fusion_strategy: str = "concatenate"
    standardize_features: bool = True
    max_iter: int = 500
    random_seed: int = 42
    min_train_items: int = 2
    min_classes_train: int = 2
    allow_inconclusive: bool = False
    class_weight: Optional[str] = None
    solver: Optional[str] = None
    fail_on_missing_feature: bool = True

    def __post_init__(self) -> None:
        if self.model_type != BaselineModelType.LOGISTIC_REGRESSION_TABULAR:
            raise ValueError("only logistic_regression_tabular is supported for classical tabular training")
        if self.fusion_strategy not in _FUSION_STRATEGIES:
            raise ValueError(f"unsupported fusion_strategy '{self.fusion_strategy}'")
        if self.fusion_strategy == "petri_only" and not self.use_petri_features:
            raise ValueError("petri_only fusion requires use_petri_features=true")
        if self.fusion_strategy == "micro_only" and not self.use_micro_features:
            raise ValueError("micro_only fusion requires use_micro_features=true")
        if self.fusion_strategy == "concatenate" and not (self.use_petri_features or self.use_micro_features):
            raise ValueError("at least one modality must be enabled")
        if self.max_iter <= 0:
            raise ValueError("max_iter must be > 0")
        if self.min_train_items < 1:
            raise ValueError("min_train_items must be >= 1")
        if self.min_classes_train < 2:
            raise ValueError("min_classes_train must be >= 2")
        if self.class_weight not in (None, "balanced"):
            raise ValueError("class_weight must be null or 'balanced'")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TabularFeatureTrainingConfig":
        payload = dict(data)
        if "feature_extraction_run_id" in payload:
            payload["feature_extraction_run_id"] = UUID(str(payload["feature_extraction_run_id"]))
        if "model_type" in payload:
            payload["model_type"] = BaselineModelType(payload["model_type"])
        return cls(**payload)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_extraction_run_id"] = str(self.feature_extraction_run_id)
        payload["model_type"] = self.model_type.value
        return payload
