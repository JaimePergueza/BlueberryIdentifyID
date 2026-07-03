from enum import Enum


class PetriRegionReviewDecision(str, Enum):
    """A reviewer's technical decision about a PetriSegmentationRegion candidate.

    These are annotation-candidate decisions, never microorganism identification.
    A `candidate_valid` region is only a useful candidate region for future
    annotation work; it is never a confirmed colony, a taxon, or a diagnosis.
    """

    CANDIDATE_VALID = "candidate_valid"
    CANDIDATE_FALSE_POSITIVE = "candidate_false_positive"
    CANDIDATE_UNCERTAIN = "candidate_uncertain"
    NEEDS_RESEGMENTATION = "needs_resegmentation"
