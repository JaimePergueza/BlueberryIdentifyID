from uuid import uuid4

import pytest

from blueberry_microid.application.dto.annotation_bundle_dto import (
    AnnotationBundleConfigDTO,
    CreateAnnotationBundleRunRequest,
)
from blueberry_microid.application.exceptions import (
    AnnotationBundleNotAllowedError,
    PetriAnnotationExportRunNotFoundError,
)
from blueberry_microid.application.services.annotation_bundle_validator import AnnotationBundleValidator
from blueberry_microid.application.services.annotation_bundle_writer import AnnotationBundleWriter
from blueberry_microid.application.use_cases.annotation_bundle.create_annotation_bundle_run import (
    CreateAnnotationBundleRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.list_annotation_bundle_files import (
    ListAnnotationBundleFilesUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.list_annotation_bundle_runs import (
    ListAnnotationBundleRunsUseCase,
)
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnnotationBundleFileRepository,
    InMemoryAnnotationBundleRunRepository,
    InMemoryPetriAnnotationExportItemRepository,
    InMemoryPetriAnnotationExportRunRepository,
)
from tests.unit.application.test_annotation_bundle_services import _export_run, _item


class FailingAnnotationBundleFileRepository(InMemoryAnnotationBundleFileRepository):
    def add_many(self, files):
        raise RuntimeError("simulated annotation bundle file insert failure")


def _build(*, file_repo=None):
    items = [_item()]
    export_run_repo = InMemoryPetriAnnotationExportRunRepository()
    export_item_repo = InMemoryPetriAnnotationExportItemRepository()
    bundle_run_repo = InMemoryAnnotationBundleRunRepository()
    bundle_file_repo = file_repo or InMemoryAnnotationBundleFileRepository()
    export_run = export_run_repo.add(_export_run(items))
    for item in items:
        object.__setattr__(item, "export_run_id", export_run.id)
    export_item_repo.add_many(items)
    uow = FakeUnitOfWork(
        analysis_run_repository=None,
        prediction_repository=None,
        annotation_bundle_run_repository=bundle_run_repo,
        annotation_bundle_file_repository=bundle_file_repo,
    )
    use_case = CreateAnnotationBundleRunUseCase(
        export_run_repo,
        export_item_repo,
        AnnotationBundleValidator(),
        AnnotationBundleWriter(),
        uow,
    )
    return use_case, export_run, export_run_repo, export_item_repo, bundle_run_repo, bundle_file_repo


def test_creates_dry_run_bundle_and_persists_planned_files(tmp_path):
    use_case, export_run, _, _, bundle_run_repo, bundle_file_repo = _build()

    result = use_case.execute(
        CreateAnnotationBundleRunRequest(
            export_run.id,
            config=AnnotationBundleConfigDTO(output_dir=str(tmp_path / "bundle"), dry_run=True),
            created_by="qa",
        )
    )

    assert result.status.value == "dry_run"
    assert result.is_completed is True
    assert result.file_count == 6
    assert result.annotation_count == 1
    assert result.label_count == 1
    assert bundle_run_repo.get_by_id(result.id) is not None
    assert len(bundle_file_repo.list_by_bundle_run_id(result.id)) == 6


def test_creates_real_bundle_files(tmp_path):
    use_case, export_run, *_ = _build()

    result = use_case.execute(
        CreateAnnotationBundleRunRequest(
            export_run.id,
            config=AnnotationBundleConfigDTO(output_dir=str(tmp_path / "bundle"), dry_run=False),
        )
    )

    assert result.status.value == "completed"
    assert (tmp_path / "bundle" / "manifest.json").exists()
    assert result.bundle_manifest["contains_training"] is False


def test_rejects_missing_export_run():
    use_case, *_ = _build()

    with pytest.raises(PetriAnnotationExportRunNotFoundError):
        use_case.execute(CreateAnnotationBundleRunRequest(uuid4()))


def test_rejects_copy_images_config():
    use_case, export_run, *_ = _build()

    with pytest.raises(AnnotationBundleNotAllowedError, match="copy_images=true"):
        use_case.execute(
            CreateAnnotationBundleRunRequest(export_run.id, config=AnnotationBundleConfigDTO(copy_images=True))
        )


def test_rolls_back_bundle_run_when_file_persistence_fails(tmp_path):
    failing_file_repo = FailingAnnotationBundleFileRepository()
    use_case, export_run, _, _, bundle_run_repo, _ = _build(file_repo=failing_file_repo)

    with pytest.raises(RuntimeError, match="simulated annotation bundle file insert failure"):
        use_case.execute(
            CreateAnnotationBundleRunRequest(
                export_run.id,
                config=AnnotationBundleConfigDTO(output_dir=str(tmp_path / "bundle"), dry_run=True),
            )
        )

    assert bundle_run_repo.list_all() == []


def test_lists_bundles_by_release_and_export(tmp_path):
    use_case, export_run, _, _, bundle_run_repo, bundle_file_repo = _build()
    created = use_case.execute(
        CreateAnnotationBundleRunRequest(
            export_run.id,
            config=AnnotationBundleConfigDTO(output_dir=str(tmp_path / "bundle"), dry_run=True),
        )
    )

    list_runs = ListAnnotationBundleRunsUseCase(bundle_run_repo)
    list_files = ListAnnotationBundleFilesUseCase(bundle_run_repo, bundle_file_repo)

    assert [run.id for run in list_runs.execute(dataset_release_id=export_run.dataset_release_id)] == [created.id]
    assert [run.id for run in list_runs.execute(petri_annotation_export_run_id=export_run.id)] == [created.id]
    assert len(list_files.execute(created.id)) == created.file_count
