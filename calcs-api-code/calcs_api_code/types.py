"""
Type definitions for Calcs API responses.

These are optional type hints that can be used for better IDE support
and documentation. The client returns plain dicts for maximum flexibility.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Test:
    """Represents a test from the Calcs API."""

    id: int
    name: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Test":
        """Create a Test from a dictionary response."""
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            status=data.get("status", ""),
            description=data.get("description"),
            # Parse dates if present
            created_at=None,  # Would parse from data.get("created_at")
            updated_at=None,  # Would parse from data.get("updated_at")
        )


@dataclass
class Client:
    """Represents a client from the Calcs API."""

    id: str
    name: str
    active: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Client":
        """Create a Client from a dictionary response."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            active=data.get("active", True),
        )


@dataclass
class Analysis:
    """Represents a rollout analysis from the Calcs API."""

    id: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    selected_products: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Analysis":
        """Create an Analysis from a dictionary response."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            status=data.get("status"),
            selected_products=data.get("selectedProducts"),
        )
