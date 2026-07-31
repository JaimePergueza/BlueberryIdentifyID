"""Fixtures for isolated API tests with authenticated role variants."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from blueberry_microid.application.use_cases.auth.create_user import CreateUserUseCase
from blueberry_microid.domain.enums.user_role import UserRole
from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.models import (
    AnalysisRunModel,
    AnnotationBundleFileModel,
    AnnotationBundleRunModel,
    AnnotationQualityGateIssueModel,
    AnnotationQualityGateRunModel,
    AuthSessionModel,
    Base,
    DatasetCurationItemModel,
    DatasetCurationRunModel,
    DatasetItemModel,
    DatasetReleaseModel,
    DatasetSnapshotModel,
    DatasetSplitItemModel,
    DetectionTrainingArtifactIssueModel,
    DetectionTrainingArtifactPolicyModel,
    DetectionTrainingArtifactRecordModel,
    DetectionTrainingEnvironmentIssueModel,
    DetectionTrainingEnvironmentSpecModel,
    DetectionTrainingExecutionIssueModel,
    DetectionTrainingExecutionRunModel,
    DetectionTrainingIssueModel,
    DetectionTrainingReadinessIssueModel,
    DetectionTrainingReadinessReportModel,
    DetectionTrainingRunModel,
    HumanReviewModel,
    ImageDatasetAuditIssueModel,
    ImageDatasetAuditRunModel,
    ImageFeatureExtractionRunModel,
    ImageFeatureVectorModel,
    MicroImageModel,
    ModelCandidateModel,
    ModelEvaluationIssueModel,
    ModelEvaluationRunModel,
    ModelPromotionGateRunModel,
    ModelVersionModel,
    PetriImageModel,
    PetriAnnotationExportItemModel,
    PetriAnnotationExportRunModel,
    PetriRegionReviewModel,
    PetriSegmentationRegionModel,
    PetriSegmentationRunModel,
    PredictionModel,
    SampleModel,
    TrainingPreflightIssueModel,
    TrainingPreflightRunModel,
    TrainingPredictionModel,
    TrainingRunModel,
    TrainingRunComparisonEntryModel,
    TrainingRunComparisonModel,
    UserModel,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.security.pwdlib_password_hasher import PwdlibPasswordHasher
from blueberry_microid.interfaces.api.app import create_app

_SQLITE_TABLES = [
    UserModel.__table__,
    AuthSessionModel.__table__,
    SampleModel.__table__,
    ModelVersionModel.__table__,
    PetriImageModel.__table__,
    MicroImageModel.__table__,
    AnalysisRunModel.__table__,
    HumanReviewModel.__table__,
    PredictionModel.__table__,
    DatasetCurationRunModel.__table__,
    DatasetCurationItemModel.__table__,
    DatasetSnapshotModel.__table__,
    DatasetItemModel.__table__,
    DatasetReleaseModel.__table__,
    DatasetSplitItemModel.__table__,
    TrainingPreflightRunModel.__table__,
    TrainingPreflightIssueModel.__table__,
    TrainingRunModel.__table__,
    TrainingPredictionModel.__table__,
    TrainingRunComparisonModel.__table__,
    TrainingRunComparisonEntryModel.__table__,
    ImageDatasetAuditRunModel.__table__,
    ImageDatasetAuditIssueModel.__table__,
    ImageFeatureExtractionRunModel.__table__,
    ImageFeatureVectorModel.__table__,
    PetriSegmentationRunModel.__table__,
    PetriSegmentationRegionModel.__table__,
    PetriRegionReviewModel.__table__,
    PetriAnnotationExportRunModel.__table__,
    PetriAnnotationExportItemModel.__table__,
    AnnotationBundleRunModel.__table__,
    AnnotationBundleFileModel.__table__,
    AnnotationQualityGateRunModel.__table__,
    AnnotationQualityGateIssueModel.__table__,
    DetectionTrainingRunModel.__table__,
    DetectionTrainingIssueModel.__table__,
    DetectionTrainingReadinessReportModel.__table__,
    DetectionTrainingReadinessIssueModel.__table__,
    DetectionTrainingEnvironmentSpecModel.__table__,
    DetectionTrainingEnvironmentIssueModel.__table__,
    DetectionTrainingArtifactPolicyModel.__table__,
    DetectionTrainingArtifactRecordModel.__table__,
    DetectionTrainingArtifactIssueModel.__table__,
    DetectionTrainingExecutionRunModel.__table__,
    DetectionTrainingExecutionIssueModel.__table__,
    ModelCandidateModel.__table__,
    ModelEvaluationRunModel.__table__,
    ModelEvaluationIssueModel.__table__,
    ModelPromotionGateRunModel.__table__,
]

_TEST_PASSWORD = "Correct-Horse-Battery-42"


@pytest.fixture()
def api_app(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=_SQLITE_TABLES)

    app = create_app()
    app.state.settings = Settings(
        _env_file=None,
        storage_root=tmp_path,
        database_url="sqlite://",
        auth_session_ttl_hours=12,
    )
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    yield app
    engine.dispose()


def _create_user(app, username: str, role: UserRole) -> None:
    with app.state.session_factory() as session:
        CreateUserUseCase(
            SqlAlchemyUserRepository(session),
            PwdlibPasswordHasher(),
        ).execute(username, _TEST_PASSWORD, role)


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": _TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def anonymous_api_client(api_app):
    with TestClient(api_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture()
def api_client(api_app):
    """Backward-compatible client authenticated as an administrator."""
    _create_user(api_app, "test-admin", UserRole.ADMIN)
    with TestClient(api_app, raise_server_exceptions=False) as client:
        token = _login(client, "test-admin")
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


@pytest.fixture()
def specialist_api_client(api_app):
    _create_user(api_app, "test-specialist", UserRole.SPECIALIST)
    with TestClient(api_app, raise_server_exceptions=False) as client:
        token = _login(client, "test-specialist")
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client
