"""Number platform for the Victron EV Charging Station."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VictronEvcsConfigEntry
from .api import VictronEvcsError
from .const import (
    DEFAULT_MAX_CURRENT,
    DEFAULT_MIN_CURRENT,
    DOMAIN,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_SCHEDULED,
    MODE_SLUGS,
)
from .coordinator import VictronEvcsCoordinator
from .entity import OptimisticValue, VictronEvcsEntity

PARALLEL_UPDATES = 1

# Each charging mode keeps its own current setpoint.
SETPOINT_KEYS = {
    MODE_MANUAL: "chargingCurrentManual",
    MODE_AUTO: "chargingCurrentAuto",
    MODE_SCHEDULED: "chargingCurrentSched",
}

CHARGING_CURRENT = NumberEntityDescription(
    key="charging_current",
    device_class=NumberDeviceClass.CURRENT,
    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    native_step=1,
    mode=NumberMode.SLIDER,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VictronEvcsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the charging current number."""
    async_add_entities(
        [VictronEvcsChargingCurrent(entry.runtime_data, CHARGING_CURRENT)]
    )


class VictronEvcsChargingCurrent(VictronEvcsEntity, NumberEntity):
    """The charging current setpoint, in amps."""

    def __init__(
        self,
        coordinator: VictronEvcsCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialise the number."""
        super().__init__(coordinator, description)
        self._optimistic = OptimisticValue()

    @property
    def _mode(self) -> int:
        """Return the active charging mode."""
        mode = self.params.get("chargingMode")
        return int(mode) if mode is not None else MODE_MANUAL

    @property
    def native_min_value(self) -> float:
        """Return the charger's own minimum current."""
        return float(self.actual.get("chCurrMin") or DEFAULT_MIN_CURRENT)

    @property
    def native_max_value(self) -> float:
        """Return the charger's own maximum current."""
        return float(self.actual.get("chCurrMax") or DEFAULT_MAX_CURRENT)

    @property
    def native_value(self) -> float | None:
        """Return the setpoint belonging to the active mode."""
        key = SETPOINT_KEYS.get(self._mode, SETPOINT_KEYS[MODE_MANUAL])
        reported = self.params.get(key)
        reported = float(reported) if reported is not None else None
        value = self._optimistic.get(reported)
        return float(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return which mode's setpoint is being shown."""
        return {"charging_mode": MODE_SLUGS.get(self._mode, "unknown")}

    async def async_set_native_value(self, value: float) -> None:
        """Write a new charging current setpoint."""
        current = int(round(value))
        try:
            await self.coordinator.client.async_set_charging_current(current)
        except VictronEvcsError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_current_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        self._optimistic.set(float(current))
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
