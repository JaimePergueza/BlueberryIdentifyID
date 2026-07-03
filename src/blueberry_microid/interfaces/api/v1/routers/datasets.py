from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.dataset_dto import CreateDatasetReleaseRequest, CreateDatasetSnapshotRequest
from blueberry_microid.application.services.dataset_manifest_exporter import DatasetManifestExporter
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.application.use_cases.dataset.create_dataset_release import CreateDatasetReleaseUseCase
from blueberry_microid.application.use_cases.dataset.create_dataset_snapshot import CreateDatasetSnapshotUseCase
from blueberry_microid.application.use_cases.dataset.get_dataset_release import GetDatasetReleaseUseCase
from blueberry_microid.application.use_cases.dataset.get_dataset_snapshot import GetDatasetSnapshotUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_items import ListDatasetItemsUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_releases import ListDatasetReleasesUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_snapshots import ListDatasetSnapshotsUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_split_items import ListDatasetSplitItemsUseCase
from blueberry_microid.application.use_cases.ml_preflight.list_training_preflight_runs import (
    ListTrainingPreflightRunsUseCase,
)
from blueberry_microid.application.use_cases.training.list_training_runs import ListTrainingRunsUseCase
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_dataset_release_use_case,
    get_create_dataset_snapshot_use_case,
    get_dataset_manifest_exporter,
    get_dataset_release_manifest_exporter,
    get_get_dataset_release_use_case,
    get_get_dataset_snapshot_use_case,
    get_list_dataset_items_use_case,
    get_list_dataset_releases_use_case,
    get_list_dataset_snapshots_use_case,
    get_list_dataset_split_items_use_case,
    get_list_training_preflight_runs_use_case,
    get_list_training_runs_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.dataset import (
    DatasetItemRead,
    DatasetReleaseCreate,
    DatasetReleaseRead,
    DatasetSnapshotCreate,
    DatasetSnapshotRead,
    DatasetSplitItemRead,
)
from blueberry_microid.interfaces.api.v1.schemas.ml_preflight import TrainingPreflightRunResponse
from blueberry_microid.interfaces.api.v1.schemas.training_run import TrainingRunResponse

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/snapshots", response_model=DatasetSnapshotRead, status_code=status.HTTP_201_CREATED)
def create_dataset_snapshot(
    payload: DatasetSnapshotCreate,
    use_case: CreateDatasetSnapshotUseCase = Depends(get_create_dataset_snapshot_use_case),
) -> DatasetSnapshotRead:
    dto = use_case.execute(
        CreateDatasetSnapshotRequest(
            name=payload.name,
            version=payload.version,
            description=payload.description,
            created_by=payload.created_by,
            notes=payload.notes,
            include_inconclusive=payload.include_inconclusive,
            include_rejected=payload.include_rejected,
        )
    )
    return DatasetSnapshotRead.model_validate(dto)


@router.get("/snapshots", response_model=list[DatasetSnapshotRead])
def list_dataset_snapshots(
    use_case: ListDatasetSnapshotsUseCase = Depends(get_list_dataset_snapshots_use_case),
) -> list[DatasetSnapshotRead]:
    return [DatasetSnapshotRead.model_validate(dto) for dto in use_case.execute()]


@router.get("/snapshots/{dataset_snapshot_id}", response_model=DatasetSnapshotRead)
def get_dataset_snapshot(
    dataset_snapshot_id: UUID,
    use_case: GetDatasetSnapshotUseCase = Depends(get_get_dataset_snapshot_use_case),
) -> DatasetSnapshotRead:
    return DatasetSnapshotRead.model_validate(use_case.execute(dataset_snapshot_id))


@router.get("/snapshots/{dataset_snapshot_id}/items", response_model=list[DatasetItemRead])
def list_dataset_items(
    dataset_snapshot_id: UUID,
    use_case: ListDatasetItemsUseCase = Depends(get_list_dataset_items_use_case),
) -> list[DatasetItemRead]:
    return [DatasetItemRead.model_validate(dto) for dto in use_case.execute(dataset_snapshot_id)]


@router.get("/snapshots/{dataset_snapshot_id}/manifest")
def get_dataset_manifest(
    dataset_snapshot_id: UUID,
    exporter: DatasetManifestExporter = Depends(get_dataset_manifest_exporter),
) -> dict:
    return exporter.export(dataset_snapshot_id)


@router.post("/releases", response_model=DatasetReleaseRead, status_code=status.HTTP_201_CREATED)
def create_dataset_release(
    payload: DatasetReleaseCreate,
    use_case: CreateDatasetReleaseUseCase = Depends(get_create_dataset_release_use_case),
) -> DatasetReleaseRead:
    dto = use_case.execute(
        CreateDatasetReleaseRequest(
            dataset_snapshot_id=payload.dataset_snapshot_id,
            name=payload.name,
            version=payload.version,
            split_strategy=payload.split_strategy,
            random_seed=payload.random_seed,
            train_ratio=payload.train_ratio,
            validation_ratio=payload.validation_ratio,
            test_ratio=payload.test_ratio,
            created_by=payload.created_by,
            notes=payload.notes,
        )
    )
    return DatasetReleaseRead.model_validate(dto)


@router.get("/releases", response_model=list[DatasetReleaseRead])
def list_dataset_releases(
    use_case: ListDatasetReleasesUseCase = Depends(get_list_dataset_releases_use_case),
) -> list[DatasetReleaseRead]:
    return [DatasetReleaseRead.model_validate(dto) for dto in use_case.execute()]


@router.get("/releases/{dataset_release_id}", response_model=DatasetReleaseRead)
def get_dataset_release(
    dataset_release_id: UUID,
    use_case: GetDatasetReleaseUseCase = Depends(get_get_dataset_release_use_case),
) -> DatasetReleaseRead:
    return DatasetReleaseRead.model_validate(use_case.execute(dataset_release_id))


@router.get("/releases/{dataset_release_id}/items", response_model=list[DatasetSplitItemRead])
def list_dataset_split_items(
    dataset_release_id: UUID,
    use_case: ListDatasetSplitItemsUseCase = Depends(get_list_dataset_split_items_use_case),
) -> list[DatasetSplitItemRead]:
    return [DatasetSplitItemRead.model_validate(dto) for dto in use_case.execute(dataset_release_id)]


@router.get("/releases/{dataset_release_id}/manifest")
def get_dataset_release_manifest(
    dataset_release_id: UUID,
    exporter: DatasetReleaseManifestExporter = Depends(get_dataset_release_manifest_exporter),
) -> dict:
    return exporter.export(dataset_release_id)


@router.get("/releases/{dataset_release_id}/preflight-runs", response_model=list[TrainingPreflightRunResponse])
def list_dataset_release_preflight_runs(
    dataset_release_id: UUID,
    use_case: ListTrainingPreflightRunsUseCase = Depends(get_list_training_preflight_runs_use_case),
) -> list[TrainingPreflightRunResponse]:
    return [TrainingPreflightRunResponse.model_validate(dto) for dto in use_case.execute(dataset_release_id)]


@router.get("/releases/{dataset_release_id}/training-runs", response_model=list[TrainingRunResponse])
def list_dataset_release_training_runs(
    dataset_release_id: UUID,
    use_case: ListTrainingRunsUseCase = Depends(get_list_training_runs_use_case),
) -> list[TrainingRunResponse]:
    return [
        TrainingRunResponse.model_validate(dto)
        for dto in use_case.execute(dataset_release_id=dataset_release_id)
    ]
