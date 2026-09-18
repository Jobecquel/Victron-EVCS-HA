"""Select platform for the Victron EV Charging Station."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VictronEvcsConfigEntry
from .api import VictronEvcsError
from .const import (
    DOMAIN,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_SCHEDULED,
    MODE_SLUGS,
    MODE_VALUES,
)
from .coordinator import VictronEvcsCoordinator
from .entity import OptimisticValue, VictronEvcsEntity

PARALLEL_UPDATES = 1

CHARGING_MODE = SelectEntityDescription(
    key="charging_mode",
    options=list(MODE_VALUES),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VictronEvcsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the charging mode select."""
    async_add_entities([VictronEvcsChargingMode(entry.runtime_data, CHARGING_MODE)])


class VictronEvcsChargingMode(VictronEvcsEntity, SelectEntity):
    """Selects manual, auto or scheduled charging."""

    _attr_icon = "mdi:tune"

    def __init__(
        self,
        coordinator: VictronEvcsCoordinator,
        description: SelectEntityDescription,
    ) -> None:
        """Initialise the select."""
        super().__init__(coordinator, description)
        self._optimistic = OptimisticValue()

    @property
    def options(self) -> list[str]:
        """Return only the modes this charger can actually use.

        Auto needs a paired GX device and scheduled needs a configured
        scheduler; the charger refuses the mode otherwise. The active mode is
        always listed so the current state stays valid.
        """
        available = [MODE_SLUGS[MODE_MANUAL]]
        if self.actual.get("useModbus"):
            available.append(MODE_SLUGS[MODE_AUTO])
        if self.actual.get("useSched"):
            available.append(MODE_SLUGS[MODE_SCHEDULED])
        if (current := self.current_option) and current not in available:
            available.append(current)
        return available

    @property
    def current_option(self) -> str | None:
        """Return the active charging mode."""
        mode = self.params.get("chargingMode")
        reported = MODE_SLUGS.get(int(mode)) if mode is not None else None
        return self._optimistic.get(reported)

    async def async_select_option(self, option: str) -> None:
        """Switch the charger to another mode."""
        if option not in self.options:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="mode_unavailable",
                translation_placeholders={"mode": option},
            )

        try:
            await self.coordinator.client.async_set_charging_mode(MODE_VALUES[option])
        except VictronEvcsError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_mode_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        self._optimistic.set(option)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
