from __future__ import annotations

"""Single source of truth for the weight/model extensions and training-output
directories that must never be tracked by Git.

Shared by `DetectionTrainingArtifactPolicyConfig` (per-policy evaluation) and
`RepositorySafetyConfig` (whole-repository scan) so the two checks can never
drift apart on what counts as a forbidden artifact.
"""


def default_forbidden_extensions() -> list[str]:
    return [".pt", ".pth", ".onnx", ".h5", ".ckpt", ".pb", ".tflite"]


def default_required_gitignore_patterns() -> list[str]:
    return [
        "*.pt",
        "*.pth",
        "*.onnx",
        "*.h5",
        "*.ckpt",
        "*.pb",
        "*.tflite",
        "runs/",
        "training_outputs/",
        "training_artifacts/",
        "model_artifacts/",
        "checkpoints/",
        "weights/",
        "mlruns/",
        "wandb/",
        "tensorboard/",
        "lightning_logs/",
        "predictions/",
        "inference_outputs/",
        "evaluation_outputs/",
        "experiments/",
        ".local_training/",
    ]
