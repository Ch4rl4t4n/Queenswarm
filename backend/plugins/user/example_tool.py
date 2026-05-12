"""Example operator plugin — copy and edit in ``plugins/user``."""

__version__ = "1.0.0"

TOOL_NAME = "example_tool"
TOOL_DESCRIPTION = "Example custom tool — replace with your own logic."


async def run(query: str = "") -> str:
    """Main entry point optionally invoked by integrations."""

    return f"Example plugin executed with query: '{query}'. Replace this with your logic!"
