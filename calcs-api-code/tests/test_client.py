"""
Tests for the Calcs API Code Client.

These tests verify the client initialization and basic functionality.
Integration tests require CALCS_API_TOKEN to be set.
"""

import os

import pytest


class TestClientInitialization:
    """Test client initialization and configuration."""

    def test_import(self):
        """Test that the package can be imported."""
        from calcs_api_code import CalcsClient

        assert CalcsClient is not None

    def test_missing_token_raises_error(self, monkeypatch):
        """Test that missing token raises ValueError."""
        from calcs_api_code import CalcsClient

        # Clear the token
        monkeypatch.delenv("CALCS_API_TOKEN", raising=False)

        with pytest.raises(ValueError, match="CALCS_API_TOKEN"):
            CalcsClient()

    def test_client_with_token(self, monkeypatch):
        """Test that client initializes with token."""
        from calcs_api_code import CalcsClient

        monkeypatch.setenv("CALCS_API_TOKEN", "test_token")

        client = CalcsClient()
        assert client.token == "test_token"
        assert client.base_url == "https://staging-app.marketdial.dev/calcs"
        client.close()

    def test_client_with_custom_url(self, monkeypatch):
        """Test that client respects custom base URL."""
        from calcs_api_code import CalcsClient

        monkeypatch.setenv("CALCS_API_TOKEN", "test_token")
        monkeypatch.setenv("CALCS_API_BASE_URL", "https://custom.api.com/calcs/")

        client = CalcsClient()
        assert client.base_url == "https://custom.api.com/calcs"  # trailing slash removed
        client.close()

    def test_client_with_default_client(self, monkeypatch):
        """Test that client respects default client setting."""
        from calcs_api_code import CalcsClient

        monkeypatch.setenv("CALCS_API_TOKEN", "test_token")
        monkeypatch.setenv("CALCS_DEFAULT_CLIENT", "TestClient")

        client = CalcsClient()
        assert client.default_client == "TestClient"
        client.close()

    def test_client_override_default_client(self, monkeypatch):
        """Test that constructor client overrides env var."""
        from calcs_api_code import CalcsClient

        monkeypatch.setenv("CALCS_API_TOKEN", "test_token")
        monkeypatch.setenv("CALCS_DEFAULT_CLIENT", "EnvClient")

        client = CalcsClient(client="ConstructorClient")
        assert client.default_client == "ConstructorClient"
        client.close()

    def test_context_manager(self, monkeypatch):
        """Test that client works as context manager."""
        from calcs_api_code import CalcsClient

        monkeypatch.setenv("CALCS_API_TOKEN", "test_token")

        with CalcsClient() as client:
            assert client is not None
        # Should not raise after context exit


class TestDiscovery:
    """Test discovery functions."""

    def test_list_available_functions(self):
        """Test that we can list available functions."""
        from calcs_api_code import list_available_functions

        functions = list_available_functions()
        assert isinstance(functions, list)
        assert "get_tests" in functions
        assert "health_check" in functions

    def test_get_function_help(self):
        """Test that we can get function help."""
        from calcs_api_code import get_function_help

        help_text = get_function_help("get_tests")
        assert help_text is not None
        assert "get_tests" in help_text
        assert "client" in help_text.lower()

    def test_get_function_help_unknown(self):
        """Test that unknown function returns None."""
        from calcs_api_code import get_function_help

        help_text = get_function_help("unknown_function")
        assert help_text is None

    def test_search_functions(self):
        """Test searching for functions."""
        from calcs_api_code.discovery import search_functions

        matches = search_functions("test")
        assert isinstance(matches, list)
        assert "get_tests" in matches
        assert "get_test_status" in matches


class TestTypes:
    """Test type definitions."""

    def test_test_from_dict(self):
        """Test creating Test from dict."""
        from calcs_api_code.types import Test

        data = {"id": 123, "name": "Test Name", "status": "active"}
        test = Test.from_dict(data)
        assert test.id == 123
        assert test.name == "Test Name"
        assert test.status == "active"


# Integration tests - only run if API token is available
@pytest.mark.skipif(
    not os.getenv("CALCS_API_TOKEN"),
    reason="CALCS_API_TOKEN not set - skipping integration tests",
)
class TestIntegration:
    """Integration tests that hit the real API."""

    def test_health_check(self):
        """Test health check endpoint."""
        from calcs_api_code import CalcsClient

        with CalcsClient() as client:
            health = client.health_check()
            assert health is not None

    def test_get_tests(self):
        """Test getting tests."""
        from calcs_api_code import CalcsClient

        with CalcsClient() as client:
            tests = client.get_tests()
            assert isinstance(tests, list)

    def test_get_active_clients(self):
        """Test getting active clients."""
        from calcs_api_code import CalcsClient

        with CalcsClient() as client:
            clients = client.get_active_clients()
            assert isinstance(clients, list)
