from io import BytesIO

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
    PreliminaryTwoImageAnalysisEngine,
    _build_quality_summary,
    _classify,
)


def _image_bytes(image: Image.Image, image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def _synthetic_petri() -> bytes:
    image = Image.new("RGB", (320, 320), "#111111")
    draw = ImageDraw.Draw(image)
    draw.ellipse((25, 25, 295, 295), fill="#8b9081", outline="#d7ddd0", width=6)
    draw.ellipse((70, 65, 175, 170), fill="#ded5b6")
    draw.ellipse((165, 105, 270, 220), fill="#d7ceb1")
    draw.ellipse((85, 180, 195, 285), fill="#e2d9be")
    for offset in range(0, 70, 7):
        draw.line((85 + offset, 75, 105 + offset, 158), fill="#a49b7e", width=2)
    return _image_bytes(image)


def _synthetic_branching_micro() -> bytes:
    image = Image.new("RGB", (320, 320), "#111111")
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 20, 300, 300), fill="#e9ece8")
    lines = [
        ((55, 250), (155, 155)),
        ((155, 155), (250, 70)),
        ((155, 155), (255, 175)),
        ((155, 155), (115, 60)),
        ((110, 210), (225, 255)),
        ((100, 90), (235, 225)),
    ]
    for start, end in lines:
        draw.line((*start, *end), fill="#76515d", width=5)
    return _image_bytes(image)


def test_petri_extractor_reports_plate_region_morphology_and_overlay():
    result = PetriVisualSignalExtractor().extract(_synthetic_petri())

    assert result.extraction_ok is True
    assert result.plate_detected is True
    assert result.region_count >= 1
    assert result.colony_coverage > 0.0
    assert 0.0 <= result.mean_circularity <= 1.0
    assert 0.0 <= result.edge_irregularity <= 1.0
    assert result.mean_texture_std >= 0.0
    assert result.visualization is not None
    assert result.visualization["coordinate_space"] == "normalized"
    assert result.visualization["outline"] is not None
    assert result.visualization["regions"]
    first_box = result.visualization["regions"][0]["bbox"]
    assert all(0.0 <= first_box[key] <= 1.0 for key in ("x", "y", "width", "height"))


def test_micro_extractor_reports_field_filaments_and_overlay():
    result = MicroVisualSignalExtractor().extract(_synthetic_branching_micro())

    assert result.extraction_ok is True
    assert result.field_detected is True
    assert result.edge_density > 0.0
    assert result.filament_coverage > 0.0
    assert result.skeleton_density > 0.0
    assert result.component_count >= 1
    assert result.visualization is not None
    assert result.visualization["coordinate_space"] == "normalized"
    assert result.visualization["outline"] is not None
    assert result.visualization["regions"]


def test_combined_filament_signals_produce_fungal_category_when_quality_passes():
    petri = PetriVisualSignals(
        region_count=3,
        colony_coverage=0.18,
        mean_saturation=0.2,
        mean_intensity=150.0,
        sharpness=300.0,
        extraction_ok=True,
        plate_detected=True,
        mean_texture_std=24.0,
        mean_circularity=0.72,
        edge_irregularity=0.28,
    )
    micro = MicroVisualSignals(
        mean_intensity=170.0,
        intensity_std=28.0,
        sharpness=250.0,
        edge_density=0.05,
        extraction_ok=True,
        field_detected=True,
        filament_coverage=0.10,
        branch_point_density=0.001,
        elongated_component_ratio=0.80,
        component_count=18,
    )
    quality = _build_quality_summary(petri, micro)

    label, confidence, explanation, trace = _classify(petri, micro, quality)

    assert quality["overall_status"] == "accepted"
    assert label == PredictedLabel.PROBABLE_FUNGAL_GROWTH
    assert confidence <= 0.65
    assert "filament" in explanation.lower()
    assert any(step.get("step") == "evidence_fusion" for step in trace)


def test_missing_plate_or_field_forces_inconclusive_quality_rejection():
    petri = PetriVisualSignals(
        region_count=4,
        colony_coverage=0.22,
        mean_saturation=0.3,
        mean_intensity=145.0,
        sharpness=220.0,
        extraction_ok=True,
        plate_detected=False,
    )
    micro = MicroVisualSignals(
        mean_intensity=155.0,
        intensity_std=30.0,
        sharpness=180.0,
        edge_density=0.12,
        extraction_ok=True,
        field_detected=False,
        filament_coverage=0.15,
        elongated_component_ratio=0.9,
        component_count=30,
    )
    quality = _build_quality_summary(petri, micro)

    label, confidence, explanation, trace = _classify(petri, micro, quality)

    assert quality["overall_status"] == "rejected"
    assert label == PredictedLabel.INCONCLUSIVE
    assert confidence == 0.25
    assert "calidad" in explanation.lower()
    assert trace[0]["step"] == "quality_gate"
    assert trace[0]["passed"] is False
    assert not any(step.get("step") == "evidence_fusion" for step in trace)


def test_engine_exposes_visualisation_and_quality_contract():
    result = PreliminaryTwoImageAnalysisEngine().analyze(
        petri_image_bytes=_synthetic_petri(),
        micro_image_bytes=_synthetic_branching_micro(),
    )

    assert result.feature_summary is not None
    assert "mean_circularity" in result.feature_summary["petri"]
    assert "filament_coverage" in result.feature_summary["micro"]
    assert "branch_point_density" in result.feature_summary["micro"]
    assert result.feature_summary["petri"]["visualization"]["kind"] == "petri"
    assert result.feature_summary["micro"]["visualization"]["kind"] == "micro"
    assert result.quality_summary is not None
    assert result.quality_summary["overall_status"] in {"accepted", "warning"}
    assert any(step.get("step") == "evidence_fusion" for step in result.decision_trace or [])
