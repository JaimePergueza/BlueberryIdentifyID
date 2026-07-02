import logging
from uuid import UUID

from blueberry_microid.application.dto.analysis_run_dto import AnalysisRunDTO, ProcessAnalysisRunResult
from blueberry_microid.application.dto.prediction_dto import PredictionDTO
from blueberry_microid.application.exceptions import (
    AnalysisProcessingError,
    AnalysisRunFinalizationError,
    AnalysisRunNotFoundError,
    DuplicatePredictionError,
    MicroImageNotFoundError,
    ModelVersionNotFoundError,
    PetriImageNotFoundError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.inference_engine import InferenceEnginePort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.exceptions.errors import InvalidAnalysisRunTransitionError

logger = logging.getLogger("blueberry_microid.business.process_analysis_run")

_NOT_PENDING_REASONS = {
    "processing": "it is already being processed",
    "completed": "it has already been processed",
    "needs_review": "it has already been processed",
    "failed": "it already failed previously; create a new AnalysisRun to retry",
}
_ANALYSIS_PROCESSING_FAILED_MESSAGE = "Analysis processing failed"
_DUPLICATE_PREDICTION_MESSAGE = "Prediction already exists for this analysis run"


class ProcessAnalysisRunUseCase:
    """Runs the (currently simulated) inference pipeline for one pending AnalysisRun.

    This does not perform real image analysis and does not identify a
    microorganism species/genus — see `InferenceEnginePort` and
    `MockInferenceEngine`. It exists to validate the technical pipeline:
    AnalysisRun (`pending`) -> `processing` -> inference -> `Prediction` +
    final status (`completed`/`needs_review`), or -> `failed` if anything
    after the claim goes wrong.

    Concurrency safety (only one caller can ever process a given
    AnalysisRun): the `pending -> processing` transition is performed by
    `AnalysisRunRepositoryPort.claim_for_processing`, a single atomic
    conditional UPDATE at the database level — not a Python-side
    read-then-write. Two simultaneous calls for the same AnalysisRun can
    never both win the claim, so only one of them ever reaches the inference
    engine or writes a Prediction. See ARCHITECTURE.md for the full
    rationale (Option B: atomic conditional update, chosen over pessimistic
    row locking for portability across SQLite and PostgreSQL).

    Idempotency: a claim only succeeds from `pending`. Every other status —
    `processing`, `completed`, `needs_review`, `failed` — makes the claim
    fail and this use case raises `InvalidAnalysisRunTransitionError`
    (mapped to HTTP 409), with a message tailored to the observed status.
    Retrying a `failed` run means creating a new AnalysisRun, not reusing
    this one.

    Recovery: once an AnalysisRun is claimed as `processing`, this use case
    guarantees it will not stay stuck there. Any failure from this point
    on — the inference engine raising, the Prediction failing to construct,
    or the final commit failing — is caught and turned into a `failed`
    AnalysisRun with a controlled `error_message`, persisted in its own
    transaction (`_handle_processing_failure`). The original exception is
    logged server-side and preserved as the cause of a controlled
    `AnalysisProcessingError` (mapped to HTTP 500). Only if *that* fallback
    write itself fails does this use case give up and raise
    `AnalysisRunFinalizationError`
    (mapped to HTTP 500) — the one scenario this cannot self-heal, logged at
    CRITICAL level server-side. `DuplicatePredictionError` is also recovered
    to `failed`, then returned as a controlled 409 conflict with a safe
    client-facing message.

    Transaction boundary: creating the Prediction and moving the AnalysisRun
    to its final status (success or failure) each happen inside their own
    single `UnitOfWorkPort` transaction — either both writes of a given step
    persist, or neither does.
    """

    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        model_version_repository: ModelVersionRepositoryPort,
        inference_engine: InferenceEnginePort,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._analysis_run_repository = analysis_run_repository
        self._petri_image_repository = petri_image_repository
        self._micro_image_repository = micro_image_repository
        self._model_version_repository = model_version_repository
        self._inference_engine = inference_engine
        self._unit_of_work = unit_of_work

    def execute(self, analysis_run_id: UUID) -> ProcessAnalysisRunResult:
        existing = self._analysis_run_repository.get_by_id(analysis_run_id)
        if existing is None:
            raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run_id}' does not exist")

        petri_image = self._petri_image_repository.get_by_id(existing.petri_image_id)
        if petri_image is None:
            raise PetriImageNotFoundError(f"petri_image '{existing.petri_image_id}' does not exist")

        micro_image = self._micro_image_repository.get_by_id(existing.micro_image_id)
        if micro_image is None:
            raise MicroImageNotFoundError(f"micro_image '{existing.micro_image_id}' does not exist")

        model_version = self._model_version_repository.get_by_id(existing.model_version_id)
        if model_version is None:
            raise ModelVersionNotFoundError(f"model_version '{existing.model_version_id}' does not exist")

        # Atomic conditional claim: succeeds only if the row is still
        # `pending` at the database level. This is the sole idempotency and
        # concurrency guard — no Python-side status check on `existing` is
        # trusted for this decision, since `existing` may already be stale.
        analysis_run = self._analysis_run_repository.claim_for_processing(analysis_run_id)
        if analysis_run is None:
            reason = _NOT_PENDING_REASONS.get(existing.status.value, "it is not pending")
            raise InvalidAnalysisRunTransitionError(
                f"cannot process AnalysisRun '{analysis_run_id}': {reason} (status='{existing.status.value}')"
            )

        logger.info(
            "analysis run processing started",
            extra={
                "analysis_run_id": str(analysis_run.id),
                "sample_id": str(analysis_run.sample_id),
                "model_version_id": str(analysis_run.model_version_id),
                "initial_status": "pending",
            },
        )

        try:
            inference_output = self._inference_engine.process(
                analysis_run=analysis_run,
                petri_image=petri_image,
                micro_image=micro_image,
                model_version=model_version,
            )

            prediction = Prediction(
                analysis_run_id=analysis_run.id,
                predicted_label=inference_output.predicted_label,
                confidence_score=inference_output.confidence_score,
                class_probabilities=inference_output.class_probabilities,
                technical_observation=inference_output.technical_observation,
                requires_human_review=inference_output.requires_human_review,
            )

            if prediction.requires_human_review:
                analysis_run.mark_needs_review()
            else:
                analysis_run.mark_completed()

            with self._unit_of_work as uow:
                created_prediction = uow.prediction_repository.add(prediction)
                updated_run = uow.analysis_run_repository.update(analysis_run)
                uow.commit()

        except DuplicatePredictionError as exc:
            # Structurally shouldn't happen: claim_for_processing() ensures
            # only one caller ever reaches this point for a given
            # AnalysisRun. If it does (e.g. manual DB tampering), do not
            # leave the run in `processing`. Mark it failed and surface the
            # conflict with a safe, stable client-facing message.
            self._handle_processing_failure(
                analysis_run,
                exc,
                error_message=_DUPLICATE_PREDICTION_MESSAGE,
            )
            raise DuplicatePredictionError(_DUPLICATE_PREDICTION_MESSAGE) from exc
        except Exception as exc:
            self._handle_processing_failure(
                analysis_run,
                exc,
                error_message=_ANALYSIS_PROCESSING_FAILED_MESSAGE,
            )
            logger.info(
                "analysis run processing finished",
                extra={
                    "analysis_run_id": str(analysis_run.id),
                    "sample_id": str(analysis_run.sample_id),
                    "model_version_id": str(analysis_run.model_version_id),
                    "final_status": AnalysisStatus.FAILED.value,
                    "prediction_created": False,
                    "requires_human_review": False,
                    "error": True,
                },
            )
            raise AnalysisProcessingError(_ANALYSIS_PROCESSING_FAILED_MESSAGE) from exc

        logger.info(
            "analysis run processing finished",
            extra={
                "analysis_run_id": str(analysis_run.id),
                "sample_id": str(analysis_run.sample_id),
                "model_version_id": str(analysis_run.model_version_id),
                "final_status": updated_run.status.value,
                "prediction_created": True,
                "requires_human_review": created_prediction.requires_human_review,
                "error": False,
            },
        )
        return ProcessAnalysisRunResult(
            analysis_run=AnalysisRunDTO.from_entity(updated_run),
            prediction=PredictionDTO.from_entity(created_prediction),
        )

    def _handle_processing_failure(
        self,
        analysis_run: AnalysisRun,
        original_error: Exception,
        *,
        error_message: str,
    ) -> AnalysisRun:
        """Best-effort: ensure `analysis_run` never stays stuck in `processing`.

        Mutates and persists `analysis_run` as `failed` in its own
        transaction, separate from whatever just failed. `error_message` is
        deliberately safe and controlled; the raw exception text stays in
        server logs. If that fallback
        write also fails, raises `AnalysisRunFinalizationError` chained to
        the persistence failure — `original_error` is never silently lost,
        it is always logged here first.
        """
        logger.error(
            "analysis run processing failed; marking as failed",
            extra={
                "analysis_run_id": str(analysis_run.id),
                "sample_id": str(analysis_run.sample_id),
                "model_version_id": str(analysis_run.model_version_id),
                "exception_type": type(original_error).__name__,
            },
            exc_info=original_error,
        )
        # `analysis_run` may already have been mutated in-memory to
        # `completed`/`needs_review` before the failure happened (e.g. the
        # failure *is* the finalizing commit itself) — but nothing beyond
        # `processing` was ever actually persisted, since that mutation and
        # the failed write both belong to the same still-open transaction.
        # Reset the in-memory entity to its last genuinely persisted state
        # so `mark_failed()` reflects reality and always succeeds here.
        analysis_run.status = AnalysisStatus.PROCESSING
        analysis_run.mark_failed(error_message)

        try:
            with self._unit_of_work as uow:
                updated = uow.analysis_run_repository.update(analysis_run)
                uow.commit()
            return updated
        except Exception as persist_error:
            logger.critical(
                "could not persist AnalysisRun failure state; it may remain stuck in 'processing'",
                extra={"analysis_run_id": str(analysis_run.id), "sample_id": str(analysis_run.sample_id)},
                exc_info=persist_error,
            )
            raise AnalysisRunFinalizationError(
                f"analysis_run '{analysis_run.id}' failed during processing, and the failure "
                "state itself could not be persisted"
            ) from persist_error
