from enum import Enum


class ModelCandidateStatus(str, Enum):
    CREATED = "created"
    EVALUATED = "evaluated"
    BLOCKED = "blocked"
    PROMOTED = "promoted"
    ARCHIVED = "archived"
    FAILED = "failed"
