import uuid
from datetime import datetime, timezone

import pytest

from blueberry_microid.application.dto.analysis_run_dto import AnalysisRunDTO, ProcessAnalysisRunResult
from blueberry_microid.application.dto.prediction_dto import PredictionDTO
from blueberry_microid.application.exceptions import AnalysisProcessingError
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.infrastructure.tasks import analysis_tasks


class _SuccessfulUseCase:
    def __init__(self) -> None:
        self.received_id = None

    def execute(self, analysis_run_id):
        self.received_id = analysis_run_id
        now = datetime.now(timezone.utc)
        prediction_id = uuid.uuid4()
        return ProcessAnalysisRunResult(
            analysis_run=AnalysisRunDTO(
                id=analysis_run_id,
                sample_id=uuid.uuid4(),
                petri_image_id=uuid.uuid4(),
                micro_image_id=uuid.uuid4(),
                model_version_id=uuid.uuid4(),
                status=AnalysisStatus.COMPLETED,
                created_at=now,
                started_at=now,
                completed_at=now,
                error_message=None,
            ),
            prediction=PredictionDTO(
                id=prediction_id,
                analysis_run_id=analysis_run_id,
                predicted_label=PredictedLabel.NO_EVIDENT_GROWTH,
                confidence_score=0.6,
                class_probabilities={"no_evident_growth": 0.6},
                technical_observation="mock",
                requires_human_review=False,
                created_at=now,
            ),
        )


class _FailingUseCase:
    def execute(self, _analysis_run_id):
        raise AnalysisProcessingError("Analysis processing failed")


def test_process_analysis_run_task_invokes_process_use_case(monkeypatch):
    run_id = uuid.uuid4()
    use_case = _SuccessfulUseCase()
    monkeypatch.setattr(analysis_tasks, "build_process_analysis_run_use_case", lambda: use_case)

    result = analysis_tasks.process_analysis_run_task.run(str(run_id))

    assert use_case.received_id == run_id
    assert result["analysis_run_id"] == str(run_id)
    assert result["status"] == "completed"
    assert result["prediction_id"] is not None
    assert result["mock"] is True


def test_process_analysis_run_task_rejects_invalid_uuid():
    with pytest.raises(ValueError):
        analysis_tasks.process_analysis_run_task.run("not-a-uuid")


def test_process_analysis_run_task_reports_failed_run_for_controlled_processing_error(monkeypatch):
    run_id = uuid.uuid4()
    monkeypatch.setattr(analysis_tasks, "build_process_analysis_run_use_case", lambda: _FailingUseCase())
    monkeypatch.setattr(analysis_tasks, "_read_run_status", lambda _analysis_run_id: "failed")

    result = analysis_tasks.process_analysis_run_task.run(str(run_id))

    assert result == {
        "analysis_run_id": str(run_id),
        "status": "failed",
        "prediction_id": None,
        "mock": True,
    }
