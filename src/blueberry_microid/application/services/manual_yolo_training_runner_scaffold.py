from __future__ import annotations

from typing import Any

from blueberry_microid.application.services.detection_training_execution_gate_evaluator import (
    DetectionTrainingExecutionGateEvaluation,
)
from blueberry_microid.domain.enums.detection_training_execution_status import DetectionTrainingExecutionStatus

_PROHIBITED_ACTIONS = [
    "do not run this command in CI",
    "do not commit model weights (.pt/.pth/.onnx/.h5/.ckpt/.pb/.tflite) to the repository",
    "do not point artifact_root_dir at a path inside the repository",
    "do not install ultralytics/torch as part of this scaffold",
    "do not treat a ready_to_execute status as a trained model",
]

_SAFETY_NOTES = [
    "no training command is executed by this phase; command_preview is text only",
    "no real weight, metric, or prediction file is created by this phase",
    "RepositorySafetyValidator must report is_safe=true before any future manual step",
]


class ManualYoloTrainingRunnerScaffold:
    """Turns a DetectionTrainingExecutionGateEvaluation into a human-readable
    manual execution plan.

    Never executes anything: no `subprocess`, no `torch`/`ultralytics`
    import, no file writes. This only assembles JSON-safe text describing
    what a human would need to do, manually, outside this system, in a
    future and separately-approved phase.
    """

    def build_execution_plan(self, evaluation: DetectionTrainingExecutionGateEvaluation) -> dict[str, Any]:
        return {
            "preconditions": self._preconditions(),
            "manual_steps": self._manual_steps(evaluation),
            "command_preview": dict(evaluation.command_preview),
            "output_expectations": self._output_expectations(evaluation),
            "artifact_policy_reminders": self._artifact_policy_reminders(),
            "rollback_notes": [
                "if a manual attempt is abandoned, delete only files under artifact_root_dir, "
                "never files inside this repository",
            ],
            "safety_notes": list(_SAFETY_NOTES),
            "prohibited_actions": list(_PROHIBITED_ACTIONS),
            "checklist": self._checklist(evaluation),
            "status": evaluation.status.value,
            "decision": evaluation.decision.value,
        }

    def _preconditions(self) -> list[str]:
        return [
            "DetectionTrainingRun must be status=planned and is_runnable=true",
            "DetectionTrainingReadinessReport must be decision=ready_for_training",
            "DetectionTrainingEnvironmentSpec must be decision=environment_ready",
            "DetectionTrainingArtifactPolicy must be decision=artifact_policy_ready",
            "RepositorySafetyValidator must report is_safe=true",
            "this evaluation must not be running inside CI",
        ]

    def _manual_steps(self, evaluation: DetectionTrainingExecutionGateEvaluation) -> list[str]:
        steps = [
            "review the AnnotationBundleRun and AnnotationQualityGateRun this plan was built from",
            "confirm artifact_root_dir points outside this repository",
            "review command_preview below; it is a plan, not an executable command",
        ]
        if evaluation.status != DetectionTrainingExecutionStatus.READY_TO_EXECUTE:
            steps.append("resolve the outstanding issues on this execution run before any manual attempt")
        steps.append(
            "in a future, separately-approved phase, a human would run the previewed command manually outside "
            "this system and register the real outputs afterward"
        )
        return steps

    def _output_expectations(self, evaluation: DetectionTrainingExecutionGateEvaluation) -> dict[str, Any]:
        return {
            "expected_outputs": dict(evaluation.expected_outputs),
            "note": "these are planned paths only; no file exists yet",
        }

    def _artifact_policy_reminders(self) -> list[str]:
        return [
            "register outputs only as planned artifacts until a future phase approves actual artifact registration",
            "never store weights inside this repository, even temporarily",
            "keep .gitignore coverage of weight/model extensions and training-output directories up to date",
        ]

    def _checklist(self, evaluation: DetectionTrainingExecutionGateEvaluation) -> list[dict[str, Any]]:
        error_codes = {issue.code for issue in evaluation.errors}
        return [
            {
                "item": "detection training run planned and runnable",
                "satisfied": "detection_training_not_planned" not in error_codes,
            },
            {
                "item": "readiness report ready",
                "satisfied": not error_codes & {"readiness_not_ready", "readiness_report_missing"},
            },
            {
                "item": "environment spec ready",
                "satisfied": not error_codes & {"environment_not_ready", "environment_spec_missing"},
            },
            {
                "item": "artifact policy ready",
                "satisfied": not error_codes & {"artifact_policy_not_ready", "artifact_policy_missing"},
            },
            {
                "item": "repository safety passed",
                "satisfied": not error_codes & {"repository_safety_failed", "artifact_root_not_safe"},
            },
            {"item": "not running in CI", "satisfied": "ci_execution_blocked" not in error_codes},
            {
                "item": "manual confirmation provided",
                "satisfied": evaluation.status == DetectionTrainingExecutionStatus.READY_TO_EXECUTE,
            },
        ]
