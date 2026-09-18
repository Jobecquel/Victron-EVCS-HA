"""Binary sensor platform for the Victron EV Charging Station."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VictronEvcsConfigEntry
from .const import STATE_CHARGING, STATE_DISCONNECTED, STATE_UNDEFINED
from .coordinator import VictronEvcsData
from .entity import VictronEvcsEntity

PARALLEL_UPDATES = 0


def _car_connected(data: VictronEvcsData) -> bool:
    car_state = data.actual.get("carState")
    return car_state not in (None, STATE_DISCONNECTED, STATE_UNDEFINED)


def _charging(data: VictronEvcsData) -> bool:
    return data.actual.get("carState") == STATE_CHARGING


def _problem(data: VictronEvcsData) -> bool:
    return bool(data.actual.get("faults")) or bool(data.actual.get("errs"))


def _warning(data: VictronEvcsData) -> bool:
    return bool(data.actual.get("warns"))


@dataclass(frozen=True, kw_only=True)
class VictronEvcsBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Victron EVCS binary sensor."""

    value_fn: Callable[[VictronEvcsData], bool]


BINARY_SENSORS: tuple[VictronEvcsBinarySensorDescription, ...] = (
    VictronEvcsBinarySensorDescription(
        key="car_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=_car_connected,
    ),
    VictronEvcsBinarySensorDescription(
        key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_charging,
    ),
    VictronEvcsBinarySensorDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_problem,
    ),
    VictronEvcsBinarySensorDescription(
        key="warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_warning,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VictronEvcsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        VictronEvcsBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class VictronEvcsBinarySensor(VictronEvcsEntity, BinarySensorEntity):
    """A binary sensor derived from the charger state."""

    entity_description: VictronEvcsBinarySensorDescription

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return self.entity_description.value_fn(self.data)
