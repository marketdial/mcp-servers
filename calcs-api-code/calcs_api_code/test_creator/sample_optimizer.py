"""
Sample Optimizer - Site selection and matching algorithms.

Provides algorithms for:
1. Treatment site selection optimized for representativeness
2. Control site matching using similarity metrics
3. Representativeness and comparability scoring
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler

from ..db import get_db


@dataclass
class SampleResult:
    """Result from sample optimization."""
    treatment_sites: List[Dict[str, Any]]
    control_sites: Optional[List[Dict[str, Any]]] = None
    site_pairs: Optional[List[Dict[str, Any]]] = None
    representativeness: float = 0.0
    comparability: Optional[float] = None
    success: bool = True
    message: str = ""


class SampleOptimizer:
    """
    Optimizes site selection for A/B tests.

    Uses site attributes to select treatment sites that are representative
    of the rollout group, and matches them with similar control sites.
    """

    def __init__(self, client: Optional[str] = None):
        """
        Initialize the sample optimizer.

        Args:
            client: Client identifier for multi-tenant access
                   (used to load credentials from config file)
        """
        self.client = client
        self._db = get_db(client=client)

    def get_site_attributes(
        self,
        site_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Get site attributes as a DataFrame.

        Args:
            site_ids: Optional list of site IDs to filter

        Returns:
            DataFrame with site_id and attribute columns
        """
        # Get variable weightings (which attributes to use)
        weights_query = """
            SELECT variable_name, weighting as weight
            FROM app_variable_set_weightings
            WHERE weighting > 0
            ORDER BY weighting DESC
            LIMIT 20
        """
        weights = self._db.execute(weights_query)

        if not weights:
            # Fallback to basic attributes
            weights = [
                {"variable_name": "latitude", "weight": 1.0},
                {"variable_name": "longitude", "weight": 1.0},
            ]

        # Build query for site attributes - use basic geographic data from dim_sites
        # Some clients don't have app_site_attributes table
        query = """
            SELECT
                s.id as site_id,
                s.latitude,
                s.longitude
            FROM dim_sites s
            WHERE s.testable = true
        """

        params = {}
        if site_ids:
            query += " AND s.id = ANY(:site_ids)"
            params["site_ids"] = site_ids

        result = self._db.execute(query, params)
        df = pd.DataFrame(result)

        # Convert Decimal columns to float (pandas doesn't recognize Decimal as numeric)
        for col in ['latitude', 'longitude']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def calculate_representativeness(
        self,
        treatment_site_ids: List[int],
        rollout_site_ids: List[int],
    ) -> float:
        """
        Calculate representativeness of treatment sites vs rollout group.

        Uses the Gower distance to compare distributions of site attributes
        between the treatment sample and the full rollout group.

        Args:
            treatment_site_ids: List of treatment site IDs
            rollout_site_ids: List of all rollout site IDs

        Returns:
            Representativeness score (0-100, higher is better)
        """
        if not treatment_site_ids or not rollout_site_ids:
            return 0.0

        # Get attributes for both groups
        treatment_df = self.get_site_attributes(treatment_site_ids)
        rollout_df = self.get_site_attributes(rollout_site_ids)

        if treatment_df.empty or rollout_df.empty:
            return 50.0  # Default if no attributes

        # Select numeric columns for comparison
        numeric_cols = treatment_df.select_dtypes(include=[np.number]).columns
        numeric_cols = [c for c in numeric_cols if c != "site_id"]

        if not numeric_cols:
            return 50.0

        # Get numeric data
        treatment_data = treatment_df[numeric_cols].values
        rollout_data = rollout_df[numeric_cols].values

        # Handle missing values
        treatment_data = np.nan_to_num(treatment_data, nan=0)
        rollout_data = np.nan_to_num(rollout_data, nan=0)

        # Standardize
        scaler = StandardScaler()
        combined = np.vstack([treatment_data, rollout_data])
        scaler.fit(combined)

        treatment_scaled = scaler.transform(treatment_data)
        rollout_scaled = scaler.transform(rollout_data)

        # Calculate mean vectors
        treatment_mean = treatment_scaled.mean(axis=0)
        rollout_mean = rollout_scaled.mean(axis=0)

        # Calculate distance between means
        distance = np.linalg.norm(treatment_mean - rollout_mean)

        # Convert to similarity score (0-100)
        # Smaller distance = higher representativeness
        max_distance = 5.0  # Empirical threshold
        score = max(0, min(100, 100 * (1 - distance / max_distance)))

        return round(score, 1)

    def select_representative_sites(
        self,
        rollout_site_ids: List[int],
        target_count: int,
        exclude_site_ids: Optional[List[int]] = None,
    ) -> SampleResult:
        """
        Select treatment sites that are representative of the rollout group.

        Uses k-medoids-like selection to choose sites that minimize
        the distance between the sample distribution and the rollout distribution.

        Args:
            rollout_site_ids: All sites in the rollout group
            target_count: Number of treatment sites to select
            exclude_site_ids: Sites to exclude (e.g., in other tests)

        Returns:
            SampleResult with selected treatment sites
        """
        if target_count >= len(rollout_site_ids):
            return SampleResult(
                treatment_sites=[],
                success=False,
                message=f"Target count ({target_count}) must be less than rollout size ({len(rollout_site_ids)})",
            )

        # Filter out excluded sites
        available_ids = rollout_site_ids
        if exclude_site_ids:
            available_ids = [s for s in rollout_site_ids if s not in exclude_site_ids]

        if target_count > len(available_ids):
            return SampleResult(
                treatment_sites=[],
                success=False,
                message=f"Not enough available sites ({len(available_ids)}) after exclusions",
            )

        # Get site attributes
        df = self.get_site_attributes(available_ids)

        if df.empty:
            # Fallback to random selection
            import random
            random.seed(42)
            selected_ids = random.sample(available_ids, target_count)
            sites = self._db.execute("""
                SELECT id, site_client_id, site_name, market
                FROM dim_sites WHERE id = ANY(:ids)
            """, {"ids": selected_ids})

            return SampleResult(
                treatment_sites=sites,
                representativeness=70.0,
                success=True,
                message="Selected sites using random sampling (no attributes available)",
            )

        # Select numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_cols = [c for c in numeric_cols if c != "site_id"]

        if not numeric_cols:
            # Fallback to random
            import random
            random.seed(42)
            selected_ids = random.sample(available_ids, target_count)
            sites = self._db.execute("""
                SELECT id, site_client_id, site_name, market
                FROM dim_sites WHERE id = ANY(:ids)
            """, {"ids": selected_ids})

            return SampleResult(
                treatment_sites=sites,
                representativeness=70.0,
                success=True,
                message="Selected sites using random sampling",
            )

        # Prepare data for selection
        data = df[numeric_cols].values
        data = np.nan_to_num(data, nan=0)

        # Standardize
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)

        # Calculate rollout centroid
        rollout_centroid = data_scaled.mean(axis=0)

        # Use stratified sampling based on distance from centroid
        # Divide sites into strata and sample from each
        distances = np.linalg.norm(data_scaled - rollout_centroid, axis=1)

        # Create strata (quintiles)
        n_strata = min(5, target_count)
        strata_bounds = np.percentile(distances, np.linspace(0, 100, n_strata + 1))

        selected_indices = []
        sites_per_stratum = target_count // n_strata
        extra = target_count % n_strata

        for i in range(n_strata):
            mask = (distances >= strata_bounds[i]) & (distances < strata_bounds[i + 1])
            if i == n_strata - 1:  # Include boundary for last stratum
                mask = (distances >= strata_bounds[i]) & (distances <= strata_bounds[i + 1])

            stratum_indices = np.where(mask)[0]

            # How many to select from this stratum
            n_select = sites_per_stratum + (1 if i < extra else 0)
            n_select = min(n_select, len(stratum_indices))

            if n_select > 0:
                # Select sites closest to stratum mean
                stratum_data = data_scaled[stratum_indices]
                stratum_centroid = stratum_data.mean(axis=0)
                stratum_distances = np.linalg.norm(stratum_data - stratum_centroid, axis=1)
                best_indices = stratum_distances.argsort()[:n_select]
                selected_indices.extend(stratum_indices[best_indices])

        # Fill remaining if needed
        while len(selected_indices) < target_count:
            remaining = [i for i in range(len(df)) if i not in selected_indices]
            if not remaining:
                break
            selected_indices.append(remaining[0])

        selected_ids = df.iloc[selected_indices]["site_id"].tolist()

        # Get site details
        sites = self._db.execute("""
            SELECT id, site_client_id, site_name, market
            FROM dim_sites WHERE id = ANY(:ids)
        """, {"ids": selected_ids})

        # Calculate representativeness
        representativeness = self.calculate_representativeness(
            selected_ids, rollout_site_ids
        )

        return SampleResult(
            treatment_sites=sites,
            representativeness=representativeness,
            success=True,
            message=f"Selected {len(sites)} representative treatment sites",
        )

    def match_control_sites(
        self,
        treatment_site_ids: List[int],
        available_control_ids: List[int],
        n_controls: int = 1,
    ) -> SampleResult:
        """
        Match control sites to treatment sites based on similarity.

        Args:
            treatment_site_ids: Treatment site IDs to match
            available_control_ids: Pool of available control sites
            n_controls: Number of control sites per treatment site

        Returns:
            SampleResult with site pairs and comparability score
        """
        if not treatment_site_ids or not available_control_ids:
            return SampleResult(
                treatment_sites=[],
                success=False,
                message="Need both treatment and control sites",
            )

        # Get attributes for both groups
        treatment_df = self.get_site_attributes(treatment_site_ids)
        control_df = self.get_site_attributes(available_control_ids)

        if treatment_df.empty or control_df.empty:
            return SampleResult(
                treatment_sites=[],
                success=False,
                message="Could not get site attributes",
            )

        # Select numeric columns
        numeric_cols = treatment_df.select_dtypes(include=[np.number]).columns
        numeric_cols = [c for c in numeric_cols if c != "site_id"]

        if not numeric_cols:
            return SampleResult(
                treatment_sites=[],
                success=False,
                message="No numeric attributes for matching",
            )

        # Prepare data
        treatment_data = treatment_df[numeric_cols].values
        control_data = control_df[numeric_cols].values

        treatment_data = np.nan_to_num(treatment_data, nan=0)
        control_data = np.nan_to_num(control_data, nan=0)

        # Standardize
        scaler = StandardScaler()
        combined = np.vstack([treatment_data, control_data])
        scaler.fit(combined)

        treatment_scaled = scaler.transform(treatment_data)
        control_scaled = scaler.transform(control_data)

        # Calculate pairwise distances
        distances = cdist(treatment_scaled, control_scaled, metric="euclidean")

        # Match each treatment to closest controls
        site_pairs = []
        used_controls = set()
        comparabilities = []

        for i, treatment_id in enumerate(treatment_df["site_id"]):
            treatment_distances = distances[i].copy()

            for c in range(n_controls):
                # Find closest unused control
                for _ in range(len(treatment_distances)):
                    best_idx = treatment_distances.argmin()
                    control_id = control_df.iloc[best_idx]["site_id"]

                    if control_id not in used_controls:
                        # Calculate similarity (0-100)
                        similarity = max(0, 100 * (1 - treatment_distances[best_idx] / 5.0))
                        comparabilities.append(similarity)

                        site_pairs.append({
                            "treatment_site_id": int(treatment_id),
                            "control_site_id": int(control_id),
                            "comparability": round(similarity, 1),
                        })
                        used_controls.add(control_id)
                        break
                    else:
                        treatment_distances[best_idx] = float("inf")

        avg_comparability = np.mean(comparabilities) if comparabilities else 0

        return SampleResult(
            treatment_sites=treatment_df[["site_id"]].to_dict("records"),
            control_sites=list(used_controls),
            site_pairs=site_pairs,
            comparability=round(avg_comparability, 1),
            success=True,
            message=f"Matched {len(site_pairs)} site pairs with {avg_comparability:.1f}% comparability",
        )

    def get_excluded_sites(self) -> List[int]:
        """
        Get sites that should be excluded (in active tests).

        Returns:
            List of site IDs to exclude
        """
        result = self._db.execute("""
            SELECT DISTINCT ts.treatment_site_id as site_id
            FROM app_tests_sites ts
            JOIN app_test_cohorts tc ON ts.cohort_id = tc.id
            JOIN app_tests t ON tc.test_id = t.id
            WHERE t.test_status IN ('IN_PROGRESS', 'SCHEDULED', 'IN_IMPLEMENTATION')
            AND t.exclude_sites_from_other_tests = true
            AND t.test_visibility = 'TEST'
        """)
        return [r["site_id"] for r in result]

    def optimize_full_sample(
        self,
        rollout_site_ids: List[int],
        target_treatment_count: int,
        n_controls: int = 1,
        exclude_active_tests: bool = True,
    ) -> SampleResult:
        """
        Full sample optimization: select treatment and match controls.

        Args:
            rollout_site_ids: All sites in the rollout group
            target_treatment_count: Number of treatment sites
            n_controls: Number of controls per treatment
            exclude_active_tests: Whether to exclude sites in active tests

        Returns:
            Complete SampleResult with treatment, control, and pairs
        """
        # Get excluded sites
        excluded = []
        if exclude_active_tests:
            excluded = self.get_excluded_sites()

        # Select treatment sites
        treatment_result = self.select_representative_sites(
            rollout_site_ids=rollout_site_ids,
            target_count=target_treatment_count,
            exclude_site_ids=excluded,
        )

        if not treatment_result.success:
            return treatment_result

        treatment_ids = [s["id"] for s in treatment_result.treatment_sites]

        # Get available control sites (not treatment, not excluded)
        all_excluded = set(excluded + treatment_ids)
        available_controls = [s for s in rollout_site_ids if s not in all_excluded]

        # Match controls
        match_result = self.match_control_sites(
            treatment_site_ids=treatment_ids,
            available_control_ids=available_controls,
            n_controls=n_controls,
        )

        return SampleResult(
            treatment_sites=treatment_result.treatment_sites,
            control_sites=match_result.control_sites,
            site_pairs=match_result.site_pairs,
            representativeness=treatment_result.representativeness,
            comparability=match_result.comparability,
            success=True,
            message=f"Optimized sample: {len(treatment_ids)} treatment sites, "
                    f"{treatment_result.representativeness:.1f}% representativeness, "
                    f"{match_result.comparability:.1f}% comparability",
        )
