"""Unit tests for MicroVisualSignalExtractor (Fase 41)."""

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from blueberry_microid.ml.inference_engine.micro_visual_signal_extractor import (
    MicroVisualSignalExtractor,
    MicroVisualSignals,
)


def _jpeg(width: int = 64, height: int = 64, color=(128, 128, 128)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _jpeg_with_noise(width: int = 64, height: int = 64) -> bytes:
    """High-variance image with random pixels (simulates structured micro view)."""
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    buf = BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG")
    return buf.getvalue()


def _jpeg_uniform() -> bytes:
    """Completely uniform gray image (simulates empty field of view)."""
    buf = BytesIO()
    Image.new("L", (64, 64), color=128).save(buf, format="JPEG")
    return buf.getvalue()


def _corrupted() -> bytes:
    return b"not-an-image"


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────

def test_returns_micro_visual_signals_instance():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert isinstance(result, MicroVisualSignals)


def test_extraction_ok_for_valid_image():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert result.extraction_ok is True


def test_mean_intensity_in_range():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert 0.0 <= result.mean_intensity <= 255.0


def test_intensity_std_non_negative():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert result.intensity_std >= 0.0


def test_edge_density_between_zero_and_one():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert 0.0 <= result.edge_density <= 1.0


def test_sharpness_non_negative():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_jpeg())
    assert result.sharpness >= 0.0


def test_noisy_image_has_higher_edge_density_than_uniform():
    extractor = MicroVisualSignalExtractor()
    noisy = extractor.extract(_jpeg_with_noise())
    uniform = extractor.extract(_jpeg_uniform())
    assert noisy.edge_density > uniform.edge_density


def test_noisy_image_has_higher_std_than_uniform():
    extractor = MicroVisualSignalExtractor()
    noisy = extractor.extract(_jpeg_with_noise())
    uniform = extractor.extract(_jpeg_uniform())
    assert noisy.intensity_std > uniform.intensity_std


# ─────────────────────────────────────────────────────────────────────────────
# Error / degraded path
# ─────────────────────────────────────────────────────────────────────────────

def test_corrupted_bytes_returns_fallback():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_corrupted())
    assert result.extraction_ok is False
    assert result.intensity_std == 0.0
    assert result.edge_density == 0.0


def test_corrupted_bytes_includes_warning():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(_corrupted())
    assert len(result.warnings) > 0
    assert any("extraction failed" in w.lower() for w in result.warnings)


def test_empty_bytes_returns_fallback():
    extractor = MicroVisualSignalExtractor()
    result = extractor.extract(b"")
    assert result.extraction_ok is False
