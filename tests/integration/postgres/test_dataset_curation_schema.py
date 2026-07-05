from uuid import uuid4
import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


pytestmark = pytest.mark.postgres


def _seed_reviewed_analysis(pg_session):
    sample_id = uuid4()
    model_version_id = uuid4()
    petri_image_id = uuid4()
    micro_image_id = uuid4()
    analysis_run_id = uuid4()
    prediction_id = uuid4()
    review_id = uuid4()

    pg_session.execute(
        text(
            """
            INSERT INTO samples (id, sample_code, product)
            VALUES (:id, 'CUR-PG-001', 'blueberry')
            """
        ),
        {"id": sample_id},
    )
    pg_session.execute(
        text(
            """
            INSERT INTO model_versions (id, name, version, model_type, is_active)
            VALUES (:id, 'mock', 'curation-pg', 'mock', true)
            """
        ),
        {"id": model_version_id},
    )
    pg_session.execute(
        text(
            """
            INSERT INTO petri_images (id, sample_id, file_path, file_name, mime_type, file_size_bytes)
            VALUES (:id, :sample_id, '/x/petri.jpg', 'petri.jpg', 'image/jpeg', 10)
            """
        ),
        {"id": petri_image_id, "sample_id": sample_id},
    )
    pg_session.execute(
        text(
            """
            INSERT INTO micro_images (id, sample_id, file_path, file_name, mime_type, file_size_bytes)
            VALUES (:id, :sample_id, '/x/micro.jpg', 'micro.jpg', 'image/jpeg', 10)
            """
        ),
        {"id": micro_image_id, "sample_id": sample_id},
    )
    pg_session.execute(
        text(
            """
            INSERT INTO analysis_runs
                (id, sample_id, petri_image_id, micro_image_id, model_version_id, status)
            VALUES
                (:id, :sample_id, :petri_image_id, :micro_image_id, :model_version_id, 'completed')
            """
        ),
        {
            "id": analysis_run_id,
            "sample_id": sample_id,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )
    pg_session.execute(
        text(
            """
            INSERT INTO predictions (id, analysis_run_id, predicted_label)
            VALUES (:id, :analysis_run_id, 'suspicious_growth')
            """
        ),
        {"id": prediction_id, "analysis_run_id": analysis_run_id},
    )
    pg_session.execute(
        text(
            """
            INSERT INTO human_reviews (id, analysis_run_id, reviewer_name, review_decision, is_final)
            VALUES (:id, :analysis_run_id, 'expert', 'confirmed', true)
            """
        ),
        {"id": review_id, "analysis_run_id": analysis_run_id},
    )
    return {
        "sample_id": sample_id,
        "petri_image_id": petri_image_id,
        "micro_image_id": micro_image_id,
        "analysis_run_id": analysis_run_id,
        "prediction_id": prediction_id,
        "review_id": review_id,
    }


def test_dataset_curation_tables_created_by_migration(pg_session):
    tables = {
        row[0]
        for row in pg_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        )
    }

    assert "dataset_curation_runs" in tables
    assert "dataset_curation_items" in tables


def test_dataset_curation_item_unique_per_run_and_analysis(pg_session):
    refs = _seed_reviewed_analysis(pg_session)
    run_id = uuid4()
    item_id = uuid4()

    pg_session.execute(
        text(
            """
            INSERT INTO dataset_curation_runs
                (id, status, policy, total_candidates_scanned, included_count, excluded_count)
            VALUES
                (:id, 'completed', CAST(:policy AS jsonb), 1, 1, 0)
            """
        ),
        {"id": run_id, "policy": json.dumps({"require_final_human_review": True})},
    )
    insert_item = text(
        """
        INSERT INTO dataset_curation_items
            (id, curation_run_id, sample_id, analysis_run_id, prediction_id, human_review_id,
             petri_image_id, micro_image_id, automatic_label, final_label, review_decision,
             curation_status, provenance)
        VALUES
            (:id, :curation_run_id, :sample_id, :analysis_run_id, :prediction_id, :human_review_id,
             :petri_image_id, :micro_image_id, 'suspicious_growth', 'suspicious_growth', 'confirmed',
             'included', CAST(:provenance AS jsonb))
        """
    )
    pg_session.execute(
        insert_item,
        {
            "id": item_id,
            "curation_run_id": run_id,
            "sample_id": refs["sample_id"],
            "analysis_run_id": refs["analysis_run_id"],
            "prediction_id": refs["prediction_id"],
            "human_review_id": refs["review_id"],
            "petri_image_id": refs["petri_image_id"],
            "micro_image_id": refs["micro_image_id"],
            "provenance": json.dumps({"prediction_is_ground_truth": False}),
        },
    )
    pg_session.flush()

    with pytest.raises(IntegrityError):
        pg_session.execute(
            insert_item,
            {
                "id": uuid4(),
                "curation_run_id": run_id,
                "sample_id": refs["sample_id"],
                "analysis_run_id": refs["analysis_run_id"],
                "prediction_id": refs["prediction_id"],
                "human_review_id": refs["review_id"],
                "petri_image_id": refs["petri_image_id"],
                "micro_image_id": refs["micro_image_id"],
                "provenance": json.dumps({"prediction_is_ground_truth": False}),
            },
        )
        pg_session.flush()
