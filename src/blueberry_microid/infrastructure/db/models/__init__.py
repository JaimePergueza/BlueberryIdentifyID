"""All ORM models must be imported here so SQLAlchemy can resolve the
string-based relationship() references between them before the mapper
configuration is used (e.g. by Base.metadata.create_all() or Alembic).
"""

from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
from blueberry_microid.infrastructure.db.models.annotation_bundle_file import AnnotationBundleFileModel
from blueberry_microid.infrastructure.db.models.annotation_bundle_run import AnnotationBundleRunModel
from blueberry_microid.infrastructure.db.models.annotation_quality_gate_issue import AnnotationQualityGateIssueModel
from blueberry_microid.infrastructure.db.models.annotation_quality_gate_run import AnnotationQualityGateRunModel
from blueberry_microid.infrastructure.db.models.base import Base
from blueberry_microid.infrastructure.db.models.dataset_item import DatasetItemModel
from blueberry_microid.infrastructure.db.models.dataset_release import DatasetReleaseModel
from blueberry_microid.infrastructure.db.models.dataset_snapshot import DatasetSnapshotModel
from blueberry_microid.infrastructure.db.models.dataset_split_item import DatasetSplitItemModel
from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
from blueberry_microid.infrastructure.db.models.image_dataset_audit_issue import ImageDatasetAuditIssueModel
from blueberry_microid.infrastructure.db.models.image_dataset_audit_run import ImageDatasetAuditRunModel
from blueberry_microid.infrastructure.db.models.image_feature_extraction_run import ImageFeatureExtractionRunModel
from blueberry_microid.infrastructure.db.models.image_feature_vector import ImageFeatureVectorModel
from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
from blueberry_microid.infrastructure.db.models.model_version import ModelVersionModel
from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
from blueberry_microid.infrastructure.db.models.petri_annotation_export_item import PetriAnnotationExportItemModel
from blueberry_microid.infrastructure.db.models.petri_annotation_export_run import PetriAnnotationExportRunModel
from blueberry_microid.infrastructure.db.models.petri_region_review import PetriRegionReviewModel
from blueberry_microid.infrastructure.db.models.petri_segmentation_region import PetriSegmentationRegionModel
from blueberry_microid.infrastructure.db.models.petri_segmentation_run import PetriSegmentationRunModel
from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
from blueberry_microid.infrastructure.db.models.sample import SampleModel
from blueberry_microid.infrastructure.db.models.training_preflight_issue import TrainingPreflightIssueModel
from blueberry_microid.infrastructure.db.models.training_preflight_run import TrainingPreflightRunModel
from blueberry_microid.infrastructure.db.models.training_prediction import TrainingPredictionModel
from blueberry_microid.infrastructure.db.models.training_run import TrainingRunModel
from blueberry_microid.infrastructure.db.models.training_run_comparison import TrainingRunComparisonModel
from blueberry_microid.infrastructure.db.models.training_run_comparison_entry import TrainingRunComparisonEntryModel

__all__ = [
    "AnalysisRunModel",
    "AnnotationBundleFileModel",
    "AnnotationBundleRunModel",
    "AnnotationQualityGateIssueModel",
    "AnnotationQualityGateRunModel",
    "Base",
    "DatasetItemModel",
    "DatasetReleaseModel",
    "DatasetSnapshotModel",
    "DatasetSplitItemModel",
    "HumanReviewModel",
    "ImageDatasetAuditIssueModel",
    "ImageDatasetAuditRunModel",
    "ImageFeatureExtractionRunModel",
    "ImageFeatureVectorModel",
    "MicroImageModel",
    "ModelVersionModel",
    "PetriImageModel",
    "PetriAnnotationExportItemModel",
    "PetriAnnotationExportRunModel",
    "PetriRegionReviewModel",
    "PetriSegmentationRegionModel",
    "PetriSegmentationRunModel",
    "PredictionModel",
    "SampleModel",
    "TrainingPreflightIssueModel",
    "TrainingPreflightRunModel",
    "TrainingPredictionModel",
    "TrainingRunModel",
    "TrainingRunComparisonModel",
    "TrainingRunComparisonEntryModel",
]
