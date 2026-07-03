from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class TrainingManifestItem:
    split: str
    analysis_run_id: str
    sample_id: str
    sample_code: str
    petri_image_path: str
    micro_image_path: str
    ground_truth_label: str
    prediction_label: str
    source_review_decision: str
    final_review_id: str
    lot_code: Optional[str] = None
    origin: Optional[str] = None
    dataset_item_id: Optional[str] = None
    dataset_split_item_id: Optional[str] = None
    petri_width: Optional[int] = None
    petri_height: Optional[int] = None
    petri_file_size_bytes: Optional[int] = None
    micro_width: Optional[int] = None
    micro_height: Optional[int] = None
    micro_file_size_bytes: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingManifestItem":
        return cls(
            split=str(data.get("split", "")),
            analysis_run_id=str(data.get("analysis_run_id", "")),
            sample_id=str(data.get("sample_id", "")),
            sample_code=str(data.get("sample_code", "")),
            lot_code=data.get("lot_code"),
            origin=data.get("origin"),
            dataset_item_id=data.get("dataset_item_id"),
            dataset_split_item_id=data.get("dataset_split_item_id"),
            petri_image_path=str(data.get("petri_image_path", "")),
            micro_image_path=str(data.get("micro_image_path", "")),
            petri_width=data.get("petri_width"),
            petri_height=data.get("petri_height"),
            petri_file_size_bytes=data.get("petri_file_size_bytes"),
            micro_width=data.get("micro_width"),
            micro_height=data.get("micro_height"),
            micro_file_size_bytes=data.get("micro_file_size_bytes"),
            ground_truth_label=str(data.get("ground_truth_label", "")),
            prediction_label=str(data.get("prediction_label", "")),
            source_review_decision=str(data.get("source_review_decision", "")),
            final_review_id=str(data.get("final_review_id", "")),
        )

    def identity_key(self) -> tuple[str, str, str]:
        return (self.analysis_run_id, self.petri_image_path, self.micro_image_path)


@dataclass(frozen=True, slots=True)
class TrainingManifest:
    dataset_release_id: str
    dataset_snapshot_id: str
    name: str
    version: str
    split_strategy: str
    random_seed: int
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    item_count: int
    train_count: int
    validation_count: int
    test_count: int
    label_distribution: dict[str, int] = field(default_factory=dict)
    split_distribution: dict[str, dict[str, int]] = field(default_factory=dict)
    items: list[TrainingManifestItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingManifest":
        ratios = data.get("ratios", {})
        counts = data.get("counts", {})
        return cls(
            dataset_release_id=str(data.get("dataset_release_id", "")),
            dataset_snapshot_id=str(data.get("dataset_snapshot_id", "")),
            name=str(data.get("name", "")),
            version=str(data.get("version", "")),
            split_strategy=str(data.get("split_strategy", "")),
            random_seed=int(data.get("random_seed", 0)),
            train_ratio=float(ratios.get("train", data.get("train_ratio", 0.0))),
            validation_ratio=float(ratios.get("validation", data.get("validation_ratio", 0.0))),
            test_ratio=float(ratios.get("test", data.get("test_ratio", 0.0))),
            item_count=int(counts.get("total", data.get("item_count", 0))),
            train_count=int(counts.get("train", data.get("train_count", 0))),
            validation_count=int(counts.get("validation", data.get("validation_count", 0))),
            test_count=int(counts.get("test", data.get("test_count", 0))),
            label_distribution=dict(data.get("label_distribution") or {}),
            split_distribution=dict(data.get("split_distribution") or {}),
            items=[TrainingManifestItem.from_dict(item) for item in data.get("items", [])],
        )

