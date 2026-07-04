from enum import Enum


class DetectionTrainingArtifactLocationType(str, Enum):
    LOCAL_PATH = "local_path"
    EXTERNAL_URI = "external_uri"
    RELATIVE_PATH = "relative_path"
    UNRESOLVED = "unresolved"
