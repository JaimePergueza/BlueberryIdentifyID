from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

_MODEL_FAMILIES = {"mock_baseline", "future_cnn", "future_vit", "future_late_fusion"}
_FUSION_STRATEGIES = {"petri_only", "micro_only", "late_fusion"}


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Future training configuration contract. It does not instantiate models."""

    experiment_name: str
    output_dir: str
    model_family: str = "mock_baseline"
    fusion_strategy: str = "late_fusion"
    dataset_manifest_path: Optional[str] = None
    petri_input_enabled: bool = True
    micro_input_enabled: bool = True
    batch_size: int = 8
    max_epochs: int = 1
    learning_rate: float = 0.001
    random_seed: int = 42
    num_workers: int = 0
    require_lot_aware_split: bool = False
    min_total_items: int = 1
    min_items_per_split: int = 1
    min_items_per_class: int = 1
    allow_inconclusive: bool = False

    def __post_init__(self) -> None:
        if self.model_family not in _MODEL_FAMILIES:
            raise ValueError(f"unsupported model_family '{self.model_family}'")
        if self.fusion_strategy not in _FUSION_STRATEGIES:
            raise ValueError(f"unsupported fusion_strategy '{self.fusion_strategy}'")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if self.max_epochs <= 0:
            raise ValueError("max_epochs must be > 0")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be > 0")
        if self.num_workers < 0:
            raise ValueError("num_workers must be >= 0")
        if self.min_total_items < 1:
            raise ValueError("min_total_items must be >= 1")
        if self.min_items_per_split < 1:
            raise ValueError("min_items_per_split must be >= 1")
        if self.min_items_per_class < 1:
            raise ValueError("min_items_per_class must be >= 1")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingConfig":
        return cls(**data)

