"""Keep operational morphology hypotheses out of final and training contracts.

The morphology differential is designed for specialist review in the analysis
detail view. It must not become reviewed ground truth, leak into training
features, or appear as part of the authoritative final-result contract.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_DIFFERENTIAL_FEATURE_KEY = "taxonomic_differential"
_DIFFERENTIAL_TRACE_STEP = "taxonomic_differential"
_DIFFERENTIAL_WARNING_PREFIX = "Las hipótesis de género son compatibilidades morfológicas"


def feature_summary_without_operational_differential(
    feature_summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return a defensive copy containing only reusable visual measurements."""

    if feature_summary is None:
        return None
    filtered = deepcopy(feature_summary)
    filtered.pop(_DIFFERENTIAL_FEATURE_KEY, None)
    return filtered


def decision_trace_without_operational_differential(
    decision_trace: list[Any] | None,
) -> list[Any] | None:
    """Remove the review-support interpretation step from the final contract."""

    if decision_trace is None:
        return None
    return [
        deepcopy(step)
        for step in decision_trace
        if not (
            isinstance(step, dict)
            and step.get("step") == _DIFFERENTIAL_TRACE_STEP
        )
    ]


def warnings_without_operational_differential(
    warnings: list[str] | None,
) -> list[str] | None:
    """Remove warnings that only describe the optional differential layer."""

    if warnings is None:
        return None
    return [
        warning
        for warning in warnings
        if not warning.startswith(_DIFFERENTIAL_WARNING_PREFIX)
    ]
