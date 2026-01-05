"""
BigQuery client for Calcs API operations.

Provides access to metric data and other BigQuery-based analytics
needed for sample optimization and test configuration.
Supports loading credentials from secrets/configs/staging.config.json.
"""

import os
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig

from .connection import get_client_db_config, load_config

# Load environment variables
load_dotenv()

# Global BigQuery client instances (per-client)
_bq_instances: Dict[str, "BigQueryClient"] = {}


class BigQueryClient:
    """
    BigQuery client for Calcs API operations.

    Environment Variables:
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
        GCP_PROJECT: Google Cloud project ID
        BQ_DATASET: Default BigQuery dataset (optional)
    """

    def __init__(
        self,
        project: Optional[str] = None,
        dataset: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize BigQuery client.

        Args:
            project: GCP project ID (or use GCP_PROJECT env var)
            dataset: Default dataset (or use BQ_DATASET env var)
            credentials_path: Path to service account JSON (or use GOOGLE_APPLICATION_CREDENTIALS)
        """
        self._project = project or os.getenv("GCP_PROJECT")
        self._dataset = dataset or os.getenv("BQ_DATASET")

        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        if not self._project:
            raise ValueError(
                "BigQuery requires GCP_PROJECT environment variable or project parameter"
            )

        self._client: Optional[bigquery.Client] = None

    @property
    def client(self) -> bigquery.Client:
        """Get or create the BigQuery client."""
        if self._client is None:
            self._client = bigquery.Client(project=self._project)
        return self._client

    def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        """
        Execute a BigQuery SQL query and return results as a DataFrame.

        Args:
            sql: SQL query string
            params: Optional query parameters
            labels: Optional job labels for tracking

        Returns:
            pandas DataFrame with query results
        """
        job_config = QueryJobConfig()

        if labels:
            job_config.labels = labels

        if params:
            # Convert params to BigQuery query parameters
            query_params = []
            for name, value in params.items():
                if isinstance(value, int):
                    query_params.append(
                        bigquery.ScalarQueryParameter(name, "INT64", value)
                    )
                elif isinstance(value, float):
                    query_params.append(
                        bigquery.ScalarQueryParameter(name, "FLOAT64", value)
                    )
                elif isinstance(value, str):
                    query_params.append(
                        bigquery.ScalarQueryParameter(name, "STRING", value)
                    )
                elif isinstance(value, list):
                    # Assume list of integers for site IDs, etc.
                    if value and isinstance(value[0], int):
                        query_params.append(
                            bigquery.ArrayQueryParameter(name, "INT64", value)
                        )
                    else:
                        query_params.append(
                            bigquery.ArrayQueryParameter(name, "STRING", value)
                        )
            job_config.query_parameters = query_params

        query_job = self.client.query(sql, job_config=job_config)
        return query_job.to_dataframe()

    def query_to_list(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a query and return results as a list of dictionaries.

        Args:
            sql: SQL query string
            params: Optional query parameters

        Returns:
            List of result rows as dictionaries
        """
        df = self.query(sql, params)
        return df.to_dict("records")

    def query_scalar(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute a query and return a single scalar value.

        Args:
            sql: SQL query string
            params: Optional query parameters

        Returns:
            Single scalar value from the query
        """
        df = self.query(sql, params)
        if df.empty:
            return None
        return df.iloc[0, 0]

    def get_pds_date_range(self) -> Dict[str, Any]:
        """
        Get the min and max dates available in the PDS (Point of Daily Sales) data.

        Returns:
            Dict with 'min_date' and 'max_date' keys
        """
        sql = """
            SELECT
                MIN(date_day) as min_date,
                MAX(date_day) as max_date
            FROM pds
        """
        result = self.query(sql)
        if result.empty:
            return {"min_date": None, "max_date": None}
        return {
            "min_date": result.iloc[0]["min_date"],
            "max_date": result.iloc[0]["max_date"],
        }

    def get_weekly_metrics_by_site(
        self,
        metric_type: str,
        site_ids: List[int],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        product_hierarchy_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Get weekly metric data for specified sites.

        Args:
            metric_type: Type of metric (e.g., 'SALES', 'UNITS', 'TRANSACTIONS')
            site_ids: List of site IDs to get metrics for
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            product_hierarchy_ids: Optional list of hierarchy IDs to filter by

        Returns:
            DataFrame with columns: site_id, week_start, metric_value
        """
        # Build the base query - this is a simplified version
        # The actual query depends on your BigQuery schema
        sql = f"""
            SELECT
                site_id,
                DATE_TRUNC(date_day, WEEK(MONDAY)) as week_start,
                SUM(metric_value) as metric_value
            FROM pds
            WHERE site_id IN UNNEST(@site_ids)
                AND metric_type = @metric_type
        """

        params = {
            "site_ids": site_ids,
            "metric_type": metric_type,
        }

        if start_date:
            sql += " AND date_day >= @start_date"
            params["start_date"] = start_date

        if end_date:
            sql += " AND date_day <= @end_date"
            params["end_date"] = end_date

        if product_hierarchy_ids:
            sql += " AND hierarchy_id IN UNNEST(@hierarchy_ids)"
            params["hierarchy_ids"] = product_hierarchy_ids

        sql += " GROUP BY site_id, week_start ORDER BY site_id, week_start"

        return self.query(sql, params)

    def close(self):
        """Close the BigQuery client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_bq(client: Optional[str] = None, **kwargs) -> BigQueryClient:
    """
    Get or create a BigQuery client for the specified client.

    First tries to load credentials from secrets/configs/staging.config.json,
    then falls back to environment variables.

    Args:
        client: Client identifier (e.g., 'maverik', 'dicks')
        **kwargs: Parameters passed to BigQueryClient (override config)

    Returns:
        BigQueryClient instance
    """
    global _bq_instances

    # Use client as cache key, or "_default" if not specified
    cache_key = client or "_default"

    if cache_key not in _bq_instances:
        # Try to load from config file first
        config = load_config()

        if client and config and not kwargs:
            client_config = get_client_db_config(client, config)
            bq_config = client_config.get("bigquery", {}) if client_config else {}

            # Get project from top-level config
            project = config.get("google_cloud_project")
            dataset = bq_config.get("dataset")

            if project:
                _bq_instances[cache_key] = BigQueryClient(
                    project=project,
                    dataset=dataset,
                )
            else:
                # Fall back to env vars
                _bq_instances[cache_key] = BigQueryClient(**kwargs)
        elif config and not kwargs:
            # No client specified but config exists, use top-level project
            project = config.get("google_cloud_project")
            if project:
                _bq_instances[cache_key] = BigQueryClient(project=project)
            else:
                _bq_instances[cache_key] = BigQueryClient(**kwargs)
        else:
            # No config or explicit kwargs provided
            _bq_instances[cache_key] = BigQueryClient(**kwargs)

    return _bq_instances[cache_key]


def reset_bq(client: Optional[str] = None):
    """
    Reset BigQuery client(s).

    Args:
        client: Specific client to reset, or None to reset all
    """
    global _bq_instances

    if client:
        cache_key = client
        if cache_key in _bq_instances:
            _bq_instances[cache_key].close()
            del _bq_instances[cache_key]
    else:
        for bq in _bq_instances.values():
            bq.close()
        _bq_instances = {}
