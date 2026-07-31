from io import BytesIO
import random

from PIL import Image, ImageDraw

from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.inference_engine.micro_visual_signal_extractor import (
    MicroVisualSignalExtractor,
    MicroVisualSignals,
)
from blueberry_microid.ml.inference_engine.petri_visual_signal_extractor import (
    PetriVisualSignalExtractor,
    PetriVisualSignals,
)
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    _build_quality_summary,
    _classify,
)


def _image_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _dark_large_colony_petri() -> bytes:
    image = Image.new("RGB", (420, 420), "#111111")
    draw = ImageDraw.Draw(image)
    draw.ellipse((25, 25, 395, 395), fill="#303637", outline="#aeb9b7", width=8)

    colonies = [
        [(80, 80, 185, 190), (100, 70, 200, 175), (70, 105, 180, 205)],
        [(235, 70, 350, 185), (260, 95, 370, 210), (225, 110, 345, 225)],
        [(90, 235, 210, 360), (120, 220, 230, 345), (70, 250, 195, 370)],
        [(240, 235, 360, 360), (265, 215, 380, 345), (225, 255, 345, 375)],
    ]
    for group in colonies:
        for box in group:
            draw.ellipse(box, fill="#77817a")

    for x_value in range(95, 345, 24):
        for y_value in range(90, 350, 28):
            if (x_value + y_value) % 3 == 0:
                draw.ellipse(
                    (x_value, y_value, x_value + 5, y_value + 5),
                    fill="#9da89e",
                )
    return _image_bytes(image)


def _noisy_branching_micro() -> bytes:
    image = Image.new("RGB", (420, 420), "#111111")
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 20, 400, 400), fill="#e7e9e5")

    for offset in range(-20, 21, 10):
        draw.line(
            (80, 330 + offset, 210, 200, 340, 90 + offset),
            fill="#76515d",
            width=4,
        )
    draw.line((210, 200, 320, 280), fill="#76515d", width=4)
    draw.line((210, 200, 120, 90), fill="#76515d", width=4)

    generator = random.Random(7)
    for _ in range(800):
        x_value = generator.randint(35, 385)
        y_value = generator.randint(35, 385)
        if (x_value - 210) ** 2 + (y_value - 210) ** 2 < 175**2:
            draw.point((x_value, y_value), fill="#777777")
    return _image_bytes(image)


def test_dark_medium_with_large_colonies_is_not_reported_as_empty():
    result = PetriVisualSignalExtractor().extract(_dark_large_colony_petri())

    assert result.extraction_ok is True
    assert result.plate_detected is True
    assert result.region_count >= 2
    assert result.colony_coverage > 0.15
    assert result.segmentation_conflict is False
    assert result.visualization is not None
    assert len(result.visualization["regions"]) >= 2


def test_noisy_micro_overlay_is_pruned_and_branch_points_are_clustered():
    result = MicroVisualSignalExtractor().extract(_noisy_branching_micro())

    assert result.extraction_ok is True
    assert result.field_detected is True
    assert result.filament_coverage > 0.0
    assert result.visualization is not None
    assert 1 <= len(result.visualization["regions"]) <= 50
    assert len(result.visualization["branch_points"]) <= 50


def test_growth_like_signal_without_reliable_regions_blocks_no_growth_label():
    petri = PetriVisualSignals(
        region_count=0,
        colony_coverage=0.0,
        mean_saturation=0.0,
        mean_intensity=120.0,
        sharpness=200.0,
        extraction_ok=True,
        plate_detected=True,
        candidate_signal_fraction=0.30,
        segmentation_conflict=True,
    )
    micro = MicroVisualSignals(
        mean_intensity=160.0,
        intensity_std=25.0,
        sharpness=200.0,
        edge_density=0.08,
        extraction_ok=True,
        field_detected=True,
        filament_coverage=0.05,
        component_count=10,
    )

    quality = _build_quality_summary(petri, micro)
    label, confidence, explanation, trace = _classify(petri, micro, quality)

    assert quality["overall_status"] == "rejected"
    assert quality["petri_segmentation_conflict"] is True
    assert label == PredictedLabel.INCONCLUSIVE
    assert confidence == 0.25
    assert "segmentación" in explanation.lower()
    assert trace[0]["step"] == "quality_gate"
    assert trace[0]["passed"] is False
