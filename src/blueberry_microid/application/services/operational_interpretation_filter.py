"""Keep operational interpretation layers out of final and training contracts.

The taxonomic differential and coherence assessment support specialist review
in the analysis-detail view. They must not become ground truth, leak automatic
labels into training features, or appear in the authoritative final-result
contract.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_OPERATIONAL_FEATURE_KEYS = {"taxonomic_differential", "coherence_assessment"}
_OPERATIONAL_TRACE_STEPS = {"taxonomic_differential", "coherence_resolution"}
_OPERATIONAL_WARNING_PREFIXES = (
    "Las hipótesis de género son compatibilidades morfológicas",
    "Se detectó conflicto entre evidencia celular y filamentosa",
    "Faltan metadatos experimentales importantes",
)


def feature_summary_without_operational_differential(
    feature_summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return reusable visual measurements without review-support decisions."""

    if feature_summary is None:
        return None
    filtered = deepcopy(feature_summary)
    for key in _OPERATIONAL_FEATURE_KEYS:
        filtered.pop(key, None)
    return filtered


def decision_trace_without_operational_differential(
    decision_trace: list[Any] | None,
) -> list[Any] | None:
    """Remove operational interpretation steps from final/training contracts."""

    if decision_trace is None:
        return None
    return [
        deepcopy(step)
        for step in decision_trace
        if not (
            isinstance(step, dict)
            and step.get("step") in _OPERATIONAL_TRACE_STEPS
        )
    ]


def warnings_without_operational_differential(
    warnings: list[str] | None,
) -> list[str] | None:
    """Remove warnings that only describe operational interpretation layers."""

    if warnings is None:
        return None
    return [
        warning
        for warning in warnings
        if not warning.startswith(_OPERATIONAL_WARNING_PREFIXES)
    ]
