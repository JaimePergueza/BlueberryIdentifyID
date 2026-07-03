from __future__ import annotations

import os
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from PIL import Image, UnidentifiedImageError

from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.ml.configs.image_audit_config import ImageAuditConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest, TrainingManifestItem
from blueberry_microid.ml.reports.image_audit_report import ImageAuditFinding, ImageDatasetAuditReport

_ERROR = ImageDatasetAuditIssueSeverity.ERROR
_WARNING = ImageDatasetAuditIssueSeverity.WARNING
_OUTLIER_RATIO = 3.0
_DIMENSION_BUCKETS = (
    (256, "under_256"),
    (512, "256_to_511"),
    (1024, "512_to_1023"),
    (2048, "1024_to_2047"),
)
_DIMENSION_OVERFLOW_BUCKET = "2048_and_above"
_FILE_SIZE_BUCKETS = (
    (100_000, "under_100kb"),
    (500_000, "100kb_to_500kb"),
    (1_000_000, "500kb_to_1mb"),
    (5_000_000, "1mb_to_5mb"),
)
_FILE_SIZE_OVERFLOW_BUCKET = "5mb_and_above"


@dataclass
class _ImageProbe:
    """Live Pillow read of one image path. `readable=False` means the file
    could not be opened/decoded at all — every other field is then None."""

    readable: bool
    image_format: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    color_mode: Optional[str] = None


def _bucket(value: int, thresholds: tuple[tuple[int, str], ...], overflow_label: str) -> str:
    for threshold, label in thresholds:
        if value < threshold:
            return label
    return overflow_label


def _probe_image(path: str) -> _ImageProbe:
    """Open the image twice, mirroring PillowImageValidator: `verify()` on
    the first handle catches corruption, but leaves the object unusable for
    reading dimensions/format/mode, so those come from a fresh second open.
    Never raises; a decode failure just means `readable=False`."""

    try:
        with Image.open(path) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return _ImageProbe(readable=False)

    try:
        with Image.open(path) as image:
            image_format = image.format
            width, height = image.size
            color_mode = image.mode
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return _ImageProbe(readable=False)

    return _ImageProbe(readable=True, image_format=image_format, width=width, height=height, color_mode=color_mode)


class ImageDatasetAuditor:
    """Runs lightweight, Pillow-based technical checks over every Petri and
    micro image path referenced by a DatasetRelease's TrainingManifest.

    This never opens images as training tensors, never trains a model, and
    never makes a microbiological/taxonomic judgment — it only answers
    whether the image *files* are technically usable for some future
    training pipeline (exist, decode, plausible format/size/color mode).

    Severity design (documented here because Task 6/11 leave it to the
    implementation): ERROR = blocks the release from a clean `passed` audit
    outright (image_empty_path, image_missing, image_unreadable,
    image_format_mismatch, image_size_bytes_mismatch — the last one signals
    the file on disk no longer matches what was recorded at upload time,
    a genuine integrity problem). WARNING = advisory, does not block
    (image_too_small, image_too_large, image_unsupported_color_mode,
    image_metadata_missing, image_dimension_outlier, image_duplicate_path —
    all describe images that are still readable/usable, just suboptimal or
    worth a human's attention).
    """

    def audit(self, manifest: TrainingManifest, config: ImageAuditConfig) -> ImageDatasetAuditReport:
        findings: list[ImageAuditFinding] = []
        format_counts: Counter[str] = Counter()
        color_mode_counts: Counter[str] = Counter()
        dimension_counts: Counter[str] = Counter()
        file_size_counts: Counter[str] = Counter()
        seen_paths: set[str] = set()

        checked_petri = 0
        checked_micro = 0
        failed_petri: set[str] = set()
        failed_micro: set[str] = set()

        # Collected only for images that decoded successfully, used for the
        # (optional) second-pass dimension-outlier check below.
        petri_dimensions: list[tuple[TrainingManifestItem, int, int]] = []
        micro_dimensions: list[tuple[TrainingManifestItem, int, int]] = []

        for item in manifest.items:
            petri_findings, petri_probe = self._audit_one_image(
                item=item,
                modality=ImageModality.PETRI,
                path=item.petri_image_path,
                declared_width=item.petri_width,
                declared_height=item.petri_height,
                declared_file_size_bytes=item.petri_file_size_bytes,
                config=config,
                seen_paths=seen_paths,
            )
            findings.extend(petri_findings)
            if petri_probe is not None and petri_probe.readable:
                checked_petri += 1
                self._record_distributions(petri_probe, item.petri_image_path, format_counts, color_mode_counts, dimension_counts, file_size_counts)
                if petri_probe.width is not None and petri_probe.height is not None:
                    petri_dimensions.append((item, petri_probe.width, petri_probe.height))
            if any(f.severity == _ERROR for f in petri_findings):
                failed_petri.add(item.dataset_item_id or item.petri_image_path)

            micro_findings, micro_probe = self._audit_one_image(
                item=item,
                modality=ImageModality.MICRO,
                path=item.micro_image_path,
                declared_width=item.micro_width,
                declared_height=item.micro_height,
                declared_file_size_bytes=item.micro_file_size_bytes,
                config=config,
                seen_paths=seen_paths,
            )
            findings.extend(micro_findings)
            if micro_probe is not None and micro_probe.readable:
                checked_micro += 1
                self._record_distributions(micro_probe, item.micro_image_path, format_counts, color_mode_counts, dimension_counts, file_size_counts)
                if micro_probe.width is not None and micro_probe.height is not None:
                    micro_dimensions.append((item, micro_probe.width, micro_probe.height))
            if any(f.severity == _ERROR for f in micro_findings):
                failed_micro.add(item.dataset_item_id or item.micro_image_path)

        if config.warn_on_dimension_outliers:
            findings.extend(self._detect_outliers(petri_dimensions, ImageModality.PETRI))
            findings.extend(self._detect_outliers(micro_dimensions, ImageModality.MICRO))

        errors = [f for f in findings if f.severity == _ERROR]
        warnings = [f for f in findings if f.severity == _WARNING]
        is_passed = not errors
        status = _status_for(errors, warnings)

        return ImageDatasetAuditReport(
            is_passed=is_passed,
            status=status,
            total_items=len(manifest.items),
            total_petri_images=len(manifest.items),
            total_micro_images=len(manifest.items),
            checked_petri_images=checked_petri,
            checked_micro_images=checked_micro,
            failed_petri_images=len(failed_petri),
            failed_micro_images=len(failed_micro),
            errors=errors,
            warnings=warnings,
            format_distribution=dict(sorted(format_counts.items())),
            color_mode_distribution=dict(sorted(color_mode_counts.items())),
            dimension_distribution=dict(sorted(dimension_counts.items())),
            file_size_distribution=dict(sorted(file_size_counts.items())),
            recommendations=_recommendations(errors, warnings),
        )

    def _audit_one_image(
        self,
        *,
        item: TrainingManifestItem,
        modality: ImageModality,
        path: str,
        declared_width: Optional[int],
        declared_height: Optional[int],
        declared_file_size_bytes: Optional[int],
        config: ImageAuditConfig,
        seen_paths: set[str],
    ) -> tuple[list[ImageAuditFinding], Optional[_ImageProbe]]:
        findings: list[ImageAuditFinding] = []

        def _finding(severity: ImageDatasetAuditIssueSeverity, code: str, message: str, details: Optional[dict] = None) -> ImageAuditFinding:
            return ImageAuditFinding(
                severity=severity,
                modality=modality,
                code=code,
                message=message,
                dataset_item_id=item.dataset_item_id,
                dataset_split_item_id=item.dataset_split_item_id,
                image_path=path or None,
                details=details,
            )

        if not path or not path.strip():
            findings.append(_finding(_ERROR, "image_empty_path", f"{modality.value} image path is empty"))
            return findings, None

        if config.validate_existence and not os.path.exists(path):
            findings.append(_finding(_ERROR, "image_missing", f"{modality.value} image file does not exist: {path}"))
            return findings, None

        if config.detect_duplicate_paths:
            if path in seen_paths:
                findings.append(_finding(_WARNING, "image_duplicate_path", f"{modality.value} image path is reused by another item: {path}"))
            else:
                seen_paths.add(path)

        probe: Optional[_ImageProbe] = None
        if config.validate_readability or config.validate_format or config.validate_dimensions or config.validate_color_mode:
            probe = _probe_image(path)
            if not probe.readable:
                if config.validate_readability:
                    findings.append(_finding(_ERROR, "image_unreadable", f"{modality.value} image is not a valid or is a corrupted image: {path}"))
                    return findings, probe
                probe = None

        if probe is not None:
            if config.validate_format and probe.image_format not in config.allowed_formats:
                findings.append(
                    _finding(
                        _ERROR,
                        "image_format_mismatch",
                        f"{modality.value} image format '{probe.image_format}' is not allowed",
                        {"detected_format": probe.image_format, "allowed_formats": list(config.allowed_formats)},
                    )
                )

            if config.validate_dimensions and probe.width is not None and probe.height is not None:
                if probe.width < config.min_width or probe.height < config.min_height:
                    findings.append(
                        _finding(
                            _WARNING,
                            "image_too_small",
                            f"{modality.value} image is smaller than the minimum ({probe.width}x{probe.height})",
                            {"width": probe.width, "height": probe.height, "min_width": config.min_width, "min_height": config.min_height},
                        )
                    )
                if (config.max_width is not None and probe.width > config.max_width) or (
                    config.max_height is not None and probe.height > config.max_height
                ):
                    findings.append(
                        _finding(
                            _WARNING,
                            "image_too_large",
                            f"{modality.value} image exceeds the maximum dimensions ({probe.width}x{probe.height})",
                            {"reason": "dimensions", "width": probe.width, "height": probe.height},
                        )
                    )

            if config.validate_color_mode and probe.color_mode not in config.allowed_color_modes:
                findings.append(
                    _finding(
                        _WARNING,
                        "image_unsupported_color_mode",
                        f"{modality.value} image color mode '{probe.color_mode}' is not in the allowed list",
                        {"detected_color_mode": probe.color_mode, "allowed_color_modes": list(config.allowed_color_modes)},
                    )
                )

        if config.validate_dimensions and (declared_width is None or declared_height is None):
            findings.append(_finding(_WARNING, "image_metadata_missing", f"{modality.value} image has no persisted width/height metadata"))

        if config.validate_file_size:
            real_size = os.path.getsize(path) if os.path.exists(path) else None
            if real_size is not None and declared_file_size_bytes is not None and real_size != declared_file_size_bytes:
                findings.append(
                    _finding(
                        _ERROR,
                        "image_size_bytes_mismatch",
                        f"{modality.value} image file size on disk ({real_size}) does not match the recorded size ({declared_file_size_bytes})",
                        {"real_file_size_bytes": real_size, "declared_file_size_bytes": declared_file_size_bytes},
                    )
                )
            if real_size is not None and config.max_file_size_bytes is not None and real_size > config.max_file_size_bytes:
                findings.append(
                    _finding(
                        _WARNING,
                        "image_too_large",
                        f"{modality.value} image file size ({real_size} bytes) exceeds the configured maximum",
                        {"reason": "file_size_bytes", "real_file_size_bytes": real_size, "max_file_size_bytes": config.max_file_size_bytes},
                    )
                )

        return findings, probe

    def _record_distributions(
        self,
        probe: _ImageProbe,
        path: str,
        format_counts: Counter[str],
        color_mode_counts: Counter[str],
        dimension_counts: Counter[str],
        file_size_counts: Counter[str],
    ) -> None:
        if probe.image_format:
            format_counts[probe.image_format] += 1
        if probe.color_mode:
            color_mode_counts[probe.color_mode] += 1
        if probe.width is not None and probe.height is not None:
            dimension_counts[_bucket(max(probe.width, probe.height), _DIMENSION_BUCKETS, _DIMENSION_OVERFLOW_BUCKET)] += 1
        if os.path.exists(path):
            file_size_counts[_bucket(os.path.getsize(path), _FILE_SIZE_BUCKETS, _FILE_SIZE_OVERFLOW_BUCKET)] += 1

    def _detect_outliers(
        self,
        dimensions: list[tuple[TrainingManifestItem, int, int]],
        modality: ImageModality,
    ) -> list[ImageAuditFinding]:
        if len(dimensions) < 2:
            return []
        median_width = statistics.median(width for _, width, _height in dimensions)
        median_height = statistics.median(height for _, _width, height in dimensions)
        findings: list[ImageAuditFinding] = []
        for item, width, height in dimensions:
            is_outlier = (
                width > median_width * _OUTLIER_RATIO
                or height > median_height * _OUTLIER_RATIO
                or (median_width > 0 and width < median_width / _OUTLIER_RATIO)
                or (median_height > 0 and height < median_height / _OUTLIER_RATIO)
            )
            if is_outlier:
                path = item.petri_image_path if modality == ImageModality.PETRI else item.micro_image_path
                findings.append(
                    ImageAuditFinding(
                        severity=_WARNING,
                        modality=modality,
                        code="image_dimension_outlier",
                        message=f"{modality.value} image dimensions ({width}x{height}) are a statistical outlier for this release",
                        dataset_item_id=item.dataset_item_id,
                        dataset_split_item_id=item.dataset_split_item_id,
                        image_path=path or None,
                        details={"width": width, "height": height, "median_width": median_width, "median_height": median_height},
                    )
                )
        return findings


def _status_for(errors: list[ImageAuditFinding], warnings: list[ImageAuditFinding]) -> ImageDatasetAuditStatus:
    if errors:
        return ImageDatasetAuditStatus.FAILED
    if warnings:
        return ImageDatasetAuditStatus.WARNING
    return ImageDatasetAuditStatus.PASSED


def _recommendations(errors: list[ImageAuditFinding], warnings: list[ImageAuditFinding]) -> list[str]:
    if errors:
        return ["fix blocking image issues before any future training attempt"]
    if warnings:
        return ["review technical warnings; images are usable but not ideal for future training"]
    return ["images passed technical audit; no model training was run"]
