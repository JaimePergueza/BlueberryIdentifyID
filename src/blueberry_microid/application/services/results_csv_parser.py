from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any


class ResultsCsvParserError(RuntimeError):
    pass


class ResultsCsvParser:
    _COLUMN_ALIASES = {
        "precision": ("metrics/precision(B)", "metrics/precision", "precision"),
        "recall": ("metrics/recall(B)", "metrics/recall", "recall"),
        "map50": ("metrics/mAP50(B)", "metrics/mAP50", "mAP50"),
        "map50_95": ("metrics/mAP50-95(B)", "metrics/mAP50-95", "mAP50-95"),
        "train_box_loss": ("train/box_loss",),
        "train_cls_loss": ("train/cls_loss",),
        "train_dfl_loss": ("train/dfl_loss",),
        "val_box_loss": ("val/box_loss",),
        "val_cls_loss": ("val/cls_loss",),
        "val_dfl_loss": ("val/dfl_loss",),
        "epoch": ("epoch",),
    }

    def parse(self, path: str | Path) -> dict[str, Any]:
        results_path = Path(path)
        if not results_path.exists():
            raise ResultsCsvParserError(f"results.csv does not exist: {results_path}")
        with results_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            return {"path": str(results_path), "latest": {}, "issues": [{"code": "empty_results_csv"}]}
        latest = {self._normalise_column(k): v for k, v in rows[-1].items()}
        metrics: dict[str, Any] = {}
        issues: list[dict[str, Any]] = []
        for name, aliases in self._COLUMN_ALIASES.items():
            value = self._first_value(latest, aliases)
            if value is None:
                issues.append({"code": "metric_missing", "metric": name})
                metrics[name] = None
                continue
            parsed = self._parse_float(value)
            metrics[name] = parsed
            if parsed is None:
                issues.append({"code": "metric_not_numeric", "metric": name, "value": value})
            elif isinstance(parsed, float) and math.isnan(parsed):
                issues.append({"code": "metric_nan", "metric": name})
        core = [metrics.get("precision"), metrics.get("recall"), metrics.get("map50"), metrics.get("map50_95")]
        metrics["core_metrics_all_zero"] = all(value == 0 for value in core if value is not None)
        if metrics["core_metrics_all_zero"]:
            issues.append({"code": "core_metrics_zero"})
        return {"path": str(results_path), "latest": metrics, "row_count": len(rows), "issues": issues}

    def _normalise_column(self, value: str) -> str:
        return value.strip()

    def _first_value(self, row: dict[str, str], aliases: tuple[str, ...]) -> str | None:
        for alias in aliases:
            if alias in row:
                return row[alias]
        return None

    def _parse_float(self, value: str | None) -> float | int | None:
        if value is None or value == "":
            return None
        try:
            number = float(value)
        except ValueError:
            return None
        if number.is_integer():
            return int(number)
        return number
