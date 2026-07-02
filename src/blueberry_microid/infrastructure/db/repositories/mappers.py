"""ORM model -> domain entity mappers.

Kept separate from the repositories so the conversion logic is easy to spot
and reuse; repositories never hand a SQLAlchemy model back to the
application layer.
"""

from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
from blueberry_microid.infrastructure.db.models.dataset_item import DatasetItemModel
from blueberry_microid.infrastructure.db.models.dataset_snapshot import DatasetSnapshotModel
from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
from blueberry_microid.infrastructure.db.models.model_version import ModelVersionModel
from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
from blueberry_microid.infrastructure.db.models.sample import SampleModel


def sample_to_entity(model: SampleModel) -> Sample:
    return Sample(
        sample_code=model.sample_code,
        id=model.id,
        product=model.product,
        lot_code=model.lot_code,
        origin=model.origin,
        collection_date=model.collection_date,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def petri_image_to_entity(model: PetriImageModel) -> PetriImage:
    return PetriImage(
        sample_id=model.sample_id,
        file_path=model.file_path,
        file_name=model.file_name,
        mime_type=model.mime_type,
        file_size_bytes=model.file_size_bytes,
        id=model.id,
        width=model.width,
        height=model.height,
        captured_at=model.captured_at,
        culture_medium=model.culture_medium,
        incubation_temperature_c=model.incubation_temperature_c,
        incubation_time_hours=model.incubation_time_hours,
        seeding_date=model.seeding_date,
        observed_colony_color=model.observed_colony_color,
        observed_colony_shape=model.observed_colony_shape,
        observed_colony_margin=model.observed_colony_margin,
        observed_colony_texture=model.observed_colony_texture,
        notes=model.notes,
        created_at=model.created_at,
    )


def micro_image_to_entity(model: MicroImageModel) -> MicroImage:
    return MicroImage(
        sample_id=model.sample_id,
        file_path=model.file_path,
        file_name=model.file_name,
        mime_type=model.mime_type,
        file_size_bytes=model.file_size_bytes,
        id=model.id,
        width=model.width,
        height=model.height,
        captured_at=model.captured_at,
        magnification=model.magnification,
        microscope_type=model.microscope_type,
        staining_method=model.staining_method,
        preparation_method=model.preparation_method,
        observed_structures=model.observed_structures,
        notes=model.notes,
        created_at=model.created_at,
    )


def model_version_to_entity(model: ModelVersionModel) -> ModelVersion:
    return ModelVersion(
        name=model.name,
        version=model.version,
        model_type=model.model_type,
        id=model.id,
        description=model.description,
        is_active=model.is_active,
        created_at=model.created_at,
    )


def analysis_run_to_entity(model: AnalysisRunModel) -> AnalysisRun:
    return AnalysisRun(
        sample_id=model.sample_id,
        petri_image_id=model.petri_image_id,
        micro_image_id=model.micro_image_id,
        model_version_id=model.model_version_id,
        id=model.id,
        status=model.status,
        created_at=model.created_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_message=model.error_message,
    )


def prediction_to_entity(model: PredictionModel) -> Prediction:
    return Prediction(
        analysis_run_id=model.analysis_run_id,
        predicted_label=model.predicted_label,
        id=model.id,
        confidence_score=model.confidence_score,
        class_probabilities=model.class_probabilities,
        technical_observation=model.technical_observation,
        requires_human_review=model.requires_human_review,
        created_at=model.created_at,
    )


def human_review_to_entity(model: HumanReviewModel) -> HumanReview:
    return HumanReview(
        analysis_run_id=model.analysis_run_id,
        reviewer_name=model.reviewer_name,
        review_decision=model.review_decision,
        id=model.id,
        corrected_label=model.corrected_label,
        comments=model.comments,
        is_final=model.is_final,
        created_at=model.created_at,
    )


def dataset_snapshot_to_entity(model: DatasetSnapshotModel) -> DatasetSnapshot:
    return DatasetSnapshot(
        name=model.name,
        version=model.version,
        id=model.id,
        description=model.description,
        created_at=model.created_at,
        created_by=model.created_by,
        selection_criteria=model.selection_criteria,
        item_count=model.item_count,
        label_distribution=model.label_distribution,
        notes=model.notes,
    )


def dataset_item_to_entity(model: DatasetItemModel) -> DatasetItem:
    return DatasetItem(
        dataset_snapshot_id=model.dataset_snapshot_id,
        analysis_run_id=model.analysis_run_id,
        sample_id=model.sample_id,
        petri_image_id=model.petri_image_id,
        micro_image_id=model.micro_image_id,
        prediction_id=model.prediction_id,
        final_review_id=model.final_review_id,
        source_review_decision=model.source_review_decision,
        id=model.id,
        ground_truth_label=model.ground_truth_label,
        included=model.included,
        exclusion_reason=model.exclusion_reason,
        created_at=model.created_at,
    )
