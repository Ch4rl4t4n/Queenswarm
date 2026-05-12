"""User plugin hooks (``.py`` drop-ins mounted at ``PLUGIN_DIR``)."""

from app.plugins.manager import (
    PLUGIN_DIR,
    discover_plugins,
    get_plugin_tool,
    load_plugin,
    unload_plugin,
)

__all__ = [
    "PLUGIN_DIR",
    "discover_plugins",
    "get_plugin_tool",
    "load_plugin",
    "unload_plugin",
]
