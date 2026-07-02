from uuid import uuid4

from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.enums.model_type import ModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.ml.inference_engine.mock_inference_engine import MockInferenceEngine

# Taxon-shaped words a mock engine must never emit anywhere in its output.
_FORBIDDEN_TAXONOMY_WORDS = (
    "aspergillus",
    "penicillium",
    "botrytis",
    "escherichia",
    "salmonella",
    "fungus",
    "species",
    "genus",
)


def _build_run_and_inputs():
    sample_id = uuid4()
    petri_image = PetriImage(
        sample_id=sample_id, file_path="/p", file_name="p.jpg", mime_type="image/jpeg", file_size_bytes=1
    )
    micro_image = MicroImage(
        sample_id=sample_id, file_path="/m", file_name="m.jpg", mime_type="image/jpeg", file_size_bytes=1
    )
    model_version = ModelVersion(name="stub", version="0.1.0", model_type=ModelType.MOCK)
    analysis_run = AnalysisRun.create(petri_image=petri_image, micro_image=micro_image, model_version_id=model_version.id)
    return analysis_run, petri_image, micro_image, model_version


def test_mock_inference_engine_returns_valid_output():
    analysis_run, petri_image, micro_image, model_version = _build_run_and_inputs()
    engine = MockInferenceEngine()

    output = engine.process(
        analysis_run=analysis_run, petri_image=petri_image, micro_image=micro_image, model_version=model_version
    )

    assert isinstance(output.predicted_label, PredictedLabel)
    assert output.confidence_score is not None
    assert 0.0 <= output.confidence_score <= 1.0
    assert output.class_probabilities is not None
    assert abs(sum(output.class_probabilities.values()) - 1.0) < 1e-6
    assert output.technical_observation
    assert isinstance(output.requires_human_review, bool)


def test_mock_inference_engine_is_deterministic_for_the_same_run():
    analysis_run, petri_image, micro_image, model_version = _build_run_and_inputs()
    engine = MockInferenceEngine()

    first = engine.process(
        analysis_run=analysis_run, petri_image=petri_image, micro_image=micro_image, model_version=model_version
    )
    second = engine.process(
        analysis_run=analysis_run, petri_image=petri_image, micro_image=micro_image, model_version=model_version
    )

    assert first.predicted_label == second.predicted_label
    assert first.confidence_score == second.confidence_score


def test_mock_inference_engine_marks_inconclusive_as_requiring_review():
    engine = MockInferenceEngine()
    # Search a handful of runs for one that lands on INCONCLUSIVE — the
    # label is a deterministic hash of analysis_run.id, not configurable
    # directly, so we just need *a* run that produces it.
    found_inconclusive = False
    for _ in range(50):
        analysis_run, petri_image, micro_image, model_version = _build_run_and_inputs()
        output = engine.process(
            analysis_run=analysis_run, petri_image=petri_image, micro_image=micro_image, model_version=model_version
        )
        if output.predicted_label == PredictedLabel.INCONCLUSIVE:
            found_inconclusive = True
            assert output.requires_human_review is True
    assert found_inconclusive, "expected at least one of 50 random runs to hash to INCONCLUSIVE"


def test_mock_inference_engine_never_mentions_species_or_genus():
    engine = MockInferenceEngine()

    for _ in range(20):
        analysis_run, petri_image, micro_image, model_version = _build_run_and_inputs()
        output = engine.process(
            analysis_run=analysis_run, petri_image=petri_image, micro_image=micro_image, model_version=model_version
        )

        # predicted_label must be one of the broad enum values, never free text.
        assert output.predicted_label in set(PredictedLabel)

        haystack = " ".join(
            [
                output.technical_observation or "",
                *(output.class_probabilities or {}).keys(),
            ]
        ).lower()
        for forbidden_word in _FORBIDDEN_TAXONOMY_WORDS:
            assert forbidden_word not in haystack


def test_mock_inference_engine_confidence_is_moderate_not_falsely_high():
    engine = MockInferenceEngine()

    for _ in range(20):
        analysis_run, petri_image, micro_image, model_version = _build_run_and_inputs()
        output = engine.process(
            analysis_run=analysis_run, petri_image=petri_image, micro_image=micro_image, model_version=model_version
        )
        # Never near-certain: a simulated engine must not look more
        # confident than a real, unvalidated model would be allowed to.
        assert output.confidence_score <= 0.75
