from enum import Enum


class ComparisonSelectionPolicy(str, Enum):
    BEST_PRIMARY_METRIC = "best_primary_metric"
    PREFER_SIMPLER_IF_TIE = "prefer_simpler_if_tie"
    NO_AUTO_SELECTION = "no_auto_selection"
