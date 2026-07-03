from enum import Enum


class PetriAnnotationExportFormat(str, Enum):
    """Supported supervised annotation export formats.

    `yolo_txt` is only a label-text export representation. It is not a YOLO
    model implementation and never trains anything.
    """

    BLUEBERRY_MANIFEST = "blueberry_manifest"
    COCO_JSON = "coco_json"
    YOLO_TXT = "yolo_txt"
