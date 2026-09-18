"""Diagnostics support for the Victron EV Charging Station."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import VictronEvcsConfigEntry

TO_REDACT = {"sn", "ip", "ssid", CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: VictronEvcsConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "device": {
            "model": coordinator.model,
            "firmware": coordinator.firmware,
        },
        "actual_state": async_redact_data(data.actual, TO_REDACT),
        "charging_params": data.params,
        "sensors": data.sensors,
        "common_data": async_redact_data(data.common, TO_REDACT),
    }
