"""
High-level Interview API for AI-driven test creation.

Provides a simplified interface designed for AI models to conduct
test creation interviews with users.
"""

import os
from typing import Any, Dict, List, Optional

from .test_creator import TestBuilder
from .test_creator.sample_optimizer import SampleOptimizer


class TestInterview:
    """
    High-level interface for AI-driven test creation.

    This class wraps TestBuilder with additional conveniences for
    AI-driven conversations:
    - Automatic state tracking
    - Helpful error messages
    - Progress indicators
    - Undo/reset capabilities

    Example:
        interview = TestInterview(client="RetailCorp")

        # Step 1: Basic info
        interview.set_basics(
            name="Q1 Promo Test",
            description="Testing 10% discount",
            test_type="Promotion",
            metric="SALES"
        )

        # Step 2: Rollout
        interview.set_rollout(include_tags=[1, 2])

        # Step 3: Products
        interview.set_products(hierarchy_search="beverages")

        # Step 4: Sample
        interview.optimize_and_accept(target_sites=30)

        # Step 5: Schedule
        interview.set_schedule("2025-02-03", test_weeks=12)

        # Step 6: Create
        result = interview.finalize()
    """

    def __init__(
        self,
        client: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        """
        Start a new test creation interview.

        Args:
            client: Client identifier
            user_id: User ID for tracking who created the test
        """
        self.client = client or os.getenv("CALCS_DEFAULT_CLIENT")
        self.user_id = user_id
        self.builder = TestBuilder(client=self.client, user_id=user_id)
        self.optimizer = SampleOptimizer(client=self.client)
        self._completed_steps = set()
        self._sample_result = None

    def reset(self):
        """Start over with a fresh interview."""
        self.builder.reset()
        self._completed_steps = set()
        self._sample_result = None

    @property
    def progress(self) -> Dict[str, Any]:
        """Get current interview progress."""
        steps = [
            ("basics", "Basic Information"),
            ("rollout", "Rollout Group"),
            ("products", "Product Selection"),
            ("sample", "Sample Optimization"),
            ("schedule", "Schedule & Confidence"),
            ("ready", "Ready to Create"),
        ]

        return {
            "completed": list(self._completed_steps),
            "current": self._get_current_step(),
            "steps": [
                {
                    "id": step_id,
                    "name": step_name,
                    "completed": step_id in self._completed_steps,
                }
                for step_id, step_name in steps
            ],
            "can_create": self._can_create(),
        }

    def _get_current_step(self) -> str:
        """Get the current step in the interview."""
        if "schedule" in self._completed_steps:
            return "ready"
        elif "sample" in self._completed_steps:
            return "schedule"
        elif "products" in self._completed_steps:
            return "sample"
        elif "rollout" in self._completed_steps:
            return "products"
        elif "basics" in self._completed_steps:
            return "rollout"
        else:
            return "basics"

    def _can_create(self) -> bool:
        """Check if test can be created."""
        is_valid, _ = self.builder.validate_draft()
        return is_valid

    # =========================================================================
    # Step 1: Basic Information
    # =========================================================================

    def set_basics(
        self,
        name: str,
        description: str,
        test_type: str = "General",
        metric: str = "SALES",
    ) -> Dict[str, Any]:
        """
        Set basic test information in one call.

        Args:
            name: Test name (must be unique)
            description: Test description/hypothesis
            test_type: Test category (Pricing, Promotion, etc.)
            metric: Primary metric (SALES, UNITS, TRANSACTIONS)

        Returns:
            Result with success status and any errors
        """
        results = []

        name_result = self.builder.set_name(name)
        results.append(("name", name_result))

        if name_result["success"]:
            desc_result = self.builder.set_description(description)
            results.append(("description", desc_result))

            if desc_result["success"]:
                type_result = self.builder.set_test_type(test_type)
                results.append(("test_type", type_result))

                metric_result = self.builder.set_metric(metric)
                results.append(("metric", metric_result))

        # Check if all succeeded
        all_success = all(r[1]["success"] for r in results)
        if all_success:
            self._completed_steps.add("basics")

        errors = [f"{field}: {r['message']}" for field, r in results if not r["success"]]

        return {
            "success": all_success,
            "message": "Basic information set successfully" if all_success else "; ".join(errors),
            "details": dict(results),
        }

    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get available metrics."""
        return self.builder.get_available_metrics()

    def get_test_types(self) -> List[str]:
        """Get available test types."""
        return self.builder.get_available_test_types()

    # =========================================================================
    # Step 2: Rollout Group
    # =========================================================================

    def set_rollout(
        self,
        include_tags: Optional[List[int]] = None,
        exclude_tags: Optional[List[int]] = None,
        full_fleet: bool = False,
    ) -> Dict[str, Any]:
        """
        Set the rollout group.

        Args:
            include_tags: Tag IDs to include
            exclude_tags: Tag IDs to exclude
            full_fleet: If True, use all testable sites

        Returns:
            Result with site count
        """
        if full_fleet:
            result = self.builder.set_full_fleet_rollout()
        else:
            result = self.builder.set_rollout_tags(include_tags, exclude_tags)

        if result["success"]:
            self._completed_steps.add("rollout")

        return result

    def get_tags(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available tags, optionally filtered by search."""
        return self.builder.get_available_tags(search)

    def get_rollout_count(self) -> int:
        """Get current rollout site count."""
        return self.builder.get_rollout_count()

    # =========================================================================
    # Step 3: Product Selection
    # =========================================================================

    def set_products(
        self,
        hierarchy_ids: Optional[List[int]] = None,
        hierarchy_search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set product selection for the test.

        Args:
            hierarchy_ids: Specific hierarchy IDs to use
            hierarchy_search: Search term to find and use hierarchies

        Returns:
            Result with selected products
        """
        if hierarchy_search and not hierarchy_ids:
            hierarchies = self.builder.search_hierarchies(hierarchy_search)
            if not hierarchies:
                return {
                    "success": False,
                    "message": f"No hierarchies found matching '{hierarchy_search}'",
                }
            hierarchy_ids = [h["id"] for h in hierarchies[:5]]  # Take top 5

        if not hierarchy_ids:
            return {
                "success": False,
                "message": "Must provide hierarchy_ids or hierarchy_search",
            }

        result = self.builder.set_hierarchies(hierarchy_ids)

        if result["success"]:
            self._completed_steps.add("products")

        return result

    def search_products(self, search: str, level: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for product hierarchies."""
        return self.builder.search_hierarchies(search, level)

    # =========================================================================
    # Step 4: Sample Optimization
    # =========================================================================

    def optimize_sample(self, target_sites: int = 30) -> Dict[str, Any]:
        """
        Run sample optimization.

        Args:
            target_sites: Target number of treatment sites

        Returns:
            Optimization result with sites and representativeness
        """
        # Get rollout site IDs
        eligible = self.builder.get_eligible_sites()
        rollout_ids = [s["id"] for s in eligible]

        # Run optimization
        result = self.optimizer.optimize_full_sample(
            rollout_site_ids=rollout_ids,
            target_treatment_count=target_sites,
            n_controls=1,
        )

        if result.success:
            self._sample_result = result
            return {
                "success": True,
                "treatment_count": len(result.treatment_sites),
                "representativeness": result.representativeness,
                "comparability": result.comparability,
                "message": result.message,
                "treatment_sites": result.treatment_sites[:10],  # First 10 for display
            }
        else:
            return {
                "success": False,
                "message": result.message,
            }

    def accept_sample(self) -> Dict[str, Any]:
        """Accept the optimized sample."""
        if not self._sample_result:
            return {
                "success": False,
                "message": "No sample to accept. Run optimize_sample first.",
            }

        # Update builder with sample
        self.builder.draft.treatment_site_ids = [
            s["id"] for s in self._sample_result.treatment_sites
        ]
        self.builder.draft.representativeness = self._sample_result.representativeness
        self.builder.draft.comparability = self._sample_result.comparability
        self.builder.draft.site_pairs = self._sample_result.site_pairs or []

        self._completed_steps.add("sample")

        return {
            "success": True,
            "message": f"Sample accepted: {len(self.builder.draft.treatment_site_ids)} treatment sites",
        }

    def optimize_and_accept(self, target_sites: int = 30) -> Dict[str, Any]:
        """Optimize and immediately accept the sample."""
        opt_result = self.optimize_sample(target_sites)
        if not opt_result["success"]:
            return opt_result

        return self.accept_sample()

    # =========================================================================
    # Step 5: Schedule & Confidence
    # =========================================================================

    def set_schedule(
        self,
        start_date: str,
        test_weeks: int = 12,
        pre_weeks: int = 13,
        expected_lift: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Set test schedule and get confidence estimate.

        Args:
            start_date: Test start date (YYYY-MM-DD, must be Monday)
            test_weeks: Test duration in weeks
            pre_weeks: Pre-period weeks
            expected_lift: Expected lift percentage

        Returns:
            Result with schedule and confidence info
        """
        schedule_result = self.builder.set_schedule(
            start_date=start_date,
            test_weeks=test_weeks,
            pre_weeks=pre_weeks,
        )

        if not schedule_result["success"]:
            return schedule_result

        confidence_result = self.builder.estimate_confidence(expected_lift)

        if confidence_result["success"]:
            self._completed_steps.add("schedule")

        return {
            "success": True,
            "schedule": schedule_result.get("dates"),
            "confidence": confidence_result.get("confidence"),
            "expected_lift": expected_lift,
            "recommendations": confidence_result.get("recommendations", []),
            "message": f"Schedule set. Estimated confidence: {confidence_result.get('confidence')}%",
        }

    # =========================================================================
    # Step 6: Finalize
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get a complete summary of the test configuration."""
        return self.builder.get_summary()

    def validate(self) -> Dict[str, Any]:
        """Validate the current configuration."""
        is_valid, errors = self.builder.validate_draft()
        return {
            "valid": is_valid,
            "errors": errors,
            "message": "Ready to create" if is_valid else f"Not ready: {'; '.join(errors)}",
        }

    def finalize(self) -> Dict[str, Any]:
        """Create the test in the database."""
        # Validate first
        validation = self.validate()
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"],
                "errors": validation["errors"],
            }

        # Create
        result = self.builder.create()

        if result["success"]:
            return {
                "success": True,
                "test_id": result["test_id"],
                "message": result["message"],
                "summary": self.get_summary(),
            }
        else:
            return result


def get_system_prompt() -> str:
    """
    Get the AI system prompt for test creation interviews.

    Returns:
        The system prompt markdown as a string
    """
    import importlib.resources as pkg_resources

    try:
        # Python 3.9+
        prompt_file = pkg_resources.files("calcs_api_code.prompts").joinpath("test_creation_guide.md")
        return prompt_file.read_text()
    except (AttributeError, TypeError):
        # Fallback for older Python or if resources not found
        import os
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "prompts",
            "test_creation_guide.md"
        )
        with open(prompt_path, "r") as f:
            return f.read()
