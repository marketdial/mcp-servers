"""Tool registration for the Calcs API MCP server.

Import all tool modules to register their @mcp.tool() decorators.
"""


def register_all_tools(mcp):
    """Import all tool modules, triggering decorator registration.

    This is called from server.py after the FastMCP instance is created.
    Each tool module imports `mcp` from here via get_mcp().
    """
    # Store mcp instance for tool modules to access
    global _mcp_instance
    _mcp_instance = mcp

    # Import tool modules — decorators register automatically
    from . import tests  # noqa: F401
    from . import results  # noqa: F401
    from . import analysis  # noqa: F401
    from . import jobs  # noqa: F401
    from . import discovery  # noqa: F401


_mcp_instance = None


def get_mcp():
    """Get the FastMCP instance for tool registration."""
    if _mcp_instance is None:
        raise RuntimeError("Tools accessed before register_all_tools() was called")
    return _mcp_instance
