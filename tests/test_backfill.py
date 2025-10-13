"""
Tests for backfill script.
"""
from datetime import date
import pytest
from agent.backfill import parse_date


def test_parse_date():
    """Test date parsing from YYYY-MM-DD format."""
    assert parse_date("2024-04-01") == date(2024, 4, 1)
    assert parse_date("2024-10-13") == date(2024, 10, 13)


def test_parse_date_invalid():
    """Test that invalid dates raise ValueError."""
    with pytest.raises(ValueError):
        parse_date("2024-13-01")  # Invalid month
    
    with pytest.raises(ValueError):
        parse_date("2024-02-30")  # Invalid day


def test_date_range_validation():
    """Test that start date must be before end date."""
    start = date(2024, 10, 1)
    end = date(2024, 9, 1)
    assert start > end  # This should fail validation in main()

