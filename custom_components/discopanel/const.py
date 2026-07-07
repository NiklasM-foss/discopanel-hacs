"""Constants for the DiscoPanel integration."""

from __future__ import annotations

from typing import Any, Final

DOMAIN: Final = "discopanel"

# Config entry / options keys
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_SSL: Final = "ssl"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_API_TOKEN: Final = "api_token"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Defaults
DEFAULT_PORT: Final = 8080
DEFAULT_SSL: Final = False
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 10

# Manufacturer / branding
MANUFACTURER: Final = "DiscoPanel"
HUB_NAME: Final = "DiscoPanel"

# Service
SERVICE_SEND_COMMAND: Final = "send_command"
ATTR_SERVER_ID: Final = "server_id"
ATTR_COMMAND: Final = "command"
ATTR_SILENT: Final = "silent"

# ---------------------------------------------------------------------------
# Server status enum handling.
#
# protojson serializes enums as their STRING name, but some builds may emit the
# integer form. We normalize both to a stable lowercase short token.
# ---------------------------------------------------------------------------

STATUS_UNSPECIFIED: Final = "unspecified"
STATUS_CREATING: Final = "creating"
STATUS_STARTING: Final = "starting"
STATUS_RUNNING: Final = "running"
STATUS_STOPPING: Final = "stopping"
STATUS_STOPPED: Final = "stopped"
STATUS_RESTARTING: Final = "restarting"
STATUS_ERROR: Final = "error"
STATUS_UNHEALTHY: Final = "unhealthy"

# Integer -> short token (protobuf enum values)
STATUS_INT_MAP: Final[dict[int, str]] = {
    0: STATUS_UNSPECIFIED,
    1: STATUS_CREATING,
    2: STATUS_STARTING,
    3: STATUS_RUNNING,
    4: STATUS_STOPPING,
    5: STATUS_STOPPED,
    6: STATUS_RESTARTING,
    7: STATUS_ERROR,
    8: STATUS_UNHEALTHY,
}

# String enum name -> short token
STATUS_STR_MAP: Final[dict[str, str]] = {
    "SERVER_STATUS_UNSPECIFIED": STATUS_UNSPECIFIED,
    "SERVER_STATUS_CREATING": STATUS_CREATING,
    "SERVER_STATUS_STARTING": STATUS_STARTING,
    "SERVER_STATUS_RUNNING": STATUS_RUNNING,
    "SERVER_STATUS_STOPPING": STATUS_STOPPING,
    "SERVER_STATUS_STOPPED": STATUS_STOPPED,
    "SERVER_STATUS_RESTARTING": STATUS_RESTARTING,
    "SERVER_STATUS_ERROR": STATUS_ERROR,
    "SERVER_STATUS_UNHEALTHY": STATUS_UNHEALTHY,
}

# Ordered list of all short tokens (used for sensor ENUM options).
SERVER_STATUS_OPTIONS: Final[list[str]] = [
    STATUS_UNSPECIFIED,
    STATUS_CREATING,
    STATUS_STARTING,
    STATUS_RUNNING,
    STATUS_STOPPING,
    STATUS_STOPPED,
    STATUS_RESTARTING,
    STATUS_ERROR,
    STATUS_UNHEALTHY,
]


def normalize_status(raw: Any) -> str:
    """Normalize a raw status value (string name or int) to a short token.

    Accepts:
      - protojson enum name, e.g. "SERVER_STATUS_RUNNING"
      - already-short token, e.g. "running"
      - integer enum value, e.g. 3
      - None / anything unknown -> "unspecified"
    """
    if raw is None:
        return STATUS_UNSPECIFIED

    # Integer form (or numeric string).
    if isinstance(raw, bool):
        # Guard: bool is a subclass of int, treat as unspecified.
        return STATUS_UNSPECIFIED
    if isinstance(raw, int):
        return STATUS_INT_MAP.get(raw, STATUS_UNSPECIFIED)
    if isinstance(raw, str):
        stripped = raw.strip()
        # Numeric string.
        if stripped.isdigit():
            return STATUS_INT_MAP.get(int(stripped), STATUS_UNSPECIFIED)
        # Full protojson enum name.
        upper = stripped.upper()
        if upper in STATUS_STR_MAP:
            return STATUS_STR_MAP[upper]
        # Already a short token.
        lower = stripped.lower()
        if lower in SERVER_STATUS_OPTIONS:
            return lower
        # Enum name without the SERVER_STATUS_ prefix.
        candidate = f"SERVER_STATUS_{upper}"
        if candidate in STATUS_STR_MAP:
            return STATUS_STR_MAP[candidate]

    return STATUS_UNSPECIFIED


def is_running(raw: Any) -> bool:
    """Return True if the given raw status represents a running server."""
    return normalize_status(raw) == STATUS_RUNNING


# ---------------------------------------------------------------------------
# Mod loader pretty names.
# ---------------------------------------------------------------------------

MOD_LOADER_PRETTY: Final[dict[str, str]] = {
    "MOD_LOADER_UNSPECIFIED": "Unknown",
    "MOD_LOADER_VANILLA": "Vanilla",
    "MOD_LOADER_FABRIC": "Fabric",
    "MOD_LOADER_FORGE": "Forge",
    "MOD_LOADER_NEOFORGE": "NeoForge",
    "MOD_LOADER_QUILT": "Quilt",
    "MOD_LOADER_PAPER": "Paper",
    "MOD_LOADER_SPIGOT": "Spigot",
    "MOD_LOADER_BUKKIT": "Bukkit",
    "MOD_LOADER_PURPUR": "Purpur",
    "MOD_LOADER_BUNGEECORD": "BungeeCord",
    "MOD_LOADER_VELOCITY": "Velocity",
    "MOD_LOADER_WATERFALL": "Waterfall",
}

# Integer enum values as a fallback (defensive; ordering per typical proto).
MOD_LOADER_INT_MAP: Final[dict[int, str]] = {
    0: "MOD_LOADER_UNSPECIFIED",
    1: "MOD_LOADER_VANILLA",
    2: "MOD_LOADER_FABRIC",
    3: "MOD_LOADER_FORGE",
    4: "MOD_LOADER_NEOFORGE",
    5: "MOD_LOADER_QUILT",
    6: "MOD_LOADER_PAPER",
    7: "MOD_LOADER_SPIGOT",
    8: "MOD_LOADER_BUKKIT",
    9: "MOD_LOADER_PURPUR",
    10: "MOD_LOADER_BUNGEECORD",
    11: "MOD_LOADER_VELOCITY",
    12: "MOD_LOADER_WATERFALL",
}


def mod_loader_pretty(raw: Any) -> str:
    """Return a human-friendly mod loader name from a string name or int."""
    if raw is None:
        return "Unknown"
    if isinstance(raw, bool):
        return "Unknown"
    if isinstance(raw, int):
        raw = MOD_LOADER_INT_MAP.get(raw, "MOD_LOADER_UNSPECIFIED")
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.isdigit():
            key = MOD_LOADER_INT_MAP.get(int(stripped), "MOD_LOADER_UNSPECIFIED")
            return MOD_LOADER_PRETTY.get(key, "Unknown")
        upper = stripped.upper()
        if upper in MOD_LOADER_PRETTY:
            return MOD_LOADER_PRETTY[upper]
        candidate = f"MOD_LOADER_{upper}"
        if candidate in MOD_LOADER_PRETTY:
            return MOD_LOADER_PRETTY[candidate]
        # Fall back to a title-cased version of whatever we got.
        return stripped.title() or "Unknown"
    return "Unknown"
