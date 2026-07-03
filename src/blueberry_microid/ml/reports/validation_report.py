from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ManifestValidationReport:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    item_count: int = 0
    split_counts: dict[str, int] = field(default_factory=dict)
    label_counts: dict[str, int] = field(default_factory=dict)
    split_label_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    leakage_checks: dict[str, bool] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "item_count": self.item_count,
            "split_counts": self.split_counts,
            "label_counts": self.label_counts,
            "split_label_counts": self.split_label_counts,
            "leakage_checks": self.leakage_checks,
            "recommendations": self.recommendations,
        }

