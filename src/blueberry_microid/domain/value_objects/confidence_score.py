from dataclasses import dataclass

from blueberry_microid.domain.exceptions.errors import InvalidConfidenceScoreError


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """A model's confidence in a prediction, constrained to the closed interval [0, 1].

    This is a technical score, not a diagnostic guarantee.
    """

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise InvalidConfidenceScoreError(
                f"confidence_score must be between 0 and 1, got {self.value}"
            )

    def __float__(self) -> float:
        return self.value
