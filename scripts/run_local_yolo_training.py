from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from blueberry_microid.application.use_cases.detection_training_execution.run_local_yolo_training import (
    RunLocalYoloTrainingUseCase,
)
from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_annotation_bundle_file_repository import (
    SqlAlchemyAnnotationBundleFileRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_artifact_policy_repository import (
    SqlAlchemyDetectionTrainingArtifactPolicyRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_execution_run_repository import (
    SqlAlchemyDetectionTrainingExecutionRunRepository,
)
from blueberry_microid.infrastructure.db.session.engine import create_db_engine
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from blueberry_microid.application.services.local_yolo_training_runner import LocalYoloTrainingRunner
from blueberry_microid.ml.configs.local_yolo_training_runner_config import LocalYoloTrainingRunnerConfig

_REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run local/manual YOLO training outside CI after all persisted gates are approved. "
            "Requires optional dependency: pip install -e .[training]"
        )
    )
    parser.add_argument("--execution-run-id", required=True)
    parser.add_argument("--dataset-yaml")
    parser.add_argument("--artifact-root-dir", required=True)
    parser.add_argument("--base-model-path", required=True)
    confirmation_group = parser.add_mutually_exclusive_group(required=True)
    confirmation_group.add_argument("--manual-confirmation-text")
    confirmation_group.add_argument("--confirmation-text")
    parser.add_argument("--run-name")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--image-size", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--device")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--patience", type=int)
    parser.add_argument("--allow-existing-output-dir", action="store_true")
    parser.add_argument("--allow-policy-without-actual-registration", action="store_true")
    parser.add_argument(
        "--dry-run-validation-only",
        action="store_true",
        help="Validate persisted gates and local paths without importing ultralytics, training, or registering artifacts.",
    )
    args = parser.parse_args(argv)
    manual_confirmation_text = args.manual_confirmation_text or args.confirmation_text

    settings = Settings()
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        use_case = RunLocalYoloTrainingUseCase(
            execution_run_repository=SqlAlchemyDetectionTrainingExecutionRunRepository(session),
            artifact_policy_repository=SqlAlchemyDetectionTrainingArtifactPolicyRepository(session),
            bundle_file_repository=SqlAlchemyAnnotationBundleFileRepository(session),
            runner=LocalYoloTrainingRunner(repo_root=_REPO_ROOT),
            unit_of_work=SqlAlchemyUnitOfWork(session_factory),
        )
        config = LocalYoloTrainingRunnerConfig(
            manual_confirmation_text=manual_confirmation_text,
            artifact_root_dir=args.artifact_root_dir,
            base_model_path=args.base_model_path,
            dataset_yaml_path=args.dataset_yaml,
            run_name=args.run_name,
            epochs=args.epochs,
            image_size=args.image_size,
            batch_size=args.batch_size,
            device=args.device,
            workers=args.workers,
            seed=args.seed,
            patience=args.patience,
            allow_existing_output_dir=args.allow_existing_output_dir,
            require_policy_allows_actual_registration=not args.allow_policy_without_actual_registration,
        )
        if args.dry_run_validation_only:
            result = use_case.validate_only(UUID(args.execution_run_id), config)
        else:
            result = use_case.execute(
                UUID(args.execution_run_id),
                config,
            )
    print(
        json.dumps(
            {
                "execution_run_id": result.execution_run_id,
                "artifact_root_dir": result.artifact_root_dir,
                "dataset_yaml_path": result.dataset_yaml_path,
                "save_dir": result.save_dir,
                "summary": result.summary,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
