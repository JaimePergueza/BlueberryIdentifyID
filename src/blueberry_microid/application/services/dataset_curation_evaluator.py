from __future__ import annotations

from typing import Optional

from blueberry_microid.application.dto.dataset_curation_dto import (
    CuratedAnalysisCandidateDTO,
    DatasetCurationPolicy,
)
from blueberry_microid.application.services.final_analysis_resolver import resolve_final_label
from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.review_decision import ReviewDecision


class DatasetCurationEvaluator:
    """Evaluates whether a two-image AnalysisRun is eligible for curation."""

    def evaluate(
        self,
        *,
        analysis_run: AnalysisRun,
        prediction: Optional[Prediction],
        final_review: Optional[HumanReview],
        petri_image: Optional[PetriImage],
        micro_image: Optional[MicroImage],
        policy: DatasetCurationPolicy,
    ) -> CuratedAnalysisCandidateDTO:
        status = DatasetCurationStatus.INCLUDED
        reason: Optional[str] = None
        final_label = None

        if analysis_run.status in {AnalysisStatus.PENDING, AnalysisStatus.PROCESSING}:
            status = DatasetCurationStatus.EXCLUDED_PENDING_REVIEW
            reason = "analysis_run is not completed or reviewable yet"
        elif policy.require_prediction and prediction is None:
            status = DatasetCurationStatus.EXCLUDED_MISSING_PREDICTION
            reason = "prediction is required before deriving reviewed ground truth"
        elif policy.require_final_human_review and final_review is None:
            status = DatasetCurationStatus.EXCLUDED_PENDING_REVIEW
            reason = "final human review is required"
        elif (policy.require_petri_image and petri_image is None) or (policy.require_micro_image and micro_image is None):
            status = DatasetCurationStatus.EXCLUDED_MISSING_IMAGES
            reason = "both Petri and microscopy images are required"
        else:
            assert prediction is not None
            resolution = resolve_final_label(prediction, final_review)
            final_label = resolution.final_label
            status, reason = self._status_from_review(final_review, final_label, policy)

        provenance = {
            "label_source": "final_human_review",
            "prediction_is_ground_truth": False,
            "uses_taxonomy": False,
            "uses_real_ai": False,
            "binary_payloads_stored": False,
        }
        if final_review is not None:
            provenance["review_decision"] = final_review.review_decision.value

        return CuratedAnalysisCandidateDTO(
            analysis_run_id=analysis_run.id,
            sample_id=analysis_run.sample_id,
            petri_image_id=analysis_run.petri_image_id if petri_image is not None else None,
            micro_image_id=analysis_run.micro_image_id if micro_image is not None else None,
            prediction_id=prediction.id if prediction is not None else None,
            human_review_id=final_review.id if final_review is not None else None,
            automatic_label=prediction.predicted_label if prediction is not None else None,
            final_label=final_label,
            review_decision=final_review.review_decision if final_review is not None else None,
            curation_status=status,
            exclusion_reason=reason,
            provenance=provenance,
            feature_summary=prediction.feature_summary if prediction is not None else None,
            quality_summary=prediction.quality_summary if prediction is not None else None,
        )

    def _status_from_review(
        self,
        review: Optional[HumanReview],
        final_label,
        policy: DatasetCurationPolicy,
    ) -> tuple[DatasetCurationStatus, Optional[str]]:
        if review is None:
            return DatasetCurationStatus.EXCLUDED_PENDING_REVIEW, "final human review is required"

        if review.review_decision == ReviewDecision.REJECTED_INVALID_SAMPLE:
            return DatasetCurationStatus.EXCLUDED_INVALID_SAMPLE, "final review rejected the sample as invalid"

        if review.review_decision == ReviewDecision.CONFIRMED and not policy.include_confirmed:
            return DatasetCurationStatus.EXCLUDED_POLICY, "confirmed reviews are disabled by policy"

        if review.review_decision == ReviewDecision.CORRECTED and not policy.include_corrected:
            return DatasetCurationStatus.EXCLUDED_POLICY, "corrected reviews are disabled by policy"

        if review.review_decision == ReviewDecision.MARKED_INCONCLUSIVE and not policy.include_marked_inconclusive:
            return DatasetCurationStatus.EXCLUDED_POLICY, "inconclusive reviews are disabled by policy"

        if final_label is None or final_label not in policy.allowed_labels:
            return DatasetCurationStatus.EXCLUDED_INVALID_LABEL, "final label is not allowed by policy"

        return DatasetCurationStatus.INCLUDED, None

