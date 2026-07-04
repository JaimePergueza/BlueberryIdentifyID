from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from blueberry_microid.application.dto.model_evaluation_dto import (  # noqa: E402
    CreateModelCandidateFromLocalTrainingRunRequest,
)
from blueberry_microid.application.use_cases.model_evaluation import (  # noqa: E402
    CreateModelCandidateFromLocalTrainingRunUseCase,
    EvaluateModelCandidateUseCase,
    ListModelEvaluationIssuesUseCase,
    RunModelPromotionGateUseCase,
)
from blueberry_microid.infrastructure.config.settings import Settings  # noqa: E402
from blueberry_microid.infrastructure.db.session.engine import create_db_engine  # noqa: E402
from blueberry_microid.infrastructure.db.session.session_factory import create_session_factory  # noqa: E402
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a metadata-only YOLO smoke model candidate.")
    parser.add_argument("--local-training-run-id", required=True)
    parser.add_argument("--created-by")
    parser.add_argument("--emit-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        local_run_id = UUID(args.local_training_run_id)
    except ValueError:
        print("local-training-run-id must be a UUID", file=sys.stderr)
        return 2

    settings = Settings()
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    candidate = CreateModelCandidateFromLocalTrainingRunUseCase(
        SqlAlchemyUnitOfWork(session_factory), repo_root=_REPO_ROOT
    ).execute(
        CreateModelCandidateFromLocalTrainingRunRequest(
            local_yolo_training_execution_run_id=local_run_id,
            created_by=args.created_by,
            notes="Fase 39 smoke model evaluation",
        )
    )
    evaluation = EvaluateModelCandidateUseCase(SqlAlchemyUnitOfWork(session_factory)).execute(candidate.id)
    gate = RunModelPromotionGateUseCase(SqlAlchemyUnitOfWork(session_factory)).execute(
        evaluation.id, created_by=args.created_by, notes="Fase 39 promotion gate"
    )
    issues = ListModelEvaluationIssuesUseCase(SqlAlchemyUnitOfWork(session_factory)).execute(evaluation.id)
    payload = {
        "model_candidate_id": str(candidate.id),
        "model_evaluation_run_id": str(evaluation.id),
        "promotion_gate_run_id": str(gate.id),
        "evaluation_decision": evaluation.decision,
        "promotion_decision": gate.decision,
        "metrics_summary": evaluation.metrics_summary,
        "blocking_reasons": gate.blocking_reasons,
        "issue_codes": [issue.code for issue in issues],
        "training_performed": False,
        "inference_performed": False,
        "metadata_only": True,
    }
    if args.emit_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
