from enum import Enum


class ModelType(str, Enum):
    """Kind of engine backing a ModelVersion. `MOCK` is the only kind used until a real model exists."""

    MOCK = "mock"
    PYTORCH = "pytorch"
    EXTERNAL = "external"
