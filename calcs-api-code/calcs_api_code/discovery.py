"""
Tool discovery functions for progressive loading.

These functions allow models to discover available functionality
without loading all method definitions into context upfront.
"""

import inspect
from typing import Dict, List, Optional


def list_available_functions() -> List[str]:
    """
    List all available CalcsClient methods.

    Returns:
        List of method names that can be called on CalcsClient.

    Example:
        from calcs_api_code import list_available_functions
        functions = list_available_functions()
        print(functions)
        # ['health_check', 'get_tests', 'get_test_status', ...]
    """
    from calcs_api_code.client import CalcsClient

    # Get all public methods (not starting with _)
    methods = [
        name
        for name in dir(CalcsClient)
        if not name.startswith("_") and callable(getattr(CalcsClient, name))
    ]
    return methods


def get_function_help(name: str) -> Optional[str]:
    """
    Get the signature and docstring for a specific CalcsClient method.

    Args:
        name: The method name (e.g., 'get_tests', 'health_check')

    Returns:
        String with signature and docstring, or None if method not found.

    Example:
        from calcs_api_code import get_function_help
        help_text = get_function_help('get_tests')
        print(help_text)
    """
    from calcs_api_code.client import CalcsClient

    method = getattr(CalcsClient, name, None)
    if method is None:
        return None

    try:
        sig = inspect.signature(method)
        doc = method.__doc__ or "No documentation available."
        return f"{name}{sig}\n\n{doc}"
    except (ValueError, TypeError):
        return f"{name}\n\nNo signature available."


def get_all_function_info() -> Dict[str, str]:
    """
    Get help text for all available functions.

    Returns:
        Dict mapping function names to their help text.

    Example:
        from calcs_api_code.discovery import get_all_function_info
        info = get_all_function_info()
        for name, help_text in info.items():
            print(f"=== {name} ===")
            print(help_text[:200])
    """
    functions = list_available_functions()
    return {name: get_function_help(name) or "" for name in functions}


def search_functions(keyword: str) -> List[str]:
    """
    Search for functions by keyword in name or docstring.

    Args:
        keyword: Search term to match.

    Returns:
        List of matching function names.

    Example:
        from calcs_api_code.discovery import search_functions
        test_functions = search_functions('test')
        # ['get_tests', 'get_test_status', 'get_site_tests', 'get_test_results']
    """
    keyword_lower = keyword.lower()
    matches = []

    for name in list_available_functions():
        help_text = get_function_help(name) or ""
        if keyword_lower in name.lower() or keyword_lower in help_text.lower():
            matches.append(name)

    return matches
