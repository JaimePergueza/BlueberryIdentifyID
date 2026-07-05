"""Unit tests for PetriVisualSignalExtractor (Fase 41)."""

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from blueberry_microid.ml.inference_engine.petri_visual_signal_extractor import (
    PetriVisualSignalExtractor,
    PetriVisualSignals,
)


def _jpeg(width: int = 64, height: int = 64, color=(200, 200, 200)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _jpeg_with_dark_spot(width: int = 100, height: int = 100) -> bytes:
    """Bright background with a small dark region (simulates a colony)."""
    arr = np.full((height, width, 3), 200, dtype=np.uint8)
    arr[35:50, 35:50] = 20  # dark patch in center
    buf = BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG")
    return buf.getvalue()


def _corrupted() -> bytes:
    return b"not-an-image"


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────

def test_returns_petri_visual_signals_instance():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert isinstance(result, PetriVisualSignals)


def test_extraction_ok_for_valid_image():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert result.extraction_ok is True


def test_coverage_between_zero_and_one():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert 0.0 <= result.colony_coverage <= 1.0


def test_mean_intensity_in_range():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert 0.0 <= result.mean_intensity <= 255.0


def test_mean_saturation_in_range():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert 0.0 <= result.mean_saturation <= 1.0


def test_region_count_non_negative():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert result.region_count >= 0


def test_sharpness_non_negative():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert result.sharpness >= 0.0


def test_dark_spot_detected_as_candidate_region():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg_with_dark_spot())
    # A clearly dark patch on a bright background should produce >= 1 region
    assert result.region_count >= 1


def test_uniform_bright_image_has_low_coverage():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg(color=(220, 220, 220)))
    # A uniform bright plate should have very low colony coverage
    assert result.colony_coverage < 0.30


# ─────────────────────────────────────────────────────────────────────────────
# Error / degraded path
# ─────────────────────────────────────────────────────────────────────────────

def test_corrupted_bytes_returns_fallback():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_corrupted())
    assert result.extraction_ok is False
    assert result.region_count == 0
    assert result.colony_coverage == 0.0


def test_corrupted_bytes_includes_warning():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_corrupted())
    assert len(result.warnings) > 0
    assert any("extraction failed" in w.lower() for w in result.warnings)


def test_empty_bytes_returns_fallback():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(b"")
    assert result.extraction_ok is False


# ─────────────────────────────────────────────────────────────────────────────
# Quality warnings
# ─────────────────────────────────────────────────────────────────────────────

def test_overexposed_image_generates_warning():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg(color=(255, 255, 255)))
    assert any("overexposed" in w.lower() for w in result.warnings)


def test_underexposed_image_generates_warning():
    extractor = PetriVisualSignalExtractor()
    result = extractor.extract(_jpeg(color=(10, 10, 10)))
    assert any("underexposed" in w.lower() for w in result.warnings)
