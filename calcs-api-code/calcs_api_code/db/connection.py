"""
PostgreSQL database connection management.

Provides direct access to the MarketDial database for test creation operations.
Supports loading credentials from secrets/configs/staging.config.json.
"""

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Load environment variables
load_dotenv()

# Global connection instances (per-client)
_db_instances: Dict[str, "DatabaseConnection"] = {}

# Config file locations to search (relative to this file, then absolute)
CONFIG_PATHS = [
    Path(__file__).parent.parent.parent.parent / "secrets" / "configs" / "staging.config.json",
    Path("/Users/jeff/Code/mcp-servers/secrets/configs/staging.config.json"),
]


def load_config() -> Optional[Dict[str, Any]]:
    """Load the staging config file if it exists."""
    for config_path in CONFIG_PATHS:
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
    return None


def get_client_db_config(client: str, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Get database config for a specific client from the config file.

    Args:
        client: Client name (e.g., 'maverik', 'dicks')
        config: Optional pre-loaded config dict

    Returns:
        Client database config dict or None if not found
    """
    if config is None:
        config = load_config()

    if not config or "db" not in config:
        return None

    # Search for client in the clients list
    for client_config in config.get("db", {}).get("clients", []):
        if client_config.get("client_name") == client:
            return client_config

    return None


class DatabaseConnection:
    """
    Direct PostgreSQL connection for Calcs API operations.

    Environment Variables:
        POSTGRES_HOST: Database host
        POSTGRES_PORT: Database port (default: 5432)
        POSTGRES_USER: Database user
        POSTGRES_PASSWORD: Database password
        POSTGRES_DATABASE: Database name

    Or use a connection URL:
        DATABASE_URL: Full connection URL (overrides individual vars)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Initialize database connection.

        Args:
            host: PostgreSQL host (or use POSTGRES_HOST env var)
            port: PostgreSQL port (or use POSTGRES_PORT env var, default 5432)
            user: Database user (or use POSTGRES_USER env var)
            password: Database password (or use POSTGRES_PASSWORD env var)
            database: Database name (or use POSTGRES_DATABASE env var)
            url: Full connection URL (overrides all other params)
        """
        if url:
            self._url = url
        elif os.getenv("DATABASE_URL"):
            self._url = os.getenv("DATABASE_URL")
        else:
            self._host = host or os.getenv("POSTGRES_HOST")
            self._port = port or int(os.getenv("POSTGRES_PORT", "5432"))
            self._user = user or os.getenv("POSTGRES_USER")
            self._password = password or os.getenv("POSTGRES_PASSWORD")
            self._database = database or os.getenv("POSTGRES_DATABASE")

            if not all([self._host, self._user, self._password, self._database]):
                raise ValueError(
                    "Database connection requires either DATABASE_URL or "
                    "POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DATABASE"
                )

            self._url = (
                f"postgresql://{self._user}:{self._password}@"
                f"{self._host}:{self._port}/{self._database}"
            )

        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """Get or create the SQLAlchemy engine."""
        if self._engine is None:
            self._engine = create_engine(
                self._url,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Create a database session context manager.

        Usage:
            with db.session() as session:
                result = session.execute(text("SELECT * FROM app_tests"))
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query and return results as dictionaries.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of result rows as dictionaries
        """
        with self.session() as session:
            result = session.execute(text(query), params or {})
            # For SELECT queries, return results as dicts
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
            return []

    def execute_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute a query and return a single result.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Single result row as dictionary, or None if no results
        """
        results = self.execute(query, params)
        return results[0] if results else None

    def execute_scalar(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a query and return a single scalar value.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Single scalar value from the query
        """
        with self.session() as session:
            result = session.execute(text(query), params or {})
            row = result.fetchone()
            return row[0] if row else None

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert a row into a table and return the new ID.

        Args:
            table: Table name
            data: Dictionary of column names to values

        Returns:
            The ID of the newly inserted row
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"

        with self.session() as session:
            result = session.execute(text(query), data)
            row = result.fetchone()
            return row[0] if row else 0

    def insert_no_return(self, table: str, data: Dict[str, Any]) -> bool:
        """
        Insert a row into a table without returning an ID.

        Use this for junction/association tables that don't have an id column.

        Args:
            table: Table name
            data: Dictionary of column names to values

        Returns:
            True if the insert was successful
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.session() as session:
            result = session.execute(text(query), data)
            return result.rowcount > 0

    def update(self, table: str, id_value: int, data: Dict[str, Any]) -> bool:
        """
        Update a row in a table by ID.

        Args:
            table: Table name
            id_value: The ID of the row to update
            data: Dictionary of column names to new values

        Returns:
            True if a row was updated
        """
        set_clause = ", ".join(f"{k} = :{k}" for k in data.keys())
        query = f"UPDATE {table} SET {set_clause} WHERE id = :id"
        data["id"] = id_value

        with self.session() as session:
            result = session.execute(text(query), data)
            return result.rowcount > 0

    def close(self):
        """Close the database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_db(
    client: Optional[str] = None,
    **kwargs
) -> DatabaseConnection:
    """
    Get or create a database connection for the specified client.

    First tries to load credentials from secrets/configs/staging.config.json,
    then falls back to environment variables.

    Args:
        client: Client identifier (e.g., 'maverik', 'dicks')
        **kwargs: Connection parameters passed to DatabaseConnection (override config)

    Returns:
        DatabaseConnection instance
    """
    global _db_instances

    # Use client as cache key, or "_default" if not specified
    cache_key = client or "_default"

    if cache_key not in _db_instances:
        # Try to load from config file first
        if client and not kwargs:
            client_config = get_client_db_config(client)
            if client_config:
                # Use k8s service name (works with kubefwd) or fall back to private_ip
                host = client_config.get("host") or client_config.get("private_ip")
                _db_instances[cache_key] = DatabaseConnection(
                    host=host,
                    port=client_config.get("port", 5432),
                    user=client_config.get("username"),
                    password=client_config.get("password"),
                    database=client_config.get("database"),
                )
            else:
                # Client not found in config, fall back to env vars
                _db_instances[cache_key] = DatabaseConnection(**kwargs)
        else:
            # No client specified or explicit kwargs provided
            _db_instances[cache_key] = DatabaseConnection(**kwargs)

    return _db_instances[cache_key]


def reset_db(client: Optional[str] = None):
    """
    Reset database connection(s).

    Args:
        client: Specific client to reset, or None to reset all
    """
    global _db_instances

    if client:
        cache_key = client
        if cache_key in _db_instances:
            _db_instances[cache_key].close()
            del _db_instances[cache_key]
    else:
        for db in _db_instances.values():
            db.close()
        _db_instances = {}


def list_available_clients() -> List[str]:
    """
    List all clients available in the config file.

    Returns:
        List of client names
    """
    config = load_config()
    if not config or "db" not in config:
        return []

    return [
        c.get("client_name")
        for c in config.get("db", {}).get("clients", [])
        if c.get("client_name")
    ]
