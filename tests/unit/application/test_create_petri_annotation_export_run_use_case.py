from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from PIL import Image

from blueberry_microid.application.dto.petri_annotation_export_dto import (
    CreatePetriAnnotationExportRunRequest,
    PetriAnnotationExportConfigDTO,
)
from blueberry_microid.application.exceptions import PetriAnnotationExportNotAllowedError
from blueberry_microid.application.services.petri_annotation_exporter import PetriAnnotationExporter
from blueberry_microid.application.use_cases.petri_annotation_export.create_petri_annotation_export_run import (
    CreatePetriAnnotationExportRunUseCase,
)
from blueberry_microid.application.use_cases.petri_annotation_export.list_petri_annotation_export_runs import (
    ListPetriAnnotationExportRunsUseCase,
)
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat
from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision
from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryDatasetReleaseRepository,
    InMemoryPetriAnnotationExportItemRepository,
    InMemoryPetriAnnotationExportRunRepository,
    InMemoryPetriRegionReviewRepository,
    InMemoryPetriSegmentationRegionRepository,
    InMemoryPetriSegmentationRunRepository,
)


class FailingPetriAnnotationExportItemRepository(InMemoryPetriAnnotationExportItemRepository):
    def add_many(self, items):
        raise RuntimeError("simulated annotation export item insert failure")


def _release():
    return DatasetRelease(
        dataset_snapshot_id=uuid4(),
        name="release",
        version="v1",
        split_strategy=SplitStrategy.BY_SAMPLE,
        random_seed=7,
        train_ratio=0.7,
        validation_ratio=0.2,
        test_ratio=0.1,
        item_count=1,
    )


def _segmentation_run(release_id: UUID):
    return PetriSegmentationRun(
        dataset_release_id=release_id,
        status=PetriSegmentationStatus.COMPLETED,
        is_completed=True,
        config={},
        total_items=1,
        processed_petri_images=1,
        failed_petri_images=0,
        total_regions_detected=1,
        summary={},
        started_at=datetime.now(timezone.utc),
    )


def _region(run, image_path):
    return PetriSegmentationRegion(
        segmentation_run_id=run.id,
        dataset_release_id=run.dataset_release_id,
        dataset_item_id=uuid4(),
        dataset_split_item_id=uuid4(),
        split=DatasetSplit.TRAIN,
        petri_image_path=str(image_path),
        region_index=0,
        area_px=100,
        centroid_x=10,
        centroid_y=10,
        bbox_x=1,
        bbox_y=2,
        bbox_width=10,
        bbox_height=12,
    )


def _review(region, *, final=True, decision=PetriRegionReviewDecision.CANDIDATE_VALID):
    return PetriRegionReview(
        petri_segmentation_region_id=region.id,
        petri_segmentation_run_id=region.segmentation_run_id,
        dataset_release_id=region.dataset_release_id,
        dataset_item_id=region.dataset_item_id,
        dataset_split_item_id=region.dataset_split_item_id,
        decision=decision,
        is_final=final,
    )


def _build(tmp_path, *, item_repo=None):
    image_path = tmp_path / "petri.png"
    Image.new("RGB", (50, 50), "white").save(image_path)
    release_repo = InMemoryDatasetReleaseRepository()
    run_repo = InMemoryPetriSegmentationRunRepository()
    region_repo = InMemoryPetriSegmentationRegionRepository()
    review_repo = InMemoryPetriRegionReviewRepository()
    export_run_repo = InMemoryPetriAnnotationExportRunRepository()
    export_item_repo = item_repo or InMemoryPetriAnnotationExportItemRepository()
    release = release_repo.add(_release())
    run = run_repo.add(_segmentation_run(release.id))
    region = region_repo.add_many([_region(run, image_path)])[0]
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        petri_annotation_export_run_repository=export_run_repo,
        petri_annotation_export_item_repository=export_item_repo,
    )
    use_case = CreatePetriAnnotationExportRunUseCase(
        release_repo,
        run_repo,
        region_repo,
        review_repo,
        PetriAnnotationExporter(),
        uow,
    )
    return use_case, release, run, region, review_repo, export_run_repo, export_item_repo


def test_creates_completed_export_run_and_items(tmp_path):
    use_case, release, run, region, review_repo, export_run_repo, export_item_repo = _build(tmp_path)
    review_repo.add(_review(region))

    result = use_case.execute(CreatePetriAnnotationExportRunRequest(release.id, run.id))

    assert result.status.value == "completed"
    assert result.exported_annotation_count == 1
    assert len(export_run_repo.list_all()) == 1
    assert len(export_item_repo.list_by_export_run_id(result.id)) == 1
    assert result.output_manifest["annotations"][0]["label"] == "candidate_region"


def test_rejects_segmentation_run_from_other_release(tmp_path):
    use_case, _, run, *_ = _build(tmp_path)
    other_release = use_case._dataset_release_repository.add(_release())

    with pytest.raises(PetriAnnotationExportNotAllowedError):
        use_case.execute(CreatePetriAnnotationExportRunRequest(other_release.id, run.id))


def test_handles_zero_exportable_annotations(tmp_path):
    use_case, release, run, region, review_repo, _, export_item_repo = _build(tmp_path)
    review_repo.add(_review(region, decision=PetriRegionReviewDecision.CANDIDATE_FALSE_POSITIVE))

    result = use_case.execute(CreatePetriAnnotationExportRunRequest(release.id, run.id))

    assert result.status.value == "completed"
    assert result.exported_annotation_count == 0
    assert export_item_repo.list_by_export_run_id(result.id) == []


def test_uses_only_final_reviews(tmp_path):
    use_case, release, run, region, review_repo, _, _ = _build(tmp_path)
    review_repo.add(_review(region, final=False))

    result = use_case.execute(CreatePetriAnnotationExportRunRequest(release.id, run.id))

    assert result.exported_annotation_count == 0


def test_yolo_export_persists_manifest(tmp_path):
    use_case, release, run, region, review_repo, _, _ = _build(tmp_path)
    review_repo.add(_review(region))

    result = use_case.execute(
        CreatePetriAnnotationExportRunRequest(
            release.id,
            run.id,
            config=PetriAnnotationExportConfigDTO(export_format=PetriAnnotationExportFormat.YOLO_TXT),
        )
    )

    assert result.output_manifest["format"] == "yolo_txt"
    assert result.output_manifest["labels"][0]["lines"]


def test_does_not_modify_review_or_region(tmp_path):
    use_case, release, run, region, review_repo, _, _ = _build(tmp_path)
    review = review_repo.add(_review(region))

    use_case.execute(CreatePetriAnnotationExportRunRequest(release.id, run.id))

    assert review_repo.get_by_id(review.id) == review
    assert use_case._region_repository.get_by_id(region.id) == region


def test_rolls_back_run_when_item_persistence_fails(tmp_path):
    failing_item_repo = FailingPetriAnnotationExportItemRepository()
    use_case, release, run, region, review_repo, export_run_repo, _ = _build(tmp_path, item_repo=failing_item_repo)
    review_repo.add(_review(region))

    with pytest.raises(RuntimeError, match="simulated annotation export item insert failure"):
        use_case.execute(CreatePetriAnnotationExportRunRequest(release.id, run.id))

    assert export_run_repo.list_all() == []


def test_lists_exports_by_release_and_segmentation(tmp_path):
    use_case, release, run, region, review_repo, export_run_repo, _ = _build(tmp_path)
    review_repo.add(_review(region))
    use_case.execute(CreatePetriAnnotationExportRunRequest(release.id, run.id))

    list_use_case = ListPetriAnnotationExportRunsUseCase(export_run_repo)

    assert len(list_use_case.execute(dataset_release_id=release.id)) == 1
    assert len(list_use_case.execute(petri_segmentation_run_id=run.id)) == 1
