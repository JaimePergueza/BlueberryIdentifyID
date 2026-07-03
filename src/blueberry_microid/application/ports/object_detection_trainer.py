from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from blueberry_microid.domain.entities.annotation_bundle_file import AnnotationBundleFile
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.entities.annotation_quality_gate_run import AnnotationQualityGateRun
from blueberry_microid.domain.entities.detection_training_issue import DetectionTrainingIssue
from blueberry_microid.domain.enums.detection_training_status import DetectionTrainingStatus
from blueberry_microid.ml.configs.detection_training_config import DetectionTrainingConfig
from typing import Optional


@dataclass(frozen=True)
class DetectionTrainingPlan:
    """The result of planning a detection training dry-run.

    Purely a plan: `training_plan`/`command_preview`/`expected_outputs` are
    JSON-serializable descriptions of what a future, separately-approved
    phase could run — nothing here executes a command, imports a training
    framework, or writes any file.
    """

    is_runnable: bool
    status: DetectionTrainingStatus
    training_plan: dict
    command_preview: dict
    dataset_summary: dict
    quality_gate_summary: dict
    expected_outputs: dict
    issues: list[DetectionTrainingIssue] = field(default_factory=list)


class ObjectDetectionTrainerPort(ABC):
    """Plans (never executes) an object-detection training attempt.

    Implementations must not call subprocess, must not import ultralytics or
    torch, must not write model weights, and must not download anything.
    """

    @abstractmethod
    def plan_training(
        self,
        bundle_run: AnnotationBundleRun,
        bundle_files: list[AnnotationBundleFile],
        quality_gate_run: Optional[AnnotationQualityGateRun],
        config: DetectionTrainingConfig,
    ) -> DetectionTrainingPlan:
        raise NotImplementedError
