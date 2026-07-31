from enum import Enum


class ModelType(str, Enum):
    """Kind of engine backing a traceable ModelVersion.

    ``MOCK`` remains available for the legacy deterministic pipeline.
    ``CLASSICAL`` identifies image-processing engines that inspect real pixels
    with transparent, non-trained algorithms. Neither kind implies scientific
    or diagnostic validation.
    """

    MOCK = "mock"
    CLASSICAL = "classical"
    PYTORCH = "pytorch"
    EXTERNAL = "external"
