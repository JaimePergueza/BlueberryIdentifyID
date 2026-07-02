from dataclasses import dataclass

from blueberry_microid.domain.exceptions.errors import EmptySampleCodeError


@dataclass(frozen=True, slots=True)
class SampleCode:
    """Non-empty, whitespace-trimmed identifier a lab assigns to a sample."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise EmptySampleCodeError("sample_code cannot be empty or whitespace-only")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
