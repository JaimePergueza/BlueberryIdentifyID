"""Application transaction/compensation tests with injected dependencies.

These do not replace SQLAlchemy or PostgreSQL integration tests.
"""

from copy import deepcopy
from types import SimpleNamespace
import unittest

from blueberry_microid.application.dto.two_image_upload_dto import TwoImageUploadRequest
from blueberry_microid.application.exceptions import ImageStorageCompensationError
from blueberry_microid.application.use_cases.analysis.analyze_two_uploaded_images import AnalyzeTwoUploadedImagesUseCase
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


class Store:
    def __init__(self, failure=False):
        self.rows = []
        self.failure = failure

    def add(self, value):
        if self.failure:
            raise RuntimeError("repository unavailable")
        self.rows.append(value)
        return value

    def list_all(self):
        return self.rows


class Transaction:
    def __init__(self, *, commit_failure=False, sample_failure=False):
        self.sample_repository = Store(sample_failure)
        self.petri_image_repository = Store()
        self.micro_image_repository = Store()
        self.analysis_run_repository = Store()
        self.prediction_repository = Store()
        self.repositories = [self.sample_repository, self.petri_image_repository,
                             self.micro_image_repository, self.analysis_run_repository,
                             self.prediction_repository]
        self.commit_failure = commit_failure
        self.committed = False

    def __enter__(self):
        self.snapshots = [deepcopy(repo.rows) for repo in self.repositories]
        return self

    def __exit__(self, exc_type, exc, traceback):
        if not self.committed:
            for repo, rows in zip(self.repositories, self.snapshots):
                repo.rows = rows

    def commit(self):
        if self.commit_failure:
            raise RuntimeError("commit unavailable")
        self.committed = True


class Storage:
    def __init__(self, cleanup_failure=False):
        self.saved = []
        self.deleted = []
        self.cleanup_failure = cleanup_failure

    def save(self, **kwargs):
        path = f"/fake/{len(self.saved)}"
        self.saved.append(path)
        return path

    def delete(self, path):
        self.deleted.append(path)
        if self.cleanup_failure:
            raise OSError("cleanup unavailable")


class Engine:
    def __init__(self, failure=False):
        self.failure = failure

    def analyze(self, **kwargs):
        if self.failure:
            raise RuntimeError("engine unavailable")
        return SimpleNamespace(
            predicted_label=PredictedLabel.INCONCLUSIVE, confidence_score=0.25,
            class_probabilities={label.value: 0.2 for label in PredictedLabel},
            feature_summary={}, quality_summary={"overall_status": "rejected"},
            explanation="Insufficient evidence", decision_trace=[], warnings=None,
            disclaimer="Preliminary result",
        )


class AnalysisCompensationTests(unittest.TestCase):
    def make_case(self, *, engine_failure=False, commit_failure=False,
                  sample_failure=False, cleanup_failure=False):
        uow = Transaction(commit_failure=commit_failure, sample_failure=sample_failure)
        storage = Storage(cleanup_failure=cleanup_failure)
        validator = SimpleNamespace(validate=lambda **kwargs: SimpleNamespace(width=32, height=24))
        case = AnalyzeTwoUploadedImagesUseCase(
            validator, storage, Engine(engine_failure),
            Store(), uow,
        )
        request = TwoImageUploadRequest("petri.png", "image/png", b"petri",
                                       "micro.png", "image/png", b"micro")
        return case, request, uow, storage

    def test_engine_failure_rolls_back_all_sample_records(self):
        case, request, uow, storage = self.make_case(engine_failure=True)
        with self.assertRaisesRegex(RuntimeError, "engine unavailable"):
            case.execute(request)
        self.assertTrue(all(not repo.rows for repo in uow.repositories))
        self.assertCountEqual(storage.deleted, storage.saved)

    def test_commit_failure_removes_files_and_all_sample_records(self):
        case, request, uow, storage = self.make_case(commit_failure=True)
        with self.assertRaisesRegex(RuntimeError, "commit unavailable"):
            case.execute(request)
        self.assertTrue(all(not repo.rows for repo in uow.repositories))
        self.assertCountEqual(storage.deleted, storage.saved)

    def test_sample_creation_failure_still_cleans_both_files(self):
        case, request, uow, storage = self.make_case(sample_failure=True)
        with self.assertRaisesRegex(RuntimeError, "repository unavailable"):
            case.execute(request)
        self.assertCountEqual(storage.deleted, storage.saved)

    def test_cleanup_attempts_both_files_and_preserves_original_cause(self):
        case, request, uow, storage = self.make_case(engine_failure=True, cleanup_failure=True)
        with self.assertLogs("blueberry_microid.business.analyze_two_uploaded_images", level="ERROR"):
            with self.assertRaises(ImageStorageCompensationError) as caught:
                case.execute(request)
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)
        self.assertCountEqual(storage.deleted, storage.saved)

    def test_success_commits_records_and_keeps_files(self):
        case, request, uow, storage = self.make_case()
        result = case.execute(request)
        self.assertTrue(uow.committed)
        self.assertTrue(all(len(repo.rows) == 1 for repo in uow.repositories))
        self.assertEqual(storage.deleted, [])
        self.assertEqual(result.sample_id, uow.sample_repository.rows[0].id)
