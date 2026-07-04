import inspect

from blueberry_microid.application.services.manual_yolo_training_runner_scaffold import (
    ManualYoloTrainingRunnerScaffold,
)
from blueberry_microid.domain.entities.detection_training_execution_issue import DetectionTrainingExecutionIssue
from blueberry_microid.domain.enums.detection_training_execution_decision import DetectionTrainingExecutionDecision
from blueberry_microid.domain.enums.detection_training_execution_issue_severity import (
    DetectionTrainingExecutionIssueSeverity,
)
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus
from tests.unit.application.test_detection_training_execution_gate_evaluator import (
    DetectionTrainingExecutionGateEvaluator,
    _evaluate,
    _setup,
)


def _ready_evaluation(tmp_path):
    from blueberry_microid.ml.configs.detection_training_execution_config import DetectionTrainingExecutionConfig

    bundle, run, readiness, environment_spec, artifact_policy = _setup(tmp_path)
    config = DetectionTrainingExecutionConfig(
        block_in_ci=False,
        manual_confirmation_text="I understand this will only create a scaffold and will not train a model",
        allow_ready_to_execute_status=True,
    )
    return _evaluate(run, readiness, environment_spec, artifact_policy, config=config)


def test_generates_execution_plan_with_manual_steps(tmp_path):
    evaluation = _ready_evaluation(tmp_path)

    plan = ManualYoloTrainingRunnerScaffold().build_execution_plan(evaluation)

    assert isinstance(plan["manual_steps"], list)
    assert len(plan["manual_steps"]) > 0


def test_includes_command_preview(tmp_path):
    evaluation = _ready_evaluation(tmp_path)

    plan = ManualYoloTrainingRunnerScaffold().build_execution_plan(evaluation)

    assert plan["command_preview"] == evaluation.command_preview


def test_includes_prohibited_actions(tmp_path):
    evaluation = _ready_evaluation(tmp_path)

    plan = ManualYoloTrainingRunnerScaffold().build_execution_plan(evaluation)

    assert len(plan["prohibited_actions"]) > 0
    assert any("ci" in action.lower() for action in plan["prohibited_actions"])


def test_includes_artifact_policy_reminders(tmp_path):
    evaluation = _ready_evaluation(tmp_path)

    plan = ManualYoloTrainingRunnerScaffold().build_execution_plan(evaluation)

    assert len(plan["artifact_policy_reminders"]) > 0


def test_never_calls_subprocess():
    source = inspect.getsource(
        __import__(
            "blueberry_microid.application.services.manual_yolo_training_runner_scaffold",
            fromlist=["ManualYoloTrainingRunnerScaffold"],
        )
    )
    assert "import subprocess" not in source
    assert "subprocess.run" not in source
    assert "subprocess.call" not in source
    assert "subprocess.Popen" not in source


def test_does_not_write_files(tmp_path):
    before = list(tmp_path.rglob("*"))
    evaluation = _ready_evaluation(tmp_path)
    before = list(tmp_path.rglob("*"))

    ManualYoloTrainingRunnerScaffold().build_execution_plan(evaluation)

    after = list(tmp_path.rglob("*"))
    assert before == after


def test_never_imports_torch_or_ultralytics():
    source = inspect.getsource(
        __import__(
            "blueberry_microid.application.services.manual_yolo_training_runner_scaffold",
            fromlist=["ManualYoloTrainingRunnerScaffold"],
        )
    )
    assert "import torch" not in source
    assert "import ultralytics" not in source


def test_checklist_reflects_manual_confirmation_status(tmp_path):
    evaluation = _ready_evaluation(tmp_path)

    plan = ManualYoloTrainingRunnerScaffold().build_execution_plan(evaluation)

    checklist_item = next(item for item in plan["checklist"] if item["item"] == "manual confirmation provided")
    assert checklist_item["satisfied"] is True
    assert evaluation.status == DetectionTrainingExecutionStatus.READY_TO_EXECUTE
