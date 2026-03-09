"""Async HTTP client for the Calcs API."""

import logging
from typing import Any

import httpx

logger = logging.getLogger("calcs-api.client")


class CalcsApiClient:
    """Async client for interacting with the Calcs API.

    Supports multi-tenant access via per-request client header override.
    """

    def __init__(self, base_url: str, token: str, default_client: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.default_client = default_client
        self.http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def close(self):
        await self.http.aclose()

    def _headers(self, client: str = "") -> dict[str, str]:
        """Build request headers with optional client override."""
        c = client or self.default_client
        return {"client": c} if c else {}

    # ── Health ──────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        try:
            r = await self.http.get(f"{self.base_url}/health")
            r.raise_for_status()
            return {"status": "healthy", "data": r.json()}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}

    # ── Test Management ────────────────────────────────────────────────

    async def get_tests(self, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/tests/",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_test_status(self, test_id: int, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/tests/{test_id}/status",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_active_clients(self, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/clients/",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_site_tests(self, client_site_id: str, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/sites/{client_site_id}/tests",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def describe_transactions(self, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/transactions/describe",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Results & Analytics ────────────────────────────────────────────

    async def get_test_results(
        self,
        test_id: int,
        filter_type: str,
        filter_value: str = None,
        client: str = "",
    ) -> dict[str, Any]:
        try:
            url = f"{self.base_url}/v1/results/test/{test_id}/{filter_type}"
            params = {}
            if filter_value:
                params["filter_value"] = filter_value
            r = await self.http.get(url, headers=self._headers(client), params=params)
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_lift_explorer_results(
        self, lift_explorer_id: str, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/results/lift-explorer/{lift_explorer_id}",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_lift_explorer_ids(self, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/lift_explorations/",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_site_pair_lift_manifest(
        self, test_id: int, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/results/test/{test_id}/site-pair-lift-manifest",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_prediction_table(
        self, test_id: int, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/results/test/{test_id}/prediction-table",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_customer_cross(
        self, test_id: int, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/results/test/{test_id}/customer-cross",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def download_all_test_data(
        self, test_id: int, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/results/test-download-all/{test_id}",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Analysis (Rollout Analyzer) ────────────────────────────────────

    async def list_analyses(self, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/rollout/analyses",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def create_analysis(
        self, analysis_data: dict, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.post(
                f"{self.base_url}/v1/rollout/analyses",
                json=analysis_data,
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_analysis(
        self, analysis_id: str, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/rollout/analyses/{analysis_id}",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def update_analysis(
        self, analysis_id: str, analysis_data: dict, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.put(
                f"{self.base_url}/v1/rollout/analyses/{analysis_id}",
                json=analysis_data,
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def delete_analysis(
        self, analysis_id: str, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.delete(
                f"{self.base_url}/v1/rollout/analyses/{analysis_id}",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def run_analysis(
        self, analysis_id: str, force_refresh: bool = False, client: str = ""
    ) -> dict[str, Any]:
        """Run analysis synchronously (waits for completion)."""
        try:
            params = {"force_refresh": str(force_refresh).lower()} if force_refresh else {}
            r = await self.http.post(
                f"{self.base_url}/v1/rollout/analyses/{analysis_id}/run",
                headers=self._headers(client),
                params=params,
                timeout=120.0,  # Analysis can take a while
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def start_analysis(
        self, analysis_id: str, force_refresh: bool = False, client: str = ""
    ) -> dict[str, Any]:
        """Start analysis asynchronously (returns immediately with progress_id)."""
        try:
            params = {"force_refresh": str(force_refresh).lower()} if force_refresh else {}
            r = await self.http.post(
                f"{self.base_url}/v1/rollout/analyses/{analysis_id}/start",
                headers=self._headers(client),
                params=params,
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_analysis_results(
        self, analysis_id: str, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/rollout/analyses/{analysis_id}/results",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Jobs & Monitoring ──────────────────────────────────────────────

    async def get_jobs_summary(
        self, start_date: str, end_date: str, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/jobs/summary",
                params={"start_date": start_date, "end_date": end_date},
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_oldest_job_date(self, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/jobs/oldest-job-date",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_newest_job_date(self, client: str = "") -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/jobs/newest-job-date",
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_clients_jobs_summary(
        self, start_date: str, end_date: str, client: str = ""
    ) -> dict[str, Any]:
        try:
            r = await self.http.get(
                f"{self.base_url}/v1/clients/jobs-summary",
                params={"start_date": start_date, "end_date": end_date},
                headers=self._headers(client),
            )
            r.raise_for_status()
            return {"status": "success", "data": r.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}
