"""Button platform for the Victron EV Charging Station."""

from __future__ import annotations

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VictronEvcsConfigEntry
from .api import VictronEvcsError
from .const import DOMAIN
from .entity import VictronEvcsEntity

PARALLEL_UPDATES = 1

REBOOT_BUTTON = ButtonEntityDescription(
    key="reboot",
    device_class=ButtonDeviceClass.RESTART,
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VictronEvcsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the reboot button."""
    async_add_entities([VictronEvcsRebootButton(entry.runtime_data, REBOOT_BUTTON)])


class VictronEvcsRebootButton(VictronEvcsEntity, ButtonEntity):
    """Reboots the charger."""

    @property
    def available(self) -> bool:
        """Stay available when polling fails.

        The reboot goes over Modbus, not HTTP, and a hung web server is exactly
        when it is needed.
        """
        return True

    async def async_press(self) -> None:
        """Send the reset command."""
        try:
            await self.coordinator.client.async_reboot()
        except VictronEvcsError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reboot_failed",
                translation_placeholders={"error": str(err)},
            ) from err
