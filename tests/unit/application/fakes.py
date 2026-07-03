"""In-memory test doubles for the application ports.

Used by the Phase 2 use-case unit tests so they exercise real business logic
without touching a database or the filesystem. `PillowImageValidator` is
used directly instead of being faked here: it is pure, deterministic
in-memory computation (no filesystem/network I/O), so faking it would only
hide real validation bugs.
"""

import copy
from types import TracebackType
from typing import Optional
from uuid import UUID

from blueberry_microid.application.exceptions import (
    AnalysisRunNotFoundError,
    DuplicateFinalHumanReviewError,
    DuplicateFinalPetriRegionReviewError,
    DuplicatePredictionError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.application.ports.annotation_quality_gate_issue_repository import (
    AnnotationQualityGateIssueRepositoryPort,
)
from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.detection_training_issue_repository import (
    DetectionTrainingIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.image_dataset_audit_issue_repository import (
    ImageDatasetAuditIssueRepositoryPort,
)
from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_extraction_run_repository import (
    ImageFeatureExtractionRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_vector_repository import ImageFeatureVectorRepositoryPort
from blueberry_microid.application.ports.image_storage import ImageCategory, ImageStoragePort
from blueberry_microid.application.ports.inference_engine import InferenceEnginePort, InferenceOutput
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.petri_annotation_export_item_repository import (
    PetriAnnotationExportItemRepositoryPort,
)
from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.ports.training_preflight_issue_repository import (
    TrainingPreflightIssueRepositoryPort,
)
from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort
from blueberry_microid.application.ports.training_prediction_repository import TrainingPredictionRepositoryPort
from blueberry_microid.application.ports.training_run_comparison_entry_repository import (
    TrainingRunComparisonEntryRepositoryPort,
)
from blueberry_microid.application.ports.training_run_comparison_repository import (
    TrainingRunComparisonRepositoryPort,
)
from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.entities.annotation_quality_gate_issue import AnnotationQualityGateIssue
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue
from blueberry_microid.domain.entities.detection_training_run import DetectionTrainingRun
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.image_dataset_audit_issue import ImageDatasetAuditIssue
from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun
from blueberry_microid.domain.entities.image_feature_extraction_run import ImageFeatureExtractionRun
from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem
from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.entities.training_preflight_issue import TrainingPreflightIssue
from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun
from blueberry_microid.domain.entities.training_prediction import TrainingPrediction
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.entities.training_run_comparison import TrainingRunComparison
from blueberry_microid.domain.entities.training_run_comparison_entry import TrainingRunComparisonEntry
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.dataset_split import DatasetSplit


class InMemorySampleRepository(SampleRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, Sample] = {}

    def add(self, sample: Sample) -> Sample:
        self._by_id[sample.id] = sample
        return sample

    def get_by_id(self, sample_id: UUID) -> Optional[Sample]:
        return self._by_id.get(sample_id)

    def get_by_sample_code(self, sample_code: str) -> Optional[Sample]:
        return next((s for s in self._by_id.values() if s.sample_code == sample_code), None)


class InMemoryPetriImageRepository(PetriImageRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PetriImage] = {}

    def add(self, petri_image: PetriImage) -> PetriImage:
        self._by_id[petri_image.id] = petri_image
        return petri_image

    def get_by_id(self, petri_image_id: UUID) -> Optional[PetriImage]:
        return self._by_id.get(petri_image_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[PetriImage]:
        return [image for image in self._by_id.values() if image.sample_id == sample_id]


class InMemoryMicroImageRepository(MicroImageRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, MicroImage] = {}

    def add(self, micro_image: MicroImage) -> MicroImage:
        self._by_id[micro_image.id] = micro_image
        return micro_image

    def get_by_id(self, micro_image_id: UUID) -> Optional[MicroImage]:
        return self._by_id.get(micro_image_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[MicroImage]:
        return [image for image in self._by_id.values() if image.sample_id == sample_id]


class InMemoryModelVersionRepository(ModelVersionRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ModelVersion] = {}

    def add(self, model_version: ModelVersion) -> ModelVersion:
        self._by_id[model_version.id] = model_version
        return model_version

    def get_by_id(self, model_version_id: UUID) -> Optional[ModelVersion]:
        return self._by_id.get(model_version_id)

    def list_all(self) -> list[ModelVersion]:
        return sorted(self._by_id.values(), key=lambda model_version: model_version.created_at)


class InMemoryAnalysisRunRepository(AnalysisRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, AnalysisRun] = {}

    def add(self, analysis_run: AnalysisRun) -> AnalysisRun:
        self._by_id[analysis_run.id] = analysis_run
        return analysis_run

    def update(self, analysis_run: AnalysisRun) -> AnalysisRun:
        if analysis_run.id not in self._by_id:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run.id}' does not exist")
        self._by_id[analysis_run.id] = analysis_run
        return analysis_run

    def claim_for_processing(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        run = self._by_id.get(analysis_run_id)
        if run is None or run.status != AnalysisStatus.PENDING:
            return None
        run.mark_processing()
        return run

    def get_by_id(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return self._by_id.get(analysis_run_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[AnalysisRun]:
        return [run for run in self._by_id.values() if run.sample_id == sample_id]

    def list_all(self) -> list[AnalysisRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))


class InMemoryDatasetSnapshotRepository(DatasetSnapshotRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, DatasetSnapshot] = {}

    def add(self, dataset_snapshot: DatasetSnapshot) -> DatasetSnapshot:
        self._by_id[dataset_snapshot.id] = dataset_snapshot
        return dataset_snapshot

    def get_by_id(self, dataset_snapshot_id: UUID) -> Optional[DatasetSnapshot]:
        return self._by_id.get(dataset_snapshot_id)

    def list_all(self) -> list[DatasetSnapshot]:
        return sorted(self._by_id.values(), key=lambda snapshot: (snapshot.created_at, snapshot.id))


class InMemoryDatasetItemRepository(DatasetItemRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, DatasetItem] = {}

    def add_many(self, dataset_items: list[DatasetItem]) -> list[DatasetItem]:
        seen = {(item.dataset_snapshot_id, item.analysis_run_id) for item in self._by_id.values()}
        for item in dataset_items:
            key = (item.dataset_snapshot_id, item.analysis_run_id)
            if key in seen:
                raise ValueError("duplicate analysis_run in dataset snapshot")
            seen.add(key)
            self._by_id[item.id] = item
        return dataset_items

    def list_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> list[DatasetItem]:
        return sorted(
            [item for item in self._by_id.values() if item.dataset_snapshot_id == dataset_snapshot_id],
            key=lambda item: (item.analysis_run_id, item.id),
        )

    def count_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> int:
        return len(
            [
                item
                for item in self._by_id.values()
                if item.dataset_snapshot_id == dataset_snapshot_id and item.included
            ]
        )

    def label_distribution_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for item in self.list_by_dataset_snapshot_id(dataset_snapshot_id):
            if item.included and item.ground_truth_label is not None:
                distribution[item.ground_truth_label.value] = distribution.get(item.ground_truth_label.value, 0) + 1
        return distribution


class InMemoryDatasetReleaseRepository(DatasetReleaseRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, DatasetRelease] = {}

    def add(self, dataset_release: DatasetRelease) -> DatasetRelease:
        self._by_id[dataset_release.id] = dataset_release
        return dataset_release

    def get_by_id(self, dataset_release_id: UUID) -> Optional[DatasetRelease]:
        return self._by_id.get(dataset_release_id)

    def list_by_dataset_snapshot_id(self, dataset_snapshot_id: UUID) -> list[DatasetRelease]:
        return sorted(
            [release for release in self._by_id.values() if release.dataset_snapshot_id == dataset_snapshot_id],
            key=lambda release: (release.created_at, release.id),
        )

    def list_all(self) -> list[DatasetRelease]:
        return sorted(self._by_id.values(), key=lambda release: (release.created_at, release.id))


class InMemoryDatasetSplitItemRepository(DatasetSplitItemRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, DatasetSplitItem] = {}

    def add_many(self, dataset_split_items: list[DatasetSplitItem]) -> list[DatasetSplitItem]:
        seen = {(item.dataset_release_id, item.dataset_item_id) for item in self._by_id.values()}
        for item in dataset_split_items:
            key = (item.dataset_release_id, item.dataset_item_id)
            if key in seen:
                raise ValueError("duplicate dataset_item in dataset release")
            seen.add(key)
            self._by_id[item.id] = item
        return dataset_split_items

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DatasetSplitItem]:
        return sorted(
            [item for item in self._by_id.values() if item.dataset_release_id == dataset_release_id],
            key=lambda item: (item.dataset_item_id, item.id),
        )

    def list_by_split(self, dataset_release_id: UUID, split: DatasetSplit) -> list[DatasetSplitItem]:
        return [item for item in self.list_by_dataset_release_id(dataset_release_id) if item.split == split]


class InMemoryTrainingPreflightRunRepository(TrainingPreflightRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, TrainingPreflightRun] = {}

    def add(self, preflight_run: TrainingPreflightRun) -> TrainingPreflightRun:
        self._by_id[preflight_run.id] = preflight_run
        return preflight_run

    def get_by_id(self, preflight_run_id: UUID) -> Optional[TrainingPreflightRun]:
        return self._by_id.get(preflight_run_id)

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingPreflightRun]:
        return sorted(
            [run for run in self._by_id.values() if run.dataset_release_id == dataset_release_id],
            key=lambda run: (run.created_at, run.id),
        )

    def list_all(self) -> list[TrainingPreflightRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def snapshot_state(self) -> dict[UUID, TrainingPreflightRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, TrainingPreflightRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryTrainingPreflightIssueRepository(TrainingPreflightIssueRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, TrainingPreflightIssue] = {}

    def add_many(self, issues: list[TrainingPreflightIssue]) -> list[TrainingPreflightIssue]:
        for issue in issues:
            self._by_id[issue.id] = issue
        return issues

    def list_by_preflight_run_id(self, preflight_run_id: UUID) -> list[TrainingPreflightIssue]:
        return sorted(
            [issue for issue in self._by_id.values() if issue.preflight_run_id == preflight_run_id],
            key=lambda issue: (issue.created_at, issue.id),
        )

    def snapshot_state(self) -> dict[UUID, TrainingPreflightIssue]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, TrainingPreflightIssue]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryImageDatasetAuditRunRepository(ImageDatasetAuditRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ImageDatasetAuditRun] = {}

    def add(self, audit_run: ImageDatasetAuditRun) -> ImageDatasetAuditRun:
        self._by_id[audit_run.id] = audit_run
        return audit_run

    def get_by_id(self, audit_run_id: UUID) -> Optional[ImageDatasetAuditRun]:
        return self._by_id.get(audit_run_id)

    def list_all(self) -> list[ImageDatasetAuditRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[ImageDatasetAuditRun]:
        return sorted(
            [run for run in self._by_id.values() if run.dataset_release_id == dataset_release_id],
            key=lambda run: (run.created_at, run.id),
        )

    def snapshot_state(self) -> dict[UUID, ImageDatasetAuditRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, ImageDatasetAuditRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryImageDatasetAuditIssueRepository(ImageDatasetAuditIssueRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ImageDatasetAuditIssue] = {}

    def add_many(self, issues: list[ImageDatasetAuditIssue]) -> list[ImageDatasetAuditIssue]:
        for issue in issues:
            self._by_id[issue.id] = issue
        return issues

    def list_by_audit_run_id(self, audit_run_id: UUID) -> list[ImageDatasetAuditIssue]:
        return sorted(
            [issue for issue in self._by_id.values() if issue.audit_run_id == audit_run_id],
            key=lambda issue: (issue.created_at, issue.id),
        )

    def snapshot_state(self) -> dict[UUID, ImageDatasetAuditIssue]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, ImageDatasetAuditIssue]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryImageFeatureExtractionRunRepository(ImageFeatureExtractionRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ImageFeatureExtractionRun] = {}

    def add(self, extraction_run: ImageFeatureExtractionRun) -> ImageFeatureExtractionRun:
        self._by_id[extraction_run.id] = extraction_run
        return extraction_run

    def get_by_id(self, extraction_run_id: UUID) -> Optional[ImageFeatureExtractionRun]:
        return self._by_id.get(extraction_run_id)

    def list_all(self) -> list[ImageFeatureExtractionRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[ImageFeatureExtractionRun]:
        return sorted(
            [run for run in self._by_id.values() if run.dataset_release_id == dataset_release_id],
            key=lambda run: (run.created_at, run.id),
        )

    def list_by_image_audit_run_id(self, image_audit_run_id: UUID) -> list[ImageFeatureExtractionRun]:
        return sorted(
            [run for run in self._by_id.values() if run.image_audit_run_id == image_audit_run_id],
            key=lambda run: (run.created_at, run.id),
        )

    def snapshot_state(self) -> dict[UUID, ImageFeatureExtractionRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, ImageFeatureExtractionRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryImageFeatureVectorRepository(ImageFeatureVectorRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ImageFeatureVector] = {}

    def add_many(self, feature_vectors: list[ImageFeatureVector]) -> list[ImageFeatureVector]:
        for vector in feature_vectors:
            self._by_id[vector.id] = vector
        return feature_vectors

    def list_by_feature_extraction_run_id(self, feature_extraction_run_id: UUID) -> list[ImageFeatureVector]:
        return sorted(
            [v for v in self._by_id.values() if v.feature_extraction_run_id == feature_extraction_run_id],
            key=lambda v: (v.created_at, v.id),
        )

    def list_by_feature_extraction_run_id_and_modality(self, feature_extraction_run_id, modality):
        return [
            v
            for v in self.list_by_feature_extraction_run_id(feature_extraction_run_id)
            if v.modality == modality
        ]

    def list_by_feature_extraction_run_id_and_split(self, feature_extraction_run_id, split):
        return [
            v for v in self.list_by_feature_extraction_run_id(feature_extraction_run_id) if v.split == split
        ]

    def snapshot_state(self) -> dict[UUID, ImageFeatureVector]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, ImageFeatureVector]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryPetriSegmentationRunRepository(PetriSegmentationRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PetriSegmentationRun] = {}

    def add(self, segmentation_run: PetriSegmentationRun) -> PetriSegmentationRun:
        self._by_id[segmentation_run.id] = segmentation_run
        return segmentation_run

    def get_by_id(self, segmentation_run_id: UUID) -> Optional[PetriSegmentationRun]:
        return self._by_id.get(segmentation_run_id)

    def list_all(self) -> list[PetriSegmentationRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriSegmentationRun]:
        return sorted(
            [run for run in self._by_id.values() if run.dataset_release_id == dataset_release_id],
            key=lambda run: (run.created_at, run.id),
        )

    def list_by_image_audit_run_id(self, image_audit_run_id: UUID) -> list[PetriSegmentationRun]:
        return sorted(
            [run for run in self._by_id.values() if run.image_audit_run_id == image_audit_run_id],
            key=lambda run: (run.created_at, run.id),
        )

    def snapshot_state(self) -> dict[UUID, PetriSegmentationRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, PetriSegmentationRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryPetriSegmentationRegionRepository(PetriSegmentationRegionRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PetriSegmentationRegion] = {}

    def add_many(self, regions: list[PetriSegmentationRegion]) -> list[PetriSegmentationRegion]:
        for region in regions:
            self._by_id[region.id] = region
        return regions

    def get_by_id(self, region_id: UUID) -> Optional[PetriSegmentationRegion]:
        return self._by_id.get(region_id)

    def list_by_segmentation_run_id(self, segmentation_run_id: UUID) -> list[PetriSegmentationRegion]:
        return sorted(
            [region for region in self._by_id.values() if region.segmentation_run_id == segmentation_run_id],
            key=lambda region: (region.dataset_split_item_id, region.region_index, region.id),
        )

    def list_by_segmentation_run_id_and_split(
        self, segmentation_run_id: UUID, split: DatasetSplit
    ) -> list[PetriSegmentationRegion]:
        return [
            region
            for region in self.list_by_segmentation_run_id(segmentation_run_id)
            if region.split == split
        ]

    def snapshot_state(self) -> dict[UUID, PetriSegmentationRegion]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, PetriSegmentationRegion]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryPetriRegionReviewRepository(PetriRegionReviewRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PetriRegionReview] = {}

    def add(self, review: PetriRegionReview) -> PetriRegionReview:
        if review.is_final and any(
            existing.petri_segmentation_region_id == review.petri_segmentation_region_id and existing.is_final
            for existing in self._by_id.values()
        ):
            raise DuplicateFinalPetriRegionReviewError(
                f"petri_segmentation_region '{review.petri_segmentation_region_id}' already has a final review"
            )
        self._by_id[review.id] = review
        return review

    def get_by_id(self, review_id: UUID) -> Optional[PetriRegionReview]:
        return self._by_id.get(review_id)

    def list_by_region_id(self, region_id: UUID) -> list[PetriRegionReview]:
        return sorted(
            [review for review in self._by_id.values() if review.petri_segmentation_region_id == region_id],
            key=lambda review: (review.created_at, review.id),
        )

    def list_by_segmentation_run_id(self, segmentation_run_id: UUID) -> list[PetriRegionReview]:
        return sorted(
            [review for review in self._by_id.values() if review.petri_segmentation_run_id == segmentation_run_id],
            key=lambda review: (review.created_at, review.id),
        )

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriRegionReview]:
        return sorted(
            [review for review in self._by_id.values() if review.dataset_release_id == dataset_release_id],
            key=lambda review: (review.created_at, review.id),
        )

    def get_final_by_region_id(self, region_id: UUID) -> Optional[PetriRegionReview]:
        return next(
            (review for review in self.list_by_region_id(region_id) if review.is_final),
            None,
        )

    def unset_final_for_region(self, region_id: UUID) -> int:
        count = 0
        for review in self._by_id.values():
            if review.petri_segmentation_region_id == region_id and review.is_final:
                review.is_final = False
                count += 1
        return count

    def snapshot_state(self) -> dict[UUID, PetriRegionReview]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, PetriRegionReview]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryPetriAnnotationExportRunRepository(PetriAnnotationExportRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PetriAnnotationExportRun] = {}

    def add(self, export_run: PetriAnnotationExportRun) -> PetriAnnotationExportRun:
        self._by_id[export_run.id] = export_run
        return export_run

    def get_by_id(self, export_run_id: UUID) -> Optional[PetriAnnotationExportRun]:
        return self._by_id.get(export_run_id)

    def list_all(self) -> list[PetriAnnotationExportRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriAnnotationExportRun]:
        return sorted(
            [run for run in self._by_id.values() if run.dataset_release_id == dataset_release_id],
            key=lambda run: (run.created_at, run.id),
        )

    def list_by_petri_segmentation_run_id(self, petri_segmentation_run_id: UUID) -> list[PetriAnnotationExportRun]:
        return sorted(
            [run for run in self._by_id.values() if run.petri_segmentation_run_id == petri_segmentation_run_id],
            key=lambda run: (run.created_at, run.id),
        )

    def snapshot_state(self) -> dict[UUID, PetriAnnotationExportRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, PetriAnnotationExportRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryPetriAnnotationExportItemRepository(PetriAnnotationExportItemRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PetriAnnotationExportItem] = {}

    def add_many(self, items: list[PetriAnnotationExportItem]) -> list[PetriAnnotationExportItem]:
        seen = {(item.export_run_id, item.petri_region_review_id) for item in self._by_id.values()}
        for item in items:
            key = (item.export_run_id, item.petri_region_review_id)
            if key in seen:
                raise ValueError("duplicate petri region review in annotation export")
            seen.add(key)
            self._by_id[item.id] = item
        return items

    def list_by_export_run_id(self, export_run_id: UUID) -> list[PetriAnnotationExportItem]:
        return sorted(
            [item for item in self._by_id.values() if item.export_run_id == export_run_id],
            key=lambda item: (item.petri_image_path, item.created_at, item.id),
        )

    def snapshot_state(self) -> dict[UUID, PetriAnnotationExportItem]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, PetriAnnotationExportItem]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryAnnotationBundleRunRepository(AnnotationBundleRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, AnnotationBundleRun] = {}

    def add(self, bundle_run: AnnotationBundleRun) -> AnnotationBundleRun:
        self._by_id[bundle_run.id] = bundle_run
        return bundle_run

    def get_by_id(self, bundle_run_id: UUID) -> Optional[AnnotationBundleRun]:
        return self._by_id.get(bundle_run_id)

    def list_all(self) -> list[AnnotationBundleRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[AnnotationBundleRun]:
        return [
            run
            for run in self.list_all()
            if run.dataset_release_id == dataset_release_id
        ]

    def list_by_petri_annotation_export_run_id(self, export_run_id: UUID) -> list[AnnotationBundleRun]:
        return [
            run
            for run in self.list_all()
            if run.petri_annotation_export_run_id == export_run_id
        ]

    def snapshot_state(self) -> dict[UUID, AnnotationBundleRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, AnnotationBundleRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryAnnotationBundleFileRepository(AnnotationBundleFileRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, AnnotationBundleFile] = {}

    def add_many(self, files: list[AnnotationBundleFile]) -> list[AnnotationBundleFile]:
        for file in files:
            self._by_id[file.id] = file
        return files

    def list_by_bundle_run_id(self, bundle_run_id: UUID) -> list[AnnotationBundleFile]:
        return sorted(
            [file for file in self._by_id.values() if file.bundle_run_id == bundle_run_id],
            key=lambda file: (file.relative_path, file.id),
        )

    def snapshot_state(self) -> dict[UUID, AnnotationBundleFile]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, AnnotationBundleFile]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryAnnotationQualityGateRunRepository(AnnotationQualityGateRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, AnnotationQualityGateRun] = {}

    def add(self, quality_gate_run: AnnotationQualityGateRun) -> AnnotationQualityGateRun:
        self._by_id[quality_gate_run.id] = quality_gate_run
        return quality_gate_run

    def get_by_id(self, quality_gate_run_id: UUID) -> Optional[AnnotationQualityGateRun]:
        return self._by_id.get(quality_gate_run_id)

    def list_all(self) -> list[AnnotationQualityGateRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[AnnotationQualityGateRun]:
        return [run for run in self.list_all() if run.dataset_release_id == dataset_release_id]

    def list_by_annotation_bundle_run_id(self, annotation_bundle_run_id: UUID) -> list[AnnotationQualityGateRun]:
        return [run for run in self.list_all() if run.annotation_bundle_run_id == annotation_bundle_run_id]

    def snapshot_state(self) -> dict[UUID, AnnotationQualityGateRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, AnnotationQualityGateRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryAnnotationQualityGateIssueRepository(AnnotationQualityGateIssueRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, AnnotationQualityGateIssue] = {}

    def add_many(self, issues: list[AnnotationQualityGateIssue]) -> list[AnnotationQualityGateIssue]:
        for issue in issues:
            self._by_id[issue.id] = issue
        return issues

    def list_by_quality_gate_run_id(self, quality_gate_run_id: UUID) -> list[AnnotationQualityGateIssue]:
        return sorted(
            [issue for issue in self._by_id.values() if issue.quality_gate_run_id == quality_gate_run_id],
            key=lambda issue: (issue.severity.value, issue.code, issue.created_at, issue.id),
        )

    def snapshot_state(self) -> dict[UUID, AnnotationQualityGateIssue]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, AnnotationQualityGateIssue]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryDetectionTrainingRunRepository(DetectionTrainingRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, DetectionTrainingRun] = {}

    def add(self, run: DetectionTrainingRun) -> DetectionTrainingRun:
        self._by_id[run.id] = run
        return run

    def get_by_id(self, run_id: UUID) -> Optional[DetectionTrainingRun]:
        return self._by_id.get(run_id)

    def list_all(self) -> list[DetectionTrainingRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[DetectionTrainingRun]:
        return [run for run in self.list_all() if run.dataset_release_id == dataset_release_id]

    def list_by_annotation_bundle_run_id(self, annotation_bundle_run_id: UUID) -> list[DetectionTrainingRun]:
        return [run for run in self.list_all() if run.annotation_bundle_run_id == annotation_bundle_run_id]

    def list_by_annotation_quality_gate_run_id(
        self, annotation_quality_gate_run_id: UUID
    ) -> list[DetectionTrainingRun]:
        return [
            run
            for run in self.list_all()
            if run.annotation_quality_gate_run_id == annotation_quality_gate_run_id
        ]

    def snapshot_state(self) -> dict[UUID, DetectionTrainingRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, DetectionTrainingRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryDetectionTrainingIssueRepository(DetectionTrainingIssueRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, DetectionTrainingIssue] = {}

    def add_many(self, issues: list[DetectionTrainingIssue]) -> list[DetectionTrainingIssue]:
        for issue in issues:
            self._by_id[issue.id] = issue
        return issues

    def list_by_detection_training_run_id(self, detection_training_run_id: UUID) -> list[DetectionTrainingIssue]:
        return sorted(
            [issue for issue in self._by_id.values() if issue.detection_training_run_id == detection_training_run_id],
            key=lambda issue: (issue.severity.value, issue.code, issue.created_at, issue.id),
        )

    def snapshot_state(self) -> dict[UUID, DetectionTrainingIssue]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, DetectionTrainingIssue]) -> None:
        self._by_id = copy.deepcopy(state)


class FailingAddDetectionTrainingIssueRepository(DetectionTrainingIssueRepositoryPort):
    """Delegates reads but always fails when adding new issues."""

    def __init__(self, delegate: DetectionTrainingIssueRepositoryPort) -> None:
        self._delegate = delegate

    def add_many(self, issues: list[DetectionTrainingIssue]) -> list[DetectionTrainingIssue]:
        raise RuntimeError("simulated detection training issue insert failure")

    def list_by_detection_training_run_id(self, detection_training_run_id: UUID) -> list[DetectionTrainingIssue]:
        return self._delegate.list_by_detection_training_run_id(detection_training_run_id)

    def snapshot_state(self):
        return self._delegate.snapshot_state()

    def restore_state(self, state) -> None:
        self._delegate.restore_state(state)


class InMemoryTrainingRunRepository(TrainingRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, TrainingRun] = {}

    def add(self, training_run: TrainingRun) -> TrainingRun:
        self._by_id[training_run.id] = training_run
        return training_run

    def get_by_id(self, training_run_id: UUID) -> Optional[TrainingRun]:
        return self._by_id.get(training_run_id)

    def list_all(self) -> list[TrainingRun]:
        return sorted(self._by_id.values(), key=lambda run: (run.created_at, run.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingRun]:
        return sorted(
            [run for run in self._by_id.values() if run.dataset_release_id == dataset_release_id],
            key=lambda run: (run.created_at, run.id),
        )

    def list_by_preflight_run_id(self, preflight_run_id: UUID) -> list[TrainingRun]:
        return sorted(
            [run for run in self._by_id.values() if run.preflight_run_id == preflight_run_id],
            key=lambda run: (run.created_at, run.id),
        )

    def snapshot_state(self) -> dict[UUID, TrainingRun]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, TrainingRun]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryTrainingRunComparisonRepository(TrainingRunComparisonRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, TrainingRunComparison] = {}

    def add(self, comparison: TrainingRunComparison) -> TrainingRunComparison:
        self._by_id[comparison.id] = comparison
        return comparison

    def get_by_id(self, comparison_id: UUID) -> Optional[TrainingRunComparison]:
        return self._by_id.get(comparison_id)

    def list_all(self) -> list[TrainingRunComparison]:
        return sorted(self._by_id.values(), key=lambda comparison: (comparison.created_at, comparison.id))

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[TrainingRunComparison]:
        return [
            comparison
            for comparison in self.list_all()
            if comparison.dataset_release_id == dataset_release_id
        ]

    def snapshot_state(self) -> dict[UUID, TrainingRunComparison]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, TrainingRunComparison]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryTrainingRunComparisonEntryRepository(TrainingRunComparisonEntryRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, TrainingRunComparisonEntry] = {}

    def add_many(self, entries: list[TrainingRunComparisonEntry]) -> list[TrainingRunComparisonEntry]:
        seen = {
            (entry.comparison_id, entry.training_run_id)
            for entry in self._by_id.values()
        }
        for entry in entries:
            key = (entry.comparison_id, entry.training_run_id)
            if key in seen:
                raise ValueError("duplicate training_run in comparison")
            seen.add(key)
            self._by_id[entry.id] = entry
        return entries

    def list_by_comparison_id(self, comparison_id: UUID) -> list[TrainingRunComparisonEntry]:
        return sorted(
            [entry for entry in self._by_id.values() if entry.comparison_id == comparison_id],
            key=lambda entry: (entry.rank or 999999, entry.training_run_id, entry.id),
        )

    def snapshot_state(self) -> dict[UUID, TrainingRunComparisonEntry]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, TrainingRunComparisonEntry]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryTrainingPredictionRepository(TrainingPredictionRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, TrainingPrediction] = {}

    def add_many(self, predictions: list[TrainingPrediction]) -> list[TrainingPrediction]:
        seen = {
            (prediction.training_run_id, prediction.dataset_split_item_id)
            for prediction in self._by_id.values()
        }
        for prediction in predictions:
            key = (prediction.training_run_id, prediction.dataset_split_item_id)
            if key in seen:
                raise ValueError("duplicate dataset_split_item in training run")
            seen.add(key)
            self._by_id[prediction.id] = prediction
        return predictions

    def list_by_training_run_id(self, training_run_id: UUID) -> list[TrainingPrediction]:
        return sorted(
            [prediction for prediction in self._by_id.values() if prediction.training_run_id == training_run_id],
            key=lambda prediction: (prediction.split.value, prediction.dataset_split_item_id, prediction.id),
        )

    def list_by_training_run_id_and_split(
        self, training_run_id: UUID, split: DatasetSplit
    ) -> list[TrainingPrediction]:
        return [
            prediction
            for prediction in self.list_by_training_run_id(training_run_id)
            if prediction.split == split
        ]

    def snapshot_state(self) -> dict[UUID, TrainingPrediction]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, TrainingPrediction]) -> None:
        self._by_id = copy.deepcopy(state)


class InMemoryPredictionRepository(PredictionRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, Prediction] = {}

    def add(self, prediction: Prediction) -> Prediction:
        if any(existing.analysis_run_id == prediction.analysis_run_id for existing in self._by_id.values()):
            raise DuplicatePredictionError(
                f"analysis_run '{prediction.analysis_run_id}' already has a prediction"
            )
        self._by_id[prediction.id] = prediction
        return prediction

    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[Prediction]:
        return next((p for p in self._by_id.values() if p.analysis_run_id == analysis_run_id), None)

    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        return self._by_id.get(prediction_id)


class InMemoryHumanReviewRepository(HumanReviewRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[UUID, HumanReview] = {}

    def add(self, human_review: HumanReview) -> HumanReview:
        if human_review.is_final and any(
            review.analysis_run_id == human_review.analysis_run_id and review.is_final
            for review in self._by_id.values()
        ):
            raise DuplicateFinalHumanReviewError(
                f"analysis_run '{human_review.analysis_run_id}' already has a final human review"
            )
        self._by_id[human_review.id] = human_review
        return human_review

    def get_by_id(self, human_review_id: UUID) -> Optional[HumanReview]:
        return self._by_id.get(human_review_id)

    def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[HumanReview]:
        return sorted(
            [review for review in self._by_id.values() if review.analysis_run_id == analysis_run_id],
            key=lambda review: (review.created_at, review.id),
        )

    def get_final_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[HumanReview]:
        return next(
            (
                review
                for review in self.list_by_analysis_run_id(analysis_run_id)
                if review.is_final
            ),
            None,
        )

    def unset_final_reviews_for_analysis_run(self, analysis_run_id: UUID) -> int:
        count = 0
        for review in self._by_id.values():
            if review.analysis_run_id == analysis_run_id and review.is_final:
                review.is_final = False
                count += 1
        return count

    def snapshot_state(self) -> dict[UUID, HumanReview]:
        return copy.deepcopy(self._by_id)

    def restore_state(self, state: dict[UUID, HumanReview]) -> None:
        self._by_id = copy.deepcopy(state)


class FakeUnitOfWork(UnitOfWorkPort):
    """In-memory stand-in for `UnitOfWorkPort`.

    Exposes the *same* repository instances passed in (rather than
    snapshot/rollback semantics): good enough to unit-test
    `ProcessAnalysisRunUseCase`'s call sequence and final state without a
    database. Real cross-repository atomicity (a failed write leaving
    nothing behind) is verified separately in
    tests/integration/db/ against the real `SqlAlchemyUnitOfWork` and
    SQLite, where an actual transaction exists to roll back.
    """

    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
        human_review_repository: Optional[HumanReviewRepositoryPort] = None,
        dataset_snapshot_repository: Optional[DatasetSnapshotRepositoryPort] = None,
        dataset_item_repository: Optional[DatasetItemRepositoryPort] = None,
        dataset_release_repository: Optional[DatasetReleaseRepositoryPort] = None,
        dataset_split_item_repository: Optional[DatasetSplitItemRepositoryPort] = None,
        training_preflight_run_repository: Optional[TrainingPreflightRunRepositoryPort] = None,
        training_preflight_issue_repository: Optional[TrainingPreflightIssueRepositoryPort] = None,
        training_run_repository: Optional[TrainingRunRepositoryPort] = None,
        training_prediction_repository: Optional[TrainingPredictionRepositoryPort] = None,
        training_run_comparison_repository: Optional[TrainingRunComparisonRepositoryPort] = None,
        training_run_comparison_entry_repository: Optional[TrainingRunComparisonEntryRepositoryPort] = None,
        image_dataset_audit_run_repository: Optional[ImageDatasetAuditRunRepositoryPort] = None,
        image_dataset_audit_issue_repository: Optional[ImageDatasetAuditIssueRepositoryPort] = None,
        image_feature_extraction_run_repository: Optional[ImageFeatureExtractionRunRepositoryPort] = None,
        image_feature_vector_repository: Optional[ImageFeatureVectorRepositoryPort] = None,
        petri_segmentation_run_repository: Optional[PetriSegmentationRunRepositoryPort] = None,
        petri_segmentation_region_repository: Optional[PetriSegmentationRegionRepositoryPort] = None,
        petri_region_review_repository: Optional[PetriRegionReviewRepositoryPort] = None,
        petri_annotation_export_run_repository: Optional[PetriAnnotationExportRunRepositoryPort] = None,
        petri_annotation_export_item_repository: Optional[PetriAnnotationExportItemRepositoryPort] = None,
        annotation_bundle_run_repository: Optional[AnnotationBundleRunRepositoryPort] = None,
        annotation_bundle_file_repository: Optional[AnnotationBundleFileRepositoryPort] = None,
        annotation_quality_gate_run_repository: Optional[AnnotationQualityGateRunRepositoryPort] = None,
        annotation_quality_gate_issue_repository: Optional[AnnotationQualityGateIssueRepositoryPort] = None,
        detection_training_run_repository: Optional["DetectionTrainingRunRepositoryPort"] = None,
        detection_training_issue_repository: Optional["DetectionTrainingIssueRepositoryPort"] = None,
    ) -> None:
        self.analysis_run_repository = analysis_run_repository
        self.prediction_repository = prediction_repository
        self.human_review_repository = human_review_repository
        self.dataset_snapshot_repository = dataset_snapshot_repository
        self.dataset_item_repository = dataset_item_repository
        self.dataset_release_repository = dataset_release_repository
        self.dataset_split_item_repository = dataset_split_item_repository
        self.training_preflight_run_repository = training_preflight_run_repository
        self.training_preflight_issue_repository = training_preflight_issue_repository
        self.training_run_repository = training_run_repository
        self.training_prediction_repository = training_prediction_repository
        self.training_run_comparison_repository = training_run_comparison_repository
        self.training_run_comparison_entry_repository = training_run_comparison_entry_repository
        self.image_dataset_audit_run_repository = image_dataset_audit_run_repository
        self.image_dataset_audit_issue_repository = image_dataset_audit_issue_repository
        self.image_feature_extraction_run_repository = image_feature_extraction_run_repository
        self.image_feature_vector_repository = image_feature_vector_repository
        self.petri_segmentation_run_repository = petri_segmentation_run_repository
        self.petri_segmentation_region_repository = petri_segmentation_region_repository
        self.petri_region_review_repository = petri_region_review_repository
        self.petri_annotation_export_run_repository = petri_annotation_export_run_repository
        self.petri_annotation_export_item_repository = petri_annotation_export_item_repository
        self.annotation_bundle_run_repository = annotation_bundle_run_repository
        self.annotation_bundle_file_repository = annotation_bundle_file_repository
        self.annotation_quality_gate_run_repository = annotation_quality_gate_run_repository
        self.annotation_quality_gate_issue_repository = annotation_quality_gate_issue_repository
        self.detection_training_run_repository = detection_training_run_repository
        self.detection_training_issue_repository = detection_training_issue_repository
        self.entered = False
        self.committed = False
        self._human_review_snapshot = None
        self._training_preflight_run_snapshot = None
        self._training_preflight_issue_snapshot = None
        self._training_run_snapshot = None
        self._training_prediction_snapshot = None
        self._training_run_comparison_snapshot = None
        self._training_run_comparison_entry_snapshot = None
        self._image_dataset_audit_run_snapshot = None
        self._image_dataset_audit_issue_snapshot = None
        self._image_feature_extraction_run_snapshot = None
        self._image_feature_vector_snapshot = None
        self._petri_segmentation_run_snapshot = None
        self._petri_segmentation_region_snapshot = None
        self._petri_region_review_snapshot = None
        self._petri_annotation_export_run_snapshot = None
        self._petri_annotation_export_item_snapshot = None
        self._annotation_bundle_run_snapshot = None
        self._annotation_bundle_file_snapshot = None
        self._annotation_quality_gate_run_snapshot = None
        self._annotation_quality_gate_issue_snapshot = None
        self._detection_training_run_snapshot = None
        self._detection_training_issue_snapshot = None

    def __enter__(self) -> "FakeUnitOfWork":
        self.entered = True
        if hasattr(self.human_review_repository, "snapshot_state"):
            self._human_review_snapshot = self.human_review_repository.snapshot_state()
        if hasattr(self.training_preflight_run_repository, "snapshot_state"):
            self._training_preflight_run_snapshot = self.training_preflight_run_repository.snapshot_state()
        if hasattr(self.training_preflight_issue_repository, "snapshot_state"):
            self._training_preflight_issue_snapshot = self.training_preflight_issue_repository.snapshot_state()
        if hasattr(self.training_run_repository, "snapshot_state"):
            self._training_run_snapshot = self.training_run_repository.snapshot_state()
        if hasattr(self.training_prediction_repository, "snapshot_state"):
            self._training_prediction_snapshot = self.training_prediction_repository.snapshot_state()
        if hasattr(self.training_run_comparison_repository, "snapshot_state"):
            self._training_run_comparison_snapshot = self.training_run_comparison_repository.snapshot_state()
        if hasattr(self.training_run_comparison_entry_repository, "snapshot_state"):
            self._training_run_comparison_entry_snapshot = (
                self.training_run_comparison_entry_repository.snapshot_state()
            )
        if hasattr(self.image_dataset_audit_run_repository, "snapshot_state"):
            self._image_dataset_audit_run_snapshot = self.image_dataset_audit_run_repository.snapshot_state()
        if hasattr(self.image_dataset_audit_issue_repository, "snapshot_state"):
            self._image_dataset_audit_issue_snapshot = self.image_dataset_audit_issue_repository.snapshot_state()
        if hasattr(self.image_feature_extraction_run_repository, "snapshot_state"):
            self._image_feature_extraction_run_snapshot = (
                self.image_feature_extraction_run_repository.snapshot_state()
            )
        if hasattr(self.image_feature_vector_repository, "snapshot_state"):
            self._image_feature_vector_snapshot = self.image_feature_vector_repository.snapshot_state()
        if hasattr(self.petri_segmentation_run_repository, "snapshot_state"):
            self._petri_segmentation_run_snapshot = self.petri_segmentation_run_repository.snapshot_state()
        if hasattr(self.petri_segmentation_region_repository, "snapshot_state"):
            self._petri_segmentation_region_snapshot = self.petri_segmentation_region_repository.snapshot_state()
        if hasattr(self.petri_region_review_repository, "snapshot_state"):
            self._petri_region_review_snapshot = self.petri_region_review_repository.snapshot_state()
        if hasattr(self.petri_annotation_export_run_repository, "snapshot_state"):
            self._petri_annotation_export_run_snapshot = (
                self.petri_annotation_export_run_repository.snapshot_state()
            )
        if hasattr(self.petri_annotation_export_item_repository, "snapshot_state"):
            self._petri_annotation_export_item_snapshot = (
                self.petri_annotation_export_item_repository.snapshot_state()
            )
        if hasattr(self.annotation_bundle_run_repository, "snapshot_state"):
            self._annotation_bundle_run_snapshot = self.annotation_bundle_run_repository.snapshot_state()
        if hasattr(self.annotation_bundle_file_repository, "snapshot_state"):
            self._annotation_bundle_file_snapshot = self.annotation_bundle_file_repository.snapshot_state()
        if hasattr(self.annotation_quality_gate_run_repository, "snapshot_state"):
            self._annotation_quality_gate_run_snapshot = self.annotation_quality_gate_run_repository.snapshot_state()
        if hasattr(self.annotation_quality_gate_issue_repository, "snapshot_state"):
            self._annotation_quality_gate_issue_snapshot = (
                self.annotation_quality_gate_issue_repository.snapshot_state()
            )
        if hasattr(self.detection_training_run_repository, "snapshot_state"):
            self._detection_training_run_snapshot = self.detection_training_run_repository.snapshot_state()
        if hasattr(self.detection_training_issue_repository, "snapshot_state"):
            self._detection_training_issue_snapshot = self.detection_training_issue_repository.snapshot_state()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if exc_type is not None and self._human_review_snapshot is not None:
            self.human_review_repository.restore_state(self._human_review_snapshot)
        if exc_type is not None and self._training_preflight_run_snapshot is not None:
            self.training_preflight_run_repository.restore_state(self._training_preflight_run_snapshot)
        if exc_type is not None and self._training_preflight_issue_snapshot is not None:
            self.training_preflight_issue_repository.restore_state(self._training_preflight_issue_snapshot)
        if exc_type is not None and self._training_run_snapshot is not None:
            self.training_run_repository.restore_state(self._training_run_snapshot)
        if exc_type is not None and self._training_prediction_snapshot is not None:
            self.training_prediction_repository.restore_state(self._training_prediction_snapshot)
        if exc_type is not None and self._training_run_comparison_snapshot is not None:
            self.training_run_comparison_repository.restore_state(self._training_run_comparison_snapshot)
        if exc_type is not None and self._training_run_comparison_entry_snapshot is not None:
            self.training_run_comparison_entry_repository.restore_state(
                self._training_run_comparison_entry_snapshot
            )
        if exc_type is not None and self._image_dataset_audit_run_snapshot is not None:
            self.image_dataset_audit_run_repository.restore_state(self._image_dataset_audit_run_snapshot)
        if exc_type is not None and self._image_dataset_audit_issue_snapshot is not None:
            self.image_dataset_audit_issue_repository.restore_state(self._image_dataset_audit_issue_snapshot)
        if exc_type is not None and self._image_feature_extraction_run_snapshot is not None:
            self.image_feature_extraction_run_repository.restore_state(self._image_feature_extraction_run_snapshot)
        if exc_type is not None and self._image_feature_vector_snapshot is not None:
            self.image_feature_vector_repository.restore_state(self._image_feature_vector_snapshot)
        if exc_type is not None and self._petri_segmentation_run_snapshot is not None:
            self.petri_segmentation_run_repository.restore_state(self._petri_segmentation_run_snapshot)
        if exc_type is not None and self._petri_segmentation_region_snapshot is not None:
            self.petri_segmentation_region_repository.restore_state(self._petri_segmentation_region_snapshot)
        if exc_type is not None and self._petri_region_review_snapshot is not None:
            self.petri_region_review_repository.restore_state(self._petri_region_review_snapshot)
        if exc_type is not None and self._petri_annotation_export_run_snapshot is not None:
            self.petri_annotation_export_run_repository.restore_state(self._petri_annotation_export_run_snapshot)
        if exc_type is not None and self._petri_annotation_export_item_snapshot is not None:
            self.petri_annotation_export_item_repository.restore_state(self._petri_annotation_export_item_snapshot)
        if exc_type is not None and self._annotation_bundle_run_snapshot is not None:
            self.annotation_bundle_run_repository.restore_state(self._annotation_bundle_run_snapshot)
        if exc_type is not None and self._annotation_bundle_file_snapshot is not None:
            self.annotation_bundle_file_repository.restore_state(self._annotation_bundle_file_snapshot)
        if exc_type is not None and self._annotation_quality_gate_run_snapshot is not None:
            self.annotation_quality_gate_run_repository.restore_state(self._annotation_quality_gate_run_snapshot)
        if exc_type is not None and self._annotation_quality_gate_issue_snapshot is not None:
            self.annotation_quality_gate_issue_repository.restore_state(self._annotation_quality_gate_issue_snapshot)
        if exc_type is not None and self._detection_training_run_snapshot is not None:
            self.detection_training_run_repository.restore_state(self._detection_training_run_snapshot)
        if exc_type is not None and self._detection_training_issue_snapshot is not None:
            self.detection_training_issue_repository.restore_state(self._detection_training_issue_snapshot)
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class FakeInferenceEngine(InferenceEnginePort):
    """Returns a fixed, caller-configured InferenceOutput — no hashing, no
    real logic — so use-case tests can control the scenario precisely.
    """

    def __init__(self, output: InferenceOutput) -> None:
        self._output = output

    def process(self, **_kwargs) -> InferenceOutput:
        return self._output


class FailingInferenceEngine(InferenceEnginePort):
    """Always raises, to test ProcessAnalysisRunUseCase's failure handling."""

    def process(self, **_kwargs) -> InferenceOutput:
        raise RuntimeError("simulated inference engine crash")


class FailingAddPredictionRepository(PredictionRepositoryPort):
    """Always raises a generic error on add() — simulates a Prediction
    insert failing for a reason *other* than the duplicate-key constraint
    (e.g. a transient DB error), which ProcessAnalysisRunUseCase must still
    recover from by marking the AnalysisRun `failed`.
    """

    def add(self, prediction: Prediction) -> Prediction:
        raise RuntimeError("simulated prediction insert failure")

    def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[Prediction]:
        return None

    def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        return None


class FailingAddHumanReviewRepository(HumanReviewRepositoryPort):
    """Delegates reads/updates but always fails when adding a new review."""

    def __init__(self, delegate: HumanReviewRepositoryPort) -> None:
        self._delegate = delegate

    def add(self, human_review: HumanReview) -> HumanReview:
        raise RuntimeError("simulated human review insert failure")

    def get_by_id(self, human_review_id: UUID) -> Optional[HumanReview]:
        return self._delegate.get_by_id(human_review_id)

    def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[HumanReview]:
        return self._delegate.list_by_analysis_run_id(analysis_run_id)

    def get_final_by_analysis_run_id(self, analysis_run_id: UUID) -> Optional[HumanReview]:
        return self._delegate.get_final_by_analysis_run_id(analysis_run_id)

    def unset_final_reviews_for_analysis_run(self, analysis_run_id: UUID) -> int:
        return self._delegate.unset_final_reviews_for_analysis_run(analysis_run_id)

    def snapshot_state(self):
        return self._delegate.snapshot_state()

    def restore_state(self, state) -> None:
        self._delegate.restore_state(state)


class FailingAddPetriRegionReviewRepository(PetriRegionReviewRepositoryPort):
    """Delegates reads/updates but always fails when adding a new review."""

    def __init__(self, delegate: PetriRegionReviewRepositoryPort) -> None:
        self._delegate = delegate

    def add(self, review: PetriRegionReview) -> PetriRegionReview:
        raise RuntimeError("simulated petri region review insert failure")

    def get_by_id(self, review_id: UUID) -> Optional[PetriRegionReview]:
        return self._delegate.get_by_id(review_id)

    def list_by_region_id(self, region_id: UUID) -> list[PetriRegionReview]:
        return self._delegate.list_by_region_id(region_id)

    def list_by_segmentation_run_id(self, segmentation_run_id: UUID) -> list[PetriRegionReview]:
        return self._delegate.list_by_segmentation_run_id(segmentation_run_id)

    def list_by_dataset_release_id(self, dataset_release_id: UUID) -> list[PetriRegionReview]:
        return self._delegate.list_by_dataset_release_id(dataset_release_id)

    def get_final_by_region_id(self, region_id: UUID) -> Optional[PetriRegionReview]:
        return self._delegate.get_final_by_region_id(region_id)

    def unset_final_for_region(self, region_id: UUID) -> int:
        return self._delegate.unset_final_for_region(region_id)

    def snapshot_state(self):
        return self._delegate.snapshot_state()

    def restore_state(self, state) -> None:
        self._delegate.restore_state(state)


class UpdateFailingNTimesAnalysisRunRepository(AnalysisRunRepositoryPort):
    """Wraps a real AnalysisRunRepositoryPort; the first `fail_call_count`
    calls to `update()` raise, after which it delegates normally.

    Lets tests simulate "the final status write fails" (fail_call_count=1,
    so the recovery `mark_failed` write that follows succeeds) or "even the
    recovery write fails" (fail_call_count=2 or more).
    """

    def __init__(self, delegate: AnalysisRunRepositoryPort, fail_call_count: int = 1) -> None:
        self._delegate = delegate
        self._fail_call_count = fail_call_count
        self._update_calls = 0

    def add(self, analysis_run: AnalysisRun) -> AnalysisRun:
        return self._delegate.add(analysis_run)

    def update(self, analysis_run: AnalysisRun) -> AnalysisRun:
        self._update_calls += 1
        if self._update_calls <= self._fail_call_count:
            raise RuntimeError(f"simulated database failure on update() call #{self._update_calls}")
        return self._delegate.update(analysis_run)

    def claim_for_processing(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return self._delegate.claim_for_processing(analysis_run_id)

    def get_by_id(self, analysis_run_id: UUID) -> Optional[AnalysisRun]:
        return self._delegate.get_by_id(analysis_run_id)

    def list_by_sample_id(self, sample_id: UUID) -> list[AnalysisRun]:
        return self._delegate.list_by_sample_id(sample_id)

    def list_all(self) -> list[AnalysisRun]:
        return self._delegate.list_all()


class InMemoryImageStorage(ImageStoragePort):
    """Keeps saved bytes in a dict instead of writing to disk."""

    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}
        self.deleted_paths: list[str] = []

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        path = f"memory://{category.value}/{len(self.saved)}-{original_file_name}"
        self.saved[path] = content
        return path

    def delete(self, path: str) -> None:
        self.deleted_paths.append(path)
        self.saved.pop(path, None)


class AlwaysFailingImageStorage(ImageStoragePort):
    """Fails every save/delete call, to test the "cleanup also fails" path."""

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        raise RuntimeError("simulated storage save failure")

    def delete(self, path: str) -> None:
        raise RuntimeError("simulated storage delete failure")


class FailingDeleteImageStorage(ImageStoragePort):
    """Saves successfully but always fails to delete."""

    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    def save(self, *, category: ImageCategory, original_file_name: str, content: bytes) -> str:
        path = f"memory://{category.value}/{len(self.saved)}-{original_file_name}"
        self.saved[path] = content
        return path

    def delete(self, path: str) -> None:
        raise RuntimeError("simulated storage delete failure")


class FailingPetriImageRepository(PetriImageRepositoryPort):
    """Always raises on add(), to test the orphan-file compensation path."""

    def add(self, petri_image: PetriImage) -> PetriImage:
        raise RuntimeError("simulated database failure")

    def get_by_id(self, petri_image_id: UUID) -> Optional[PetriImage]:
        return None

    def list_by_sample_id(self, sample_id: UUID) -> list[PetriImage]:
        return []


class FailingMicroImageRepository(MicroImageRepositoryPort):
    """Always raises on add(), to test the orphan-file compensation path."""

    def add(self, micro_image: MicroImage) -> MicroImage:
        raise RuntimeError("simulated database failure")

    def get_by_id(self, micro_image_id: UUID) -> Optional[MicroImage]:
        return None

    def list_by_sample_id(self, sample_id: UUID) -> list[MicroImage]:
        return []
