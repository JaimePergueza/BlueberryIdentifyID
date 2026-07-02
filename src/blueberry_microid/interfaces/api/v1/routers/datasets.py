from uuid import UUID

from fastapi import APIRouter, Depends, status

from blueberry_microid.application.dto.dataset_dto import CreateDatasetSnapshotRequest
from blueberry_microid.application.services.dataset_manifest_exporter import DatasetManifestExporter
from blueberry_microid.application.use_cases.dataset.create_dataset_snapshot import CreateDatasetSnapshotUseCase
from blueberry_microid.application.use_cases.dataset.get_dataset_snapshot import GetDatasetSnapshotUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_items import ListDatasetItemsUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_snapshots import ListDatasetSnapshotsUseCase
from blueberry_microid.interfaces.api.v1.dependencies import (
    get_create_dataset_snapshot_use_case,
    get_dataset_manifest_exporter,
    get_get_dataset_snapshot_use_case,
    get_list_dataset_items_use_case,
    get_list_dataset_snapshots_use_case,
)
from blueberry_microid.interfaces.api.v1.schemas.dataset import (
    DatasetItemRead,
    DatasetSnapshotCreate,
    DatasetSnapshotRead,
)

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

