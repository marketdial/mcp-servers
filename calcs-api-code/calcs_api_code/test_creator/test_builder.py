"""
TestBuilder - Main orchestrator for AI-driven test creation.

Provides a step-by-step API for creating A/B tests, designed to be
invoked by AI models in a conversational interview flow.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..db import get_db, get_bq
from ..db.models import (
    Test,
    TestCohort,
    TestSitePair,
    DirectCategory,
    DirectItemsAssociation,
    TestTagAssociation,
    TestStatusEnum,
)
from .validators import (
    ValidationError,
    validate_test_name,
    validate_description,
    validate_dates,
    validate_site_count,
    validate_expected_lift,
    validate_metric,
)


@dataclass
class TestDraft:
    """Holds the current state of a test being created."""

    # Basic info
    test_name: Optional[str] = None
    test_description: Optional[str] = None
    test_type: Optional[str] = None

    # Metric
    metric_type: Optional[str] = None
    metric_id: Optional[int] = None
    measurement_type: str = "SITE"

    # Rollout group
    population_include_tag_ids: List[int] = field(default_factory=list)
    population_exclude_tag_ids: List[int] = field(default_factory=list)
    rollout_site_count: Optional[int] = None

    # Treatment selection
    treatment_include_tag_ids: List[int] = field(default_factory=list)
    treatment_exclude_tag_ids: List[int] = field(default_factory=list)
    treatment_site_ids: List[int] = field(default_factory=list)
    control_site_ids: List[int] = field(default_factory=list)
    site_pairs: List[Dict[str, Any]] = field(default_factory=list)

    # Product selection
    hierarchy_ids: List[int] = field(default_factory=list)
    product_ids: List[int] = field(default_factory=list)

    # Schedule
    test_start_date: Optional[date] = None
    impl_weeks: int = 0
    pre_weeks: int = 13
    test_weeks: int = 12

    # Confidence
    anticipated_lift_prcnt: float = 5.0
    estimated_confidence: Optional[float] = None

    # Quality scores
    representativeness: Optional[float] = None
    comparability: Optional[float] = None

    # Options
    exclude_sites_from_other_tests: bool = True
    is_historic: bool = False


class TestBuilder:
    """
    Builder for creating A/B tests step-by-step.

    Example usage:
        builder = TestBuilder(client="RetailCorp")

        # Step 1: Basic info
        builder.set_name("Q1 Promotion Test")
        builder.set_description("Testing 10% discount on beverages")
        builder.set_test_type("Pricing")
        builder.set_metric("SALES")

        # Step 2: Rollout group
        tags = builder.get_available_tags()
        builder.set_rollout_tags(include=[1, 2], exclude=[3])
        print(f"Rollout: {builder.get_rollout_count()} sites")

        # Step 3: Products
        hierarchies = builder.search_hierarchies("beverage")
        builder.set_hierarchies([h['id'] for h in hierarchies])

        # Step 4: Sample
        sample = builder.optimize_sample(target_count=30)
        builder.accept_sample(sample)

        # Step 5: Schedule & Confidence
        builder.set_schedule(start_date="2025-02-03", test_weeks=12)
        confidence = builder.estimate_confidence(expected_lift=5.0)

        # Step 6: Create
        test = builder.create()
        print(f"Created test ID: {test['id']}")
    """

    def __init__(
        self,
        client: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        """
        Initialize the test builder.

        Args:
            client: Client identifier for multi-tenant access
                   (used to load credentials from config file)
            user_id: Optional user ID for created_by tracking
        """
        self.client = client
        self.user_id = user_id
        self.draft = TestDraft()
        self._db = get_db(client=client)

    def reset(self):
        """Reset the builder to start a new test."""
        self.draft = TestDraft()

    # =========================================================================
    # Step 1: Basic Info
    # =========================================================================

    def set_name(self, name: str) -> Dict[str, Any]:
        """
        Set the test name.

        Args:
            name: The test name (must be unique)

        Returns:
            Dict with 'success' and 'message' keys
        """
        is_valid, error = validate_test_name(name, client=self.client)
        if not is_valid:
            return {"success": False, "message": error}

        self.draft.test_name = name.strip()
        return {"success": True, "message": f"Test name set to '{name}'"}

    def set_description(self, description: str) -> Dict[str, Any]:
        """
        Set the test description.

        Args:
            description: A brief description of what the test is measuring

        Returns:
            Dict with 'success' and 'message' keys
        """
        is_valid, error = validate_description(description)
        if not is_valid:
            return {"success": False, "message": error}

        self.draft.test_description = description.strip()
        return {"success": True, "message": "Description set successfully"}

    def set_test_type(self, test_type: str) -> Dict[str, Any]:
        """
        Set the test type category.

        Args:
            test_type: Category like 'Pricing', 'Promotion', 'Layout', etc.

        Returns:
            Dict with 'success' and 'message' keys
        """
        self.draft.test_type = test_type
        return {"success": True, "message": f"Test type set to '{test_type}'"}

    def get_available_test_types(self) -> List[str]:
        """
        Get the list of available test types for this client.

        Returns:
            List of test type strings
        """
        # Query distinct test types from existing tests
        result = self._db.execute("""
            SELECT DISTINCT test_type
            FROM app_tests
            WHERE test_type IS NOT NULL
            ORDER BY test_type
        """)
        return [r["test_type"] for r in result]

    def set_metric(self, metric_type: str) -> Dict[str, Any]:
        """
        Set the primary metric for the test.

        Args:
            metric_type: Metric type like 'SALES', 'UNITS', 'TRANSACTIONS'

        Returns:
            Dict with 'success', 'message', and optionally 'metric' keys
        """
        is_valid, error, metric_info = validate_metric(
            metric_type, self.draft.measurement_type, client=self.client
        )
        if not is_valid:
            return {"success": False, "message": error}

        self.draft.metric_type = metric_type.upper()
        self.draft.metric_id = metric_info["id"]
        return {
            "success": True,
            "message": f"Primary metric set to {metric_type}",
            "metric": metric_info,
        }

    def get_available_metrics(self) -> List[Dict[str, Any]]:
        """
        Get the list of available metrics.

        Returns:
            List of metric dictionaries with 'type', 'level', 'measurement_type'
        """
        result = self._db.execute("""
            SELECT id, type, level, measurement_type, uuid
            FROM app_metrics
            WHERE is_primary = true
            ORDER BY type
        """)
        return result

    # =========================================================================
    # Step 2: Rollout Group
    # =========================================================================

    def get_available_tags(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available tags for filtering sites.

        Args:
            search: Optional search term to filter tags

        Returns:
            List of tag dictionaries with 'id', 'text', 'site_count'
        """
        query = """
            SELECT
                t.id,
                t.text as name,
                t.category,
                t.type as tag_type,
                COUNT(DISTINCT st.site_id) as site_count
            FROM app_tags t
            LEFT JOIN app_site_tags st ON t.id = st.tag_id
        """

        params = {}
        if search:
            query += " WHERE LOWER(t.text) LIKE LOWER(:search)"
            params["search"] = f"%{search}%"

        query += " GROUP BY t.id, t.text, t.category, t.type ORDER BY t.text"

        return self._db.execute(query, params)

    def set_rollout_tags(
        self,
        include: Optional[List[int]] = None,
        exclude: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Set the rollout group by including/excluding tags.

        Args:
            include: Tag IDs to include (sites must have these tags)
            exclude: Tag IDs to exclude (sites must NOT have these tags)

        Returns:
            Dict with 'success', 'message', 'site_count'
        """
        self.draft.population_include_tag_ids = include or []
        self.draft.population_exclude_tag_ids = exclude or []

        # Calculate resulting site count
        site_count = self._calculate_rollout_count()
        self.draft.rollout_site_count = site_count

        if site_count == 0:
            return {
                "success": False,
                "message": "No sites match the selected tags. Try different tags.",
                "site_count": 0,
            }

        return {
            "success": True,
            "message": f"Rollout group set: {site_count} sites",
            "site_count": site_count,
        }

    def set_full_fleet_rollout(self) -> Dict[str, Any]:
        """
        Set rollout to include all testable sites.

        Returns:
            Dict with 'success', 'message', 'site_count'
        """
        self.draft.population_include_tag_ids = []
        self.draft.population_exclude_tag_ids = []

        # Get all testable sites
        result = self._db.execute_one("""
            SELECT COUNT(*) as count FROM dim_sites WHERE testable = true
        """)
        site_count = result["count"] if result else 0
        self.draft.rollout_site_count = site_count

        return {
            "success": True,
            "message": f"Full fleet rollout: {site_count} sites",
            "site_count": site_count,
        }

    def get_rollout_count(self) -> int:
        """Get the current rollout group site count."""
        if self.draft.rollout_site_count is None:
            self.draft.rollout_site_count = self._calculate_rollout_count()
        return self.draft.rollout_site_count

    def _calculate_rollout_count(self) -> int:
        """Calculate the number of sites in the rollout group."""
        include_tags = self.draft.population_include_tag_ids
        exclude_tags = self.draft.population_exclude_tag_ids

        if not include_tags and not exclude_tags:
            # All testable sites
            result = self._db.execute_one("""
                SELECT COUNT(*) as count FROM dim_sites WHERE testable = true
            """)
            return result["count"] if result else 0

        # Build query for tag filtering
        query = """
            SELECT COUNT(DISTINCT s.id) as count
            FROM dim_sites s
            WHERE s.testable = true
        """
        params = {}

        if include_tags:
            query += """
                AND s.id IN (
                    SELECT site_id FROM app_site_tags
                    WHERE tag_id = ANY(:include_tags)
                )
            """
            params["include_tags"] = include_tags

        if exclude_tags:
            query += """
                AND s.id NOT IN (
                    SELECT site_id FROM app_site_tags
                    WHERE tag_id = ANY(:exclude_tags)
                )
            """
            params["exclude_tags"] = exclude_tags

        result = self._db.execute_one(query, params)
        return result["count"] if result else 0

    # =========================================================================
    # Step 3: Product Selection
    # =========================================================================

    def search_hierarchies(
        self,
        search: str,
        level: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search for product hierarchies.

        Args:
            search: Search term to find hierarchies
            level: Optional hierarchy level filter
            limit: Maximum results to return

        Returns:
            List of hierarchy dictionaries
        """
        query = """
            SELECT id, hierarchy_name as name, level, parent_hierarchy_id as parent_id
            FROM dim_hierarchies
            WHERE LOWER(hierarchy_name) LIKE LOWER(:search)
        """
        params = {"search": f"%{search}%"}

        if level is not None:
            query += " AND level = :level"
            params["level"] = level

        query += " ORDER BY level, hierarchy_name LIMIT :limit"
        params["limit"] = limit

        return self._db.execute(query, params)

    def set_hierarchies(self, hierarchy_ids: List[int]) -> Dict[str, Any]:
        """
        Set the product hierarchies for the test.

        Args:
            hierarchy_ids: List of hierarchy IDs to include

        Returns:
            Dict with 'success' and 'message'
        """
        # Validate hierarchies exist
        result = self._db.execute("""
            SELECT id, hierarchy_name as name FROM dim_hierarchies
            WHERE id = ANY(:ids)
        """, {"ids": hierarchy_ids})

        if len(result) != len(hierarchy_ids):
            found_ids = {r["id"] for r in result}
            missing = [h for h in hierarchy_ids if h not in found_ids]
            return {
                "success": False,
                "message": f"Hierarchies not found: {missing}",
            }

        self.draft.hierarchy_ids = hierarchy_ids
        names = [r["name"] for r in result]
        return {
            "success": True,
            "message": f"Selected {len(hierarchy_ids)} hierarchies: {', '.join(names[:3])}{'...' if len(names) > 3 else ''}",
        }

    # =========================================================================
    # Step 4: Sample Optimization (Simplified)
    # =========================================================================

    def get_eligible_sites(self) -> List[Dict[str, Any]]:
        """
        Get sites eligible for treatment based on rollout group.

        Returns:
            List of site dictionaries with id, client_site_id, site_name
        """
        include_tags = self.draft.population_include_tag_ids
        exclude_tags = self.draft.population_exclude_tag_ids

        query = """
            SELECT s.id, s.site_client_id, s.site_name, s.market
            FROM dim_sites s
            WHERE s.testable = true
        """
        params = {}

        if include_tags:
            query += """
                AND s.id IN (
                    SELECT site_id FROM app_site_tags
                    WHERE tag_id = ANY(:include_tags)
                )
            """
            params["include_tags"] = include_tags

        if exclude_tags:
            query += """
                AND s.id NOT IN (
                    SELECT site_id FROM app_site_tags
                    WHERE tag_id = ANY(:exclude_tags)
                )
            """
            params["exclude_tags"] = exclude_tags

        # Exclude sites in active tests if configured
        if self.draft.exclude_sites_from_other_tests:
            query += """
                AND s.id NOT IN (
                    SELECT DISTINCT treatment_site_id FROM app_tests_sites ts
                    JOIN app_test_cohorts tc ON ts.cohort_id = tc.id
                    JOIN app_tests t ON tc.test_id = t.id
                    WHERE t.test_status::text IN ('IN_PROGRESS', 'SCHEDULED')
                    AND t.exclude_sites_from_other_tests = true
                )
            """

        query += " ORDER BY s.site_client_id"
        return self._db.execute(query, params)

    def optimize_sample(
        self,
        target_count: int = 30,
    ) -> Dict[str, Any]:
        """
        Run sample optimization to select treatment sites.

        This is a simplified version of the full MarketDial algorithm.
        It selects treatment sites that are representative of the rollout group.

        Args:
            target_count: Target number of treatment sites

        Returns:
            Dict with 'treatment_sites', 'representativeness', 'suggested_count'
        """
        # Get eligible sites
        eligible_sites = self.get_eligible_sites()
        rollout_count = len(eligible_sites)

        if rollout_count < target_count * 2:
            return {
                "success": False,
                "message": f"Not enough eligible sites ({rollout_count}) for {target_count} treatment sites. Need at least {target_count * 2}.",
                "rollout_count": rollout_count,
            }

        # For now, implement a simple random selection
        # TODO: Replace with proper representativeness-based selection
        import random
        random.seed(42)  # For reproducibility

        selected_sites = random.sample(eligible_sites, min(target_count, rollout_count))

        # Calculate a simple representativeness score
        # (In the full algorithm, this would use site attributes and Gower distance)
        representativeness = min(95.0, 70.0 + (target_count / rollout_count) * 50)

        self.draft.treatment_site_ids = [s["id"] for s in selected_sites]
        self.draft.representativeness = representativeness

        return {
            "success": True,
            "treatment_sites": selected_sites,
            "treatment_count": len(selected_sites),
            "rollout_count": rollout_count,
            "representativeness": round(representativeness, 1),
            "message": f"Selected {len(selected_sites)} treatment sites with {representativeness:.1f}% representativeness",
        }

    def accept_sample(self, sample_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accept the optimized sample.

        Args:
            sample_result: The result from optimize_sample()

        Returns:
            Dict with 'success' and 'message'
        """
        if not sample_result.get("success"):
            return {"success": False, "message": "Cannot accept failed sample"}

        self.draft.treatment_site_ids = [s["id"] for s in sample_result["treatment_sites"]]
        self.draft.representativeness = sample_result["representativeness"]

        return {
            "success": True,
            "message": f"Sample accepted: {len(self.draft.treatment_site_ids)} treatment sites",
        }

    # =========================================================================
    # Step 5: Schedule & Confidence
    # =========================================================================

    def set_schedule(
        self,
        start_date: str,
        test_weeks: int = 12,
        pre_weeks: int = 13,
        impl_weeks: int = 0,
    ) -> Dict[str, Any]:
        """
        Set the test schedule.

        Args:
            start_date: Test start date (YYYY-MM-DD format, must be Monday)
            test_weeks: Number of test period weeks
            pre_weeks: Number of pre-period weeks
            impl_weeks: Number of implementation weeks

        Returns:
            Dict with 'success', 'message', 'dates'
        """
        try:
            parsed_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            return {"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}

        is_valid, error, dates = validate_dates(
            parsed_date, pre_weeks, test_weeks, impl_weeks
        )

        if not is_valid:
            return {"success": False, "message": error}

        self.draft.test_start_date = parsed_date
        self.draft.test_weeks = test_weeks
        self.draft.pre_weeks = pre_weeks
        self.draft.impl_weeks = impl_weeks

        return {
            "success": True,
            "message": f"Schedule set: Test runs {test_weeks} weeks starting {start_date}",
            "dates": {k: v.isoformat() for k, v in dates.items()},
        }

    def estimate_confidence(self, expected_lift: float = 5.0) -> Dict[str, Any]:
        """
        Estimate confidence for the current test configuration.

        Args:
            expected_lift: Expected lift percentage (e.g., 5.0 for 5%)

        Returns:
            Dict with 'confidence', 'message', 'recommendations'
        """
        is_valid, error = validate_expected_lift(expected_lift)
        if not is_valid:
            return {"success": False, "message": error}

        self.draft.anticipated_lift_prcnt = expected_lift

        # Simplified confidence calculation
        # In the full algorithm, this would run simulations
        site_count = len(self.draft.treatment_site_ids)
        week_count = self.draft.test_weeks

        # Basic formula: more sites and weeks = higher confidence
        base_confidence = 50.0
        site_factor = min(site_count / 10, 3.0) * 10  # Up to +30%
        week_factor = min(week_count / 4, 3.0) * 5    # Up to +15%
        lift_factor = min(expected_lift / 2, 2.5) * 2  # Larger lift easier to detect

        confidence = min(99, base_confidence + site_factor + week_factor + lift_factor)
        self.draft.estimated_confidence = confidence

        recommendations = []
        if confidence < 80:
            if site_count < 30:
                recommendations.append(f"Increase treatment sites (currently {site_count})")
            if week_count < 12:
                recommendations.append(f"Extend test duration (currently {week_count} weeks)")
            if expected_lift < 5:
                recommendations.append("Consider if a larger lift is realistic")

        return {
            "success": True,
            "confidence": round(confidence, 1),
            "expected_lift": expected_lift,
            "site_count": site_count,
            "week_count": week_count,
            "message": f"Estimated confidence: {confidence:.1f}%",
            "recommendations": recommendations,
        }

    # =========================================================================
    # Step 6: Create Test
    # =========================================================================

    def validate_draft(self) -> Tuple[bool, List[str]]:
        """
        Validate the current draft is ready to create.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not self.draft.test_name:
            errors.append("Test name is required")
        if not self.draft.test_description:
            errors.append("Test description is required")
        if not self.draft.metric_id:
            errors.append("Primary metric must be selected")
        if not self.draft.treatment_site_ids:
            errors.append("Treatment sites must be selected (run optimize_sample)")
        if not self.draft.test_start_date:
            errors.append("Test schedule must be set")
        if not self.draft.hierarchy_ids and not self.draft.product_ids:
            errors.append("At least one product hierarchy or product must be selected")

        return len(errors) == 0, errors

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current test configuration.

        Returns:
            Dict with all test parameters
        """
        return {
            "test_name": self.draft.test_name,
            "test_description": self.draft.test_description,
            "test_type": self.draft.test_type,
            "metric": self.draft.metric_type,
            "rollout_site_count": self.draft.rollout_site_count,
            "treatment_site_count": len(self.draft.treatment_site_ids),
            "hierarchy_count": len(self.draft.hierarchy_ids),
            "test_start_date": self.draft.test_start_date.isoformat() if self.draft.test_start_date else None,
            "test_weeks": self.draft.test_weeks,
            "pre_weeks": self.draft.pre_weeks,
            "expected_lift": self.draft.anticipated_lift_prcnt,
            "estimated_confidence": self.draft.estimated_confidence,
            "representativeness": self.draft.representativeness,
            "exclude_sites_from_other_tests": self.draft.exclude_sites_from_other_tests,
        }

    def create(self) -> Dict[str, Any]:
        """
        Create the test in the database.

        Returns:
            Dict with 'success', 'test_id', 'message'
        """
        is_valid, errors = self.validate_draft()
        if not is_valid:
            return {
                "success": False,
                "message": "Test configuration is incomplete",
                "errors": errors,
            }

        try:
            # Insert the test
            test_data = {
                "test_name": self.draft.test_name,
                "test_description": self.draft.test_description,
                "test_type": self.draft.test_type,
                "test_visibility": "TEST",
                "test_status": "INCOMPLETE",
                "test_metric_id": self.draft.metric_id,
                "is_historic": self.draft.is_historic,
                "is_market_based_samples": False,
                "is_date_staggered": False,
                "is_repeat_controls": False,
                "site_count": len(self.draft.treatment_site_ids),
                "site_count_range": 15,
                "rollout_group_count": self.draft.rollout_site_count,
                "week_count": self.draft.test_weeks,
                "pre_week_count": self.draft.pre_weeks,
                "anticipated_lift_prcnt": self.draft.anticipated_lift_prcnt,
                "estimated_confidence": self.draft.estimated_confidence,
                "representativeness": self.draft.representativeness,
                "exclude_sites_from_other_tests": self.draft.exclude_sites_from_other_tests,
                "created_by_user_id": self.user_id,
                "date_created": datetime.utcnow(),
                "date_updated": datetime.utcnow(),
            }

            test_id = self._db.insert("app_tests", test_data)

            # Insert cohort
            cohort_data = {
                "test_id": test_id,
                "date_test_start": self.draft.test_start_date,
                "impl_week_count": self.draft.impl_weeks,
                "pre_blockout_week_count": 0,
                "test_blockout_week_count": 0,
            }
            cohort_id = self._db.insert("app_test_cohorts", cohort_data)

            # Insert site pairs (use matched pairs if available, otherwise treatment only)
            if self.draft.site_pairs:
                for pair in self.draft.site_pairs:
                    pair_data = {
                        "cohort_id": cohort_id,
                        "treatment_site_id": pair["treatment_site_id"],
                        "control_site_id": pair.get("control_site_id"),
                    }
                    self._db.insert("app_tests_sites", pair_data)
            else:
                for site_id in self.draft.treatment_site_ids:
                    pair_data = {
                        "cohort_id": cohort_id,
                        "treatment_site_id": site_id,
                        "control_site_id": None,
                    }
                    self._db.insert("app_tests_sites", pair_data)

            # Insert direct category
            if self.draft.hierarchy_ids or self.draft.product_ids:
                category_data = {
                    "test_id": test_id,
                    "name": self.draft.test_name,
                }
                category_id = self._db.insert("app_tests_direct_category", category_data)

                # Insert hierarchy associations (junction table - no id column)
                for hierarchy_id in self.draft.hierarchy_ids:
                    self._db.insert_no_return("app_tests_direct_items", {
                        "direct_category_id": category_id,
                        "hierarchy_id": hierarchy_id,
                    })

            # Insert tag associations
            for tag_id in self.draft.population_include_tag_ids:
                self._db.insert("app_tests_tags_association", {
                    "test_id": test_id,
                    "tag_id": tag_id,
                    "association_type": "POPULATION_INCLUDE",
                })

            for tag_id in self.draft.population_exclude_tag_ids:
                self._db.insert("app_tests_tags_association", {
                    "test_id": test_id,
                    "tag_id": tag_id,
                    "association_type": "POPULATION_EXCLUDE",
                })

            return {
                "success": True,
                "test_id": test_id,
                "message": f"Test '{self.draft.test_name}' created successfully with ID {test_id}",
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create test: {str(e)}",
            }
