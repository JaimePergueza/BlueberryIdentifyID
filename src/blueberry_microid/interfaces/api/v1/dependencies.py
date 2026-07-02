"""Composition root for the API layer.

This module is the one sanctioned place where `interfaces/api` is allowed to
import SQLAlchemy repositories and filesystem/Pillow-backed infrastructure
directly (see CLAUDE.md, "Arquitectura obligatoria"): every dependency
below is built here and handed to a use case through its constructor. The
routers only ever import use case classes and these factory functions —
never a repository or storage class directly.

`application/` never imports FastAPI, and no `Depends(...)` ever appears
outside `interfaces/`.
"""

from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker
from celery import Celery

from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.image_storage import ImageStoragePort
from blueberry_microid.application.ports.image_validator import ImageValidatorPort
from blueberry_microid.application.ports.inference_engine import InferenceEnginePort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.image_intake_service import ImageIntakeService
from blueberry_microid.application.use_cases.inference.create_analysis_run import CreateAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.get_analysis_run import GetAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.get_prediction import GetPredictionForAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.process_analysis_run import ProcessAnalysisRunUseCase
from blueberry_microid.application.use_cases.micro_image.register_micro_image import RegisterMicroImageUseCase
from blueberry_microid.application.use_cases.model_version.create_model_version import CreateModelVersionUseCase
from blueberry_microid.application.use_cases.model_version.list_model_versions import ListModelVersionsUseCase
from blueberry_microid.application.use_cases.petri_image.register_petri_image import RegisterPetriImageUseCase
from blueberry_microid.application.use_cases.review.get_final_human_review import GetFinalHumanReviewUseCase
from blueberry_microid.application.use_cases.review.list_human_reviews import ListHumanReviewsUseCase
from blueberry_microid.application.use_cases.review.submit_human_review import SubmitHumanReviewUseCase
from blueberry_microid.application.use_cases.sample.create_sample import CreateSampleUseCase
from blueberry_microid.application.use_cases.sample.get_sample import (
    GetSampleByIdUseCase,
    GetSampleBySampleCodeUseCase,
)
from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_human_review_repository import (
    SqlAlchemyHumanReviewRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_micro_image_repository import (
    SqlAlchemyMicroImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_model_version_repository import (
    SqlAlchemyModelVersionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_image_repository import (
    SqlAlchemyPetriImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_prediction_repository import (
    SqlAlchemyPredictionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from blueberry_microid.infrastructure.storage.local_image_storage import LocalImageStorage
from blueberry_microid.infrastructure.storage.pillow_image_validator import PillowImageValidator
from blueberry_microid.infrastructure.tasks.analysis_tasks import process_analysis_run_task
from blueberry_microid.infrastructure.tasks.celery_app import celery_app
from blueberry_microid.ml.inference_engine.mock_inference_engine import MockInferenceEngine

# --- settings & database session -----------------------------------------


def get_settings_dependency(request: Request) -> Settings:
    """Read from `request.app.state`, not a module-level global, so tests
    can swap in a different Settings instance per-app (see tests/api/conftest.py).
    """
    return request.app.state.settings


def get_db_session(request: Request) -> Iterator[Session]:
    """One Session per request, closed when the request finishes.

    The session factory lives on `app.state` (set once in `create_app()`),
    not imported as a module-level global, for the same testability reason.
    """
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_session_factory(request: Request) -> sessionmaker[Session]:
    """Exposes the raw session factory (not a single Session) for
    `UnitOfWorkPort`, which needs to open its own, separate transaction —
    see `get_unit_of_work` below.
    """
    return request.app.state.session_factory


def get_unit_of_work(session_factory: sessionmaker[Session] = Depends(get_session_factory)) -> UnitOfWorkPort:
    return SqlAlchemyUnitOfWork(session_factory)


def get_celery_app(request: Request) -> Celery:
    return getattr(request.app.state, "celery_app", celery_app)


def get_process_analysis_run_task():
    return process_analysis_run_task


# --- infrastructure: storage & validation ---------------------------------


def get_image_storage(settings: Settings = Depends(get_settings_dependency)) -> ImageStoragePort:
    return LocalImageStorage(settings.storage_root)


def get_image_validator() -> ImageValidatorPort:
    return PillowImageValidator()


def get_image_intake_service(
    settings: Settings = Depends(get_settings_dependency),
    image_validator: ImageValidatorPort = Depends(get_image_validator),
    image_storage: ImageStoragePort = Depends(get_image_storage),
) -> ImageIntakeService:
    # The upload size ceiling always comes from Settings (MAX_UPLOAD_SIZE_MB)
    # — never hardcoded in a router — so it is one source of truth and one
    # environment variable to change it.
    return ImageIntakeService(image_validator, image_storage, settings.max_upload_size_bytes)


# --- repositories ----------------------------------------------------------


def get_sample_repository(session: Session = Depends(get_db_session)) -> SampleRepositoryPort:
    return SqlAlchemySampleRepository(session)


def get_petri_image_repository(session: Session = Depends(get_db_session)) -> PetriImageRepositoryPort:
    return SqlAlchemyPetriImageRepository(session)


def get_micro_image_repository(session: Session = Depends(get_db_session)) -> MicroImageRepositoryPort:
    return SqlAlchemyMicroImageRepository(session)


def get_model_version_repository(session: Session = Depends(get_db_session)) -> ModelVersionRepositoryPort:
    return SqlAlchemyModelVersionRepository(session)


def get_analysis_run_repository(session: Session = Depends(get_db_session)) -> AnalysisRunRepositoryPort:
    return SqlAlchemyAnalysisRunRepository(session)


def get_human_review_repository(session: Session = Depends(get_db_session)) -> HumanReviewRepositoryPort:
    return SqlAlchemyHumanReviewRepository(session)


def get_prediction_repository(session: Session = Depends(get_db_session)) -> PredictionRepositoryPort:
    return SqlAlchemyPredictionRepository(session)


# --- inference engine --------------------------------------------------------


def get_inference_engine() -> InferenceEnginePort:
    """Selects which InferenceEnginePort implementation the API uses.

    Currently always `MockInferenceEngine` — a deterministic simulation,
    not real image analysis (see its docstring and ARCHITECTURE.md). This
    is the single place that would change to plug in a real/trained model
    later; nothing else in `application/` or `interfaces/` refers to
    `MockInferenceEngine` by name.
    """
    return MockInferenceEngine()


# --- use cases ---------------------------------------------------------------


def get_create_sample_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
) -> CreateSampleUseCase:
    return CreateSampleUseCase(sample_repository)


def get_get_sample_by_id_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
) -> GetSampleByIdUseCase:
    return GetSampleByIdUseCase(sample_repository)


def get_get_sample_by_code_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
) -> GetSampleBySampleCodeUseCase:
    return GetSampleBySampleCodeUseCase(sample_repository)


def get_register_petri_image_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    image_intake: ImageIntakeService = Depends(get_image_intake_service),
) -> RegisterPetriImageUseCase:
    return RegisterPetriImageUseCase(sample_repository, petri_image_repository, image_intake)


def get_register_micro_image_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    image_intake: ImageIntakeService = Depends(get_image_intake_service),
) -> RegisterMicroImageUseCase:
    return RegisterMicroImageUseCase(sample_repository, micro_image_repository, image_intake)


def get_create_model_version_use_case(
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
) -> CreateModelVersionUseCase:
    return CreateModelVersionUseCase(model_version_repository)


def get_list_model_versions_use_case(
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
) -> ListModelVersionsUseCase:
    return ListModelVersionsUseCase(model_version_repository)


def get_create_analysis_run_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
) -> CreateAnalysisRunUseCase:
    return CreateAnalysisRunUseCase(
        sample_repository,
        petri_image_repository,
        micro_image_repository,
        model_version_repository,
        analysis_run_repository,
    )


def get_get_analysis_run_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
) -> GetAnalysisRunUseCase:
    return GetAnalysisRunUseCase(analysis_run_repository)


def get_process_analysis_run_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
    inference_engine: InferenceEnginePort = Depends(get_inference_engine),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> ProcessAnalysisRunUseCase:
    return ProcessAnalysisRunUseCase(
        analysis_run_repository,
        petri_image_repository,
        micro_image_repository,
        model_version_repository,
        inference_engine,
        unit_of_work,
    )


def get_get_prediction_use_case(
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
) -> GetPredictionForAnalysisRunUseCase:
    return GetPredictionForAnalysisRunUseCase(prediction_repository)


def get_submit_human_review_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> SubmitHumanReviewUseCase:
    return SubmitHumanReviewUseCase(analysis_run_repository, prediction_repository, unit_of_work)


def get_get_final_human_review_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    human_review_repository: HumanReviewRepositoryPort = Depends(get_human_review_repository),
) -> GetFinalHumanReviewUseCase:
    return GetFinalHumanReviewUseCase(analysis_run_repository, human_review_repository)


def get_list_human_reviews_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    human_review_repository: HumanReviewRepositoryPort = Depends(get_human_review_repository),
) -> ListHumanReviewsUseCase:
    return ListHumanReviewsUseCase(analysis_run_repository, human_review_repository)
