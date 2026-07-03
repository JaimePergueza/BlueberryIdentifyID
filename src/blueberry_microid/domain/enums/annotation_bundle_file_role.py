from enum import Enum


class AnnotationBundleFileRole(str, Enum):
    COCO_ANNOTATIONS = "coco_annotations"
    YOLO_LABEL = "yolo_label"
    BLUEBERRY_MANIFEST = "blueberry_manifest"
    DATASET_YAML = "dataset_yaml"
    README = "readme"
    BUNDLE_MANIFEST = "bundle_manifest"
    COPIED_IMAGE = "copied_image"
