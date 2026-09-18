"""Client for the Victron EV Charging Station local HTTP API.

The charger serves the same JSON API its own web interface uses. Every
call is a plain GET, no authentication of any kind is involved, and commands
carry their payload as JSON in a ``jsonData`` query parameter.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import quote

import aiohttp
from yarl import URL

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10

# Endpoints
EP_ACTUAL_STATE = "/actualStateRead"
EP_BASIC_DATA = "/basicDataRead"
EP_CHARGING_PARAMS = "/chargingParamsRead"
EP_COMMON_DATA = "/commonDataRead"
EP_SENSORS = "/sensorsRead"
EP_CHARGING_START = "/chargingStart"
EP_CHARGING_STOP = "/chargingStop"
EP_CURRENT_SET = "/chargingCurrentSet"
EP_MODE_SET = "/chargingModeSet"


class VictronEvcsError(Exception):
    """Base error for the Victron EVCS API."""


class VictronEvcsConnectionError(VictronEvcsError):
    """The charger could not be reached."""


class VictronEvcsCommandError(VictronEvcsError):
    """The charger rejected a command."""


def _json_query(path: str, payload: dict[str, Any]) -> str:
    """Build a command path with a ``jsonData`` query parameter.

    The braces, colons and commas are left literal and only the quotes are
    percent-encoded, which is exactly the form the charger's own web UI sends.
    """
    body = json.dumps(payload, separators=(",", ":"))
    return f"{path}?jsonData={quote(body, safe='{}:,')}"


class VictronEvcsClient:
    """Talks to a single EV Charging Station."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._host = host
        self._port = port
        self._base = f"http://{host}" if port == 80 else f"http://{host}:{port}"
        # The charger's web UI runs a strictly single-in-flight command queue.
        # This is a small embedded web server, so we do the same rather than
        # letting the coordinator and a command overlap.
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the charger host."""
        return self._host

    @property
    def base_url(self) -> str:
        """Return the charger's base URL."""
        return self._base

    async def _get(self, path: str) -> dict[str, Any]:
        """Perform one GET and return the decoded JSON body."""
        url = URL(f"{self._base}{path}", encoded=True)
        async with self._lock:
            try:
                async with self._session.get(
                    url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as response:
                    response.raise_for_status()
                    text = await response.text()
            except TimeoutError as err:
                raise VictronEvcsConnectionError(f"Timeout calling {path}") from err
            except aiohttp.ClientError as err:
                raise VictronEvcsConnectionError(f"Error calling {path}: {err}") from err

        try:
            data = json.loads(text)
        except ValueError as err:
            raise VictronEvcsError(
                f"Invalid JSON from {path}: {text[:120]!r}"
            ) from err

        if not isinstance(data, dict):
            raise VictronEvcsError(f"Unexpected payload from {path}: {data!r}")
        return data

    async def _command(self, path: str) -> dict[str, Any]:
        """Send a command and verify the charger acknowledged it."""
        data = await self._get(path)
        # A successful command replies {"state":1,"isActive":1}. Anything else
        # means the charger silently declined, so surface it instead.
        if data.get("state") != 1:
            raise VictronEvcsCommandError(
                f"Charger did not accept command {path}: {data}"
            )
        _LOGGER.debug("Command %s acknowledged: %s", path, data)
        return data

    # Reads

    async def async_basic_data(self) -> dict[str, Any]:
        """Return firmware and serial. Smallest payload, used for probing."""
        return await self._get(EP_BASIC_DATA)

    async def async_common_data(self) -> dict[str, Any]:
        """Return device identity, network and uptime information."""
        return await self._get(EP_COMMON_DATA)

    async def async_actual_state(self) -> dict[str, Any]:
        """Return the main live state of the charger."""
        return await self._get(EP_ACTUAL_STATE)

    async def async_charging_params(self) -> dict[str, Any]:
        """Return the charging mode and the per-mode current setpoints."""
        return await self._get(EP_CHARGING_PARAMS)

    async def async_sensors(self) -> dict[str, Any]:
        """Return raw sensor readings used for diagnostics."""
        return await self._get(EP_SENSORS)

    # Commands

    async def async_start_charging(self) -> None:
        """Start charging."""
        await self._command(EP_CHARGING_START)

    async def async_stop_charging(self) -> None:
        """Stop charging."""
        await self._command(EP_CHARGING_STOP)

    async def async_set_charging_current(self, current: int) -> None:
        """Set the charging current setpoint in amps."""
        await self._command(_json_query(EP_CURRENT_SET, {"chargingCurrent": int(current)}))

    async def async_set_charging_mode(self, mode: int) -> None:
        """Set the charging mode (0 manual, 1 auto, 2 scheduled)."""
        await self._command(_json_query(EP_MODE_SET, {"chargingMode": int(mode)}))
