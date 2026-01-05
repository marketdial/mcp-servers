"""
Calcs API Client - Direct Python client for code execution patterns.

This client is designed to be imported and used directly in code execution
environments (Claude Code CLI, Gemini code_execution, etc.) without MCP overhead.
"""

import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class CalcsClient:
    """
    Direct API client for Calcs API.

    Import and use in code execution environments:

        from calcs_api_code import CalcsClient

        client = CalcsClient(client="RetailCorp")
        tests = client.get_tests()
        active = [t for t in tests if t["status"] == "active"]
        print(f"Found {len(active)} active tests")

    Environment Variables:
        CALCS_API_TOKEN: Bearer token for authentication (required)
        CALCS_API_BASE_URL: API base URL (optional, defaults to staging)
        CALCS_DEFAULT_CLIENT: Default client identifier (optional)
    """

    def __init__(self, client: Optional[str] = None):
        """
        Initialize the Calcs API client.

        Args:
            client: Optional client identifier for multi-tenant access.
                    Falls back to CALCS_DEFAULT_CLIENT env var if not provided.
        """
        self.base_url = os.getenv(
            "CALCS_API_BASE_URL", "https://staging-app.marketdial.dev/calcs"
        ).rstrip("/")
        self.token = os.getenv("CALCS_API_TOKEN")
        self.default_client = client or os.getenv("CALCS_DEFAULT_CLIENT")

        if not self.token:
            raise ValueError(
                "CALCS_API_TOKEN environment variable is required. "
                "Set it in your environment or .env file."
            )

        # Handle tokens with or without "Bearer " prefix
        auth_header = self.token if self.token.startswith("Bearer ") else f"Bearer {self.token}"

        self._http = httpx.Client(
            headers={"Authorization": auth_header},
            timeout=30.0,
        )

    def _get_headers(self, client: Optional[str] = None) -> Dict[str, str]:
        """Build request headers with optional client identifier."""
        headers = {}
        client_value = client or self.default_client
        if client_value:
            headers["client"] = client_value
        return headers

    def close(self):
        """Close the HTTP client connection."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # =========================================================================
    # Health Check
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Calcs API connection.

        Returns:
            Dict with health status information.

        Example:
            status = client.health_check()
            print(f"API is {'healthy' if status.get('status') == 'ok' else 'down'}")
        """
        resp = self._http.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    # =========================================================================
    # Test Management
    # =========================================================================

    def get_tests(self, client: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all tests from the Calcs API.

        Args:
            client: Optional client identifier (overrides default).

        Returns:
            List of test dictionaries. Each test contains fields like:
            - id: Test ID
            - name: Test name
            - status: Test status (e.g., "active", "completed")
            - created_at: Creation timestamp

        Example:
            tests = client.get_tests()
            active = [t for t in tests if t["status"] == "active"]
            print(f"Found {len(active)} active tests out of {len(tests)} total")
        """
        resp = self._http.get(
            f"{self.base_url}/v1/tests/",
            headers=self._get_headers(client),
        )
        resp.raise_for_status()
        return resp.json()

    def get_test_status(
        self, test_id: int, client: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a specific test.

        Args:
            test_id: The ID of the test to check.
            client: Optional client identifier (overrides default).

        Returns:
            Dict with test status information.

        Example:
            status = client.get_test_status(123)
            print(f"Test 123 status: {status['status']}")
        """
        resp = self._http.get(
            f"{self.base_url}/v1/tests/{test_id}/status",
            headers=self._get_headers(client),
        )
        resp.raise_for_status()
        return resp.json()

    def get_active_clients(self, client: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all active clients.

        Args:
            client: Optional client identifier (overrides default).

        Returns:
            List of client dictionaries.

        Example:
            clients = client.get_active_clients()
            for c in clients:
                print(f"Client: {c['name']}")
        """
        resp = self._http.get(
            f"{self.base_url}/v1/clients/",
            headers=self._get_headers(client),
        )
        resp.raise_for_status()
        return resp.json()

    def get_site_tests(
        self, client_site_id: str, client: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all tests where a site has treatment or control role.

        Args:
            client_site_id: The site ID to look up.
            client: Optional client identifier (overrides default).

        Returns:
            List of test dictionaries for the specified site.

        Example:
            site_tests = client.get_site_tests("STORE-001")
            print(f"Site STORE-001 is in {len(site_tests)} tests")
        """
        resp = self._http.get(
            f"{self.base_url}/v1/sites/{client_site_id}/tests",
            headers=self._get_headers(client),
        )
        resp.raise_for_status()
        return resp.json()

    # =========================================================================
    # Results & Analytics (for future expansion)
    # =========================================================================

    def get_test_results(
        self,
        test_id: int,
        filter_type: str = "OVERALL",
        filter_value: Optional[str] = None,
        client: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get test results with filtering.

        Args:
            test_id: The ID of the test.
            filter_type: Filter type (OVERALL, CUSTOMER_COHORT, CUSTOMER_SEGMENT,
                        SITE_COHORT, SITE_PAIR, FINISHED_COHORT, SITE_TAG).
            filter_value: Optional filter value.
            client: Optional client identifier (overrides default).

        Returns:
            Dict with test results.

        Example:
            results = client.get_test_results(123, filter_type="OVERALL")
            print(f"Lift: {results.get('lift', 'N/A')}")
        """
        params = {}
        if filter_value is not None:
            params["filter_value"] = filter_value

        resp = self._http.get(
            f"{self.base_url}/v1/results/test/{test_id}/{filter_type}",
            headers=self._get_headers(client),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def get_lift_explorer_results(
        self, lift_explorer_id: str, client: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get lift explorer results.

        Args:
            lift_explorer_id: The lift explorer ID.
            client: Optional client identifier (overrides default).

        Returns:
            Dict with lift explorer results.

        Example:
            results = client.get_lift_explorer_results("abc123")
            print(f"Got {len(results.get('data', []))} data points")
        """
        resp = self._http.get(
            f"{self.base_url}/v1/results/lift-explorer/{lift_explorer_id}",
            headers=self._get_headers(client),
        )
        resp.raise_for_status()
        return resp.json()

    # =========================================================================
    # Analysis Management (for future expansion)
    # =========================================================================

    def list_analyses(self, client: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all rollout analyses for the client.

        Args:
            client: Optional client identifier (overrides default).

        Returns:
            List of analysis dictionaries.

        Example:
            analyses = client.list_analyses()
            for a in analyses[:5]:
                print(f"{a['id']}: {a['name']}")
        """
        resp = self._http.get(
            f"{self.base_url}/v1/rollout/analyses",
            headers=self._get_headers(client),
        )
        resp.raise_for_status()
        return resp.json()

    def get_analysis(
        self, analysis_id: str, client: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a specific analysis by ID.

        Args:
            analysis_id: The analysis ID.
            client: Optional client identifier (overrides default).

        Returns:
            Dict with analysis details.

        Example:
            analysis = client.get_analysis("abc123")
            print(f"Analysis: {analysis['name']}")
        """
        resp = self._http.get(
            f"{self.base_url}/v1/rollout/analyses/{analysis_id}",
            headers=self._get_headers(client),
        )
        resp.raise_for_status()
        return resp.json()
