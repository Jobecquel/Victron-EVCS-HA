"""The Victron EV Charging Station integration."""

from __future__ import annotations

from time import monotonic

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VictronEvcsClient
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FAILSAFE_AFTER,
    FAILSAFE_RETRY,
    UNAVAILABLE_GRACE,
)
from .coordinator import VictronEvcsCoordinator
from .helpers import LinkMonitor

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type VictronEvcsConfigEntry = ConfigEntry[VictronEvcsCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VictronEvcsConfigEntry) -> bool:
    """Set up a charger from a config entry."""
    client = VictronEvcsClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, 80),
    )
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    # Kept across setup retries: a charger that is already hung when Home
    # Assistant starts never lets setup finish, and still needs the failsafe.
    links: dict[str, LinkMonitor] = hass.data.setdefault(DOMAIN, {})
    link = links.setdefault(
        entry.entry_id, LinkMonitor(UNAVAILABLE_GRACE, FAILSAFE_AFTER, FAILSAFE_RETRY)
    )

    coordinator = VictronEvcsCoordinator(hass, entry, client, scan_interval, link)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        now = monotonic()
        link.failure(now)
        await coordinator.async_failsafe(now)
        raise
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VictronEvcsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: VictronEvcsConfigEntry) -> None:
    """Forget the link state of a removed charger."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)


async def _async_update_listener(
    hass: HomeAssistant, entry: VictronEvcsConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
