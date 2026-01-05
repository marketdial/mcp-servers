"""
Database access layer for Calcs API Code.

Provides direct PostgreSQL and BigQuery access for test creation,
bypassing the web-api for a cleaner, isolated implementation.

Credentials can be loaded from:
1. secrets/configs/staging.config.json (preferred)
2. Environment variables (fallback)
"""

from .connection import DatabaseConnection, get_db, list_available_clients, load_config
from .bigquery import BigQueryClient, get_bq

__all__ = [
    "DatabaseConnection",
    "get_db",
    "list_available_clients",
    "load_config",
    "BigQueryClient",
    "get_bq",
]
