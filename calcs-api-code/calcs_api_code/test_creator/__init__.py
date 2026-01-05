"""
Test Creator Package - AI-driven test creation for A/B tests.

Provides a clean API for creating tests programmatically,
designed to be used by AI models (Claude, Gemini) in an interview-style flow.
"""

from .test_builder import TestBuilder
from .sample_optimizer import SampleOptimizer, SampleResult
from .validators import ValidationError, validate_test_name, validate_dates

__all__ = [
    "TestBuilder",
    "SampleOptimizer",
    "SampleResult",
    "ValidationError",
    "validate_test_name",
    "validate_dates",
]
