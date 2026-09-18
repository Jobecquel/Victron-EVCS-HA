"""Switch platform for the Victron EV Charging Station."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VictronEvcsConfigEntry
from .api import VictronEvcsError
from .const import DOMAIN
from .coordinator import VictronEvcsCoordinator
from .entity import OptimisticValue, VictronEvcsEntity
from .helpers import is_charging_enabled

PARALLEL_UPDATES = 1

CHARGING_SWITCH = SwitchEntityDescription(
    key="charging",
    device_class=SwitchDeviceClass.SWITCH,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VictronEvcsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the charging switch."""
    async_add_entities([VictronEvcsChargingSwitch(entry.runtime_data, CHARGING_SWITCH)])


class VictronEvcsChargingSwitch(VictronEvcsEntity, SwitchEntity):
    """Starts and stops charging."""

    _attr_icon = "mdi:ev-station"

    def __init__(
        self,
        coordinator: VictronEvcsCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, description)
        self._optimistic = OptimisticValue()

    @property
    def is_on(self) -> bool:
        """Return True when the charger is charging or waiting to charge."""
        reported = is_charging_enabled(
            self.actual.get("carState"), self.actual.get("carSubState")
        )
        return bool(self._optimistic.get(reported))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start charging."""
        await self._async_command(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop charging."""
        await self._async_command(False)

    async def _async_command(self, start: bool) -> None:
        """Send a start or stop command and reflect it immediately."""
        try:
            if start:
                await self.coordinator.client.async_start_charging()
            else:
                await self.coordinator.client.async_stop_charging()
        except VictronEvcsError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="start_stop_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        self._optimistic.set(start)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
