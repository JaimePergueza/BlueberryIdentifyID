from enum import Enum


class PredictedLabel(str, Enum):
    """Preliminary visual classes produced by the inference engine.

    These are broad, non-diagnostic categories. They never encode a species or
    genus, and must not be extended with taxonomic values without a validated
    dataset and expert review protocol.
    """

    NO_EVIDENT_GROWTH = "no_evident_growth"
    SUSPICIOUS_GROWTH = "suspicious_growth"
    PROBABLE_FUNGAL_GROWTH = "probable_fungal_growth"
    PROBABLE_BACTERIAL_GROWTH = "probable_bacterial_growth"
    INCONCLUSIVE = "inconclusive"
