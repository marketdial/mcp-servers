"""
Validation utilities for test creation.

Provides input validation for all test creation parameters,
with clear error messages suitable for AI-driven interactions.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..db import get_db


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str, suggestion: Optional[str] = None):
        self.field = field
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"{field}: {message}")

    def __str__(self):
        result = f"{self.field}: {self.message}"
        if self.suggestion:
            result += f" Suggestion: {self.suggestion}"
        return result


def validate_test_name(
    name: str,
    existing_test_id: Optional[int] = None,
    client: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate a test name.

    Args:
        name: The proposed test name
        existing_test_id: If updating, the ID of the existing test
        client: Client identifier for multi-tenant check

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check length
    if not name or len(name.strip()) == 0:
        return False, "Test name cannot be empty"

    if len(name) > 400:
        return False, "Test name must be 400 characters or less"

    # Check for uniqueness
    db = get_db(client=client)
    query = """
        SELECT id FROM app_tests
        WHERE LOWER(test_name) = LOWER(:name)
        AND test_visibility = 'TEST'
    """
    params = {"name": name.strip()}

    if existing_test_id:
        query += " AND id != :test_id"
        params["test_id"] = existing_test_id

    result = db.execute_one(query, params)

    if result:
        return False, f"A test named '{name}' already exists"

    return True, None


def validate_description(description: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a test description.

    Args:
        description: The test description

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not description or len(description.strip()) == 0:
        return False, "Test description is required"

    if len(description) > 400:
        return False, "Test description must be 400 characters or less"

    return True, None


def validate_dates(
    test_start_date: date,
    pre_weeks: int = 13,
    test_weeks: int = 12,
    impl_weeks: int = 0,
) -> Tuple[bool, Optional[str], Optional[Dict[str, date]]]:
    """
    Validate test dates and calculate derived dates.

    Args:
        test_start_date: The date the test period begins
        pre_weeks: Number of pre-period weeks
        test_weeks: Number of test period weeks
        impl_weeks: Number of implementation weeks (usually 0 or 1)

    Returns:
        Tuple of (is_valid, error_message, calculated_dates)
    """
    today = date.today()

    # Test start must be in the future (at least a week out)
    min_start_date = today + timedelta(weeks=1)
    if test_start_date < min_start_date:
        return (
            False,
            f"Test start date must be at least 1 week in the future ({min_start_date})",
            None,
        )

    # Test start should be a Monday
    if test_start_date.weekday() != 0:  # 0 = Monday
        # Find the next Monday
        days_until_monday = (7 - test_start_date.weekday()) % 7
        suggested_date = test_start_date + timedelta(days=days_until_monday)
        return (
            False,
            f"Test start date should be a Monday. Suggested: {suggested_date}",
            None,
        )

    # Validate week counts
    if pre_weeks < 8:
        return False, "Pre-period must be at least 8 weeks for reliable results", None

    if test_weeks < 4:
        return False, "Test period must be at least 4 weeks", None

    if test_weeks > 52:
        return False, "Test period cannot exceed 52 weeks", None

    # Calculate dates
    impl_start = test_start_date - timedelta(weeks=impl_weeks)
    pre_start = impl_start - timedelta(weeks=pre_weeks)
    test_end = test_start_date + timedelta(weeks=test_weeks) - timedelta(days=1)

    calculated_dates = {
        "pre_period_start": pre_start,
        "implementation_start": impl_start,
        "implementation_end": test_start_date - timedelta(days=1) if impl_weeks > 0 else test_start_date,
        "test_start": test_start_date,
        "test_end": test_end,
    }

    return True, None, calculated_dates


def validate_site_count(
    count: int,
    rollout_count: int,
    min_sites: int = 10,
    max_percentage: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """
    Validate the number of treatment sites.

    Args:
        count: Requested number of treatment sites
        rollout_count: Total sites in the rollout group
        min_sites: Minimum required treatment sites
        max_percentage: Maximum percentage of rollout that can be treatment

    Returns:
        Tuple of (is_valid, error_message)
    """
    if count < min_sites:
        return False, f"Need at least {min_sites} treatment sites for reliable results"

    max_treatment = int(rollout_count * max_percentage)
    if count > max_treatment:
        return (
            False,
            f"Treatment sites ({count}) cannot exceed {int(max_percentage * 100)}% "
            f"of rollout group ({max_treatment} sites)",
        )

    return True, None


def validate_expected_lift(lift: float) -> Tuple[bool, Optional[str]]:
    """
    Validate the expected lift percentage.

    Args:
        lift: Expected lift as a percentage (e.g., 5.0 for 5%)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if lift <= 0:
        return False, "Expected lift must be positive"

    if lift > 100:
        return False, "Expected lift seems unrealistic (>100%). Are you sure?"

    if lift < 0.5:
        return (
            False,
            "Expected lift is very small (<0.5%). This will be difficult to detect. "
            "Consider a longer test or more sites.",
        )

    return True, None


def validate_metric(
    metric_type: str,
    measurement_type: str = "SITE",
    client: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate and look up a metric.

    Args:
        metric_type: Type of metric (e.g., 'SALES', 'UNITS')
        measurement_type: 'SITE' or 'CUSTOMER'
        client: Client identifier for database connection

    Returns:
        Tuple of (is_valid, error_message, metric_info)
    """
    db = get_db(client=client)

    query = """
        SELECT id, type, level, measurement_type, uuid
        FROM app_metrics
        WHERE UPPER(type::text) = UPPER(:metric_type)
        AND UPPER(measurement_type::text) = UPPER(:measurement_type)
        AND is_primary = true
        LIMIT 1
    """

    result = db.execute_one(query, {
        "metric_type": metric_type,
        "measurement_type": measurement_type,
    })

    if not result:
        # Get available metrics
        available = db.execute("""
            SELECT DISTINCT type FROM app_metrics
            WHERE UPPER(measurement_type::text) = UPPER(:measurement_type)
            AND is_primary = true
        """, {"measurement_type": measurement_type})

        available_types = [r["type"] for r in available]
        return (
            False,
            f"Metric '{metric_type}' not found. Available: {', '.join(available_types)}",
            None,
        )

    return True, None, result


def validate_tags(
    tag_ids: List[int],
    required_sites: int = 0,
    client: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate that tags exist and have enough sites.

    Args:
        tag_ids: List of tag IDs
        required_sites: Minimum required sites (0 to skip check)
        client: Client identifier for database connection

    Returns:
        Tuple of (is_valid, error_message, site_count)
    """
    if not tag_ids:
        return True, None, None

    db = get_db(client=client)

    # Check tags exist
    query = """
        SELECT id, text FROM app_tags WHERE id = ANY(:tag_ids)
    """
    tags = db.execute(query, {"tag_ids": tag_ids})

    if len(tags) != len(tag_ids):
        found_ids = {t["id"] for t in tags}
        missing = [tid for tid in tag_ids if tid not in found_ids]
        return False, f"Tags not found: {missing}", None

    # Count sites with these tags
    site_query = """
        SELECT COUNT(DISTINCT site_id) as count
        FROM app_site_tags
        WHERE tag_id = ANY(:tag_ids)
    """
    result = db.execute_one(site_query, {"tag_ids": tag_ids})
    site_count = result["count"] if result else 0

    if required_sites > 0 and site_count < required_sites:
        return (
            False,
            f"Selected tags only have {site_count} sites, need at least {required_sites}",
            site_count,
        )

    return True, None, site_count
