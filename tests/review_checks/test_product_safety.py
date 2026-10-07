"""Isolated safety checks runnable with unittest without DB/OpenCV services."""

import io
import unittest
from tempfile import SpooledTemporaryFile
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image
from pydantic import ValidationError

from blueberry_microid.application.exceptions import ImageTooLargeError, InvalidImageError
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.infrastructure.storage.pillow_image_validator import PillowImageValidator
from blueberry_microid.interfaces.api.upload_limits import read_bounded_upload
from blueberry_microid.interfaces.api.v1.schemas.human_review import HumanReviewCreate
from blueberry_microid.ml.inference_engine.colony_count_assessment import assess_colony_count


def countable_plate(**changes):
    fields = dict(region_count=12, sharpness=100.0, mean_intensity=128.0,
                  colony_coverage=0.03, extraction_ok=True, plate_detected=True,
                  segmentation_conflict=False, confluent_growth_detected=False,
                  visualization={"regions": [{}] * 12})
    fields.update(changes)
    return fields


class ColonyCountTests(unittest.TestCase):
    def test_returns_unvalidated_count_and_never_cfu(self):
        result = assess_colony_count(countable_plate())
        self.assertEqual(result["estimated_count"], 12)
        self.assertEqual(result["status"], "preliminary")
        self.assertEqual(result["validation_status"], "unvalidated")
        self.assertIsNone(result["cfu_per_ml"])
        self.assertTrue(result["requires_human_review"])

    def test_empty_clear_plate_has_zero_not_missing_count(self):
        result = assess_colony_count(countable_plate(region_count=0, colony_coverage=0.0))
        self.assertEqual(result["estimated_count"], 0)

    def test_unsuitable_capture_never_returns_a_count(self):
        for field, value, reason in [
            ("extraction_ok", False, "extraction_failed"),
            ("plate_detected", False, "plate_not_detected"),
            ("sharpness", 49.0, "insufficient_focus"),
            ("sharpness", float("nan"), "insufficient_focus"),
            ("mean_intensity", 231.0, "unsuitable_exposure"),
            ("segmentation_conflict", True, "segmentation_uncertain"),
            ("confluent_growth_detected", True, "connected_growth"),
            ("colony_coverage", 0.45, "high_coverage"),
            ("colony_coverage", float("inf"), "invalid_coverage"),
            ("region_count", 301, "too_many_candidates"),
            ("region_count", -1, "invalid_candidate_count"),
            ("region_count", True, "invalid_candidate_count"),
        ]:
            with self.subTest(field=field, value=value):
                result = assess_colony_count(countable_plate(**{field: value}))
                self.assertIsNone(result["estimated_count"])
                self.assertEqual(result["status"], "not_countable")
                self.assertIn(reason, result["reason_codes"])

    def test_missing_signals_abstain(self):
        self.assertEqual(assess_colony_count({})["status"], "not_countable")

    def test_overlay_limit_does_not_truncate_count(self):
        result = assess_colony_count(countable_plate(region_count=120))
        self.assertEqual(result["estimated_count"], 120)
        self.assertEqual(result["visible_region_count"], 12)
        self.assertTrue(any("solo parte" in item for item in result["warnings"]))


def memory_upload(content: bytes):
    stream = SpooledTemporaryFile(max_size=2_000_000)
    stream.write(content)
    stream.seek(0)
    return UploadFile(stream, filename="test.png")


class UploadLimitTests(unittest.IsolatedAsyncioTestCase):
    def _upload(self, content: bytes):
        upload = memory_upload(content)
        self.addCleanup(upload.file.close)
        return upload

    async def test_exact_limit_is_accepted(self):
        upload = self._upload(b"a" * 10)
        self.assertEqual(await read_bounded_upload(upload, 10), b"a" * 10)

    async def test_oversized_upload_stops_at_limit_plus_one(self):
        upload = self._upload(b"a" * 1_000_000)
        stream = upload.file
        with self.assertRaises(ImageTooLargeError):
            await read_bounded_upload(upload, 10)
        self.assertEqual(stream.tell(), 11)

    async def test_empty_file_is_left_to_image_validator(self):
        self.assertEqual(await read_bounded_upload(self._upload(b""), 10), b"")

    async def test_invalid_limit_fails_closed(self):
        with self.assertRaises(ValueError):
            await read_bounded_upload(self._upload(b"abc"), 0)


class ImagePixelLimitTests(unittest.TestCase):
    def test_compressed_small_file_with_too_many_pixels_is_rejected(self):
        stream = io.BytesIO()
        Image.new("RGB", (100, 100)).save(stream, format="PNG")
        with self.assertRaises(InvalidImageError):
            PillowImageValidator(max_pixels=9999).validate(
                file_name="plate.png", mime_type="image/png", content=stream.getvalue())

    def test_exact_pixel_limit_is_accepted(self):
        stream = io.BytesIO()
        Image.new("RGB", (100, 100)).save(stream, format="PNG")
        self.assertEqual(PillowImageValidator(max_pixels=10000).validate(
            file_name="plate.png", mime_type="image/png", content=stream.getvalue()).width, 100)


class HumanReviewTests(unittest.TestCase):
    def test_zero_is_a_confirmed_manual_count(self):
        user_id = uuid4()
        review = HumanReview(uuid4(), "specialist", ReviewDecision.CONFIRMED,
                            reviewer_user_id=user_id, reviewed_colony_count=0)
        self.assertEqual(review.reviewed_colony_count, 0)
        self.assertEqual(review.reviewer_user_id, user_id)

    def test_missing_manual_count_remains_none(self):
        self.assertIsNone(HumanReview(uuid4(), "specialist", ReviewDecision.CONFIRMED).reviewed_colony_count)

    def test_invalid_manual_counts_are_rejected_by_domain_and_api(self):
        for count in [-1, 100001, 1.5, True]:
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    HumanReview(uuid4(), "specialist", ReviewDecision.CONFIRMED,
                                reviewed_colony_count=count)
                with self.assertRaises(ValidationError):
                    HumanReviewCreate(review_decision="confirmed", reviewed_colony_count=count)

    def test_rejected_sample_cannot_have_confirmed_count(self):
        with self.assertRaises(ValueError):
            HumanReview(uuid4(), "specialist", ReviewDecision.REJECTED_INVALID_SAMPLE,
                        reviewed_colony_count=0)
        with self.assertRaises(ValidationError):
            HumanReviewCreate(review_decision="rejected_invalid_sample", reviewed_colony_count=0)

    def test_client_does_not_need_to_supply_reviewer_identity(self):
        self.assertIsNone(HumanReviewCreate(review_decision="confirmed").reviewer_name)


if __name__ == "__main__":
    unittest.main()
