from datetime import datetime, timezone

import pytest

from blueberry_microid.application.dto.analysis_history_dto import (
    AnalysisHistoryFilters,
    AnalysisHistoryPageDTO,
)


@pytest.mark.parametrize(
    ("total", "page_size", "expected"),
    [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2), (101, 100, 2)],
)
def test_total_pages_is_calculated_with_a_ceiling(total: int, page_size: int, expected: int):
    assert AnalysisHistoryPageDTO.total_pages_for(total, page_size) == expected


def test_filters_normalize_blank_and_surrounding_sample_code():
    filters = AnalysisHistoryFilters(sample_code="  Sample-42  ")
    blank = AnalysisHistoryFilters(sample_code="   ")

    assert filters.sample_code == "Sample-42"
    assert blank.sample_code is None


def test_filters_reject_invalid_pagination_values():
    with pytest.raises(ValueError, match="page must"):
        AnalysisHistoryFilters(page=0)
    with pytest.raises(ValueError, match="page_size"):
        AnalysisHistoryFilters(page_size=101)


def test_filters_reject_an_inverted_date_range():
    later = datetime(2026, 1, 2, tzinfo=timezone.utc)
    earlier = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="created_from"):
        AnalysisHistoryFilters(created_from=later, created_to=earlier)
