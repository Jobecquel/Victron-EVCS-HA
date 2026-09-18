"""Sensor platform for the Victron EV Charging Station."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import VictronEvcsConfigEntry
from .const import STATUS_OPTIONS
from .coordinator import VictronEvcsData
from .entity import VictronEvcsEntity
from .helpers import active_phase_count, charging_status

PARALLEL_UPDATES = 0


def _number(source: str, key: str) -> Callable[[VictronEvcsData], StateType]:
    """Return a getter for a numeric field on one of the payloads."""

    def _get(data: VictronEvcsData) -> StateType:
        value = getattr(data, source).get(key)
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return _get


def _text(source: str, key: str) -> Callable[[VictronEvcsData], StateType]:
    """Return a getter for a string field on one of the payloads."""

    def _get(data: VictronEvcsData) -> StateType:
        value = getattr(data, source).get(key)
        return value if value not in (None, "") else None

    return _get


def _fault_text(key: str) -> Callable[[VictronEvcsData], StateType]:
    """Return a getter for an error/warning string, blank meaning none."""

    def _get(data: VictronEvcsData) -> StateType:
        return data.actual.get(key) or "none"

    return _get


def _status(data: VictronEvcsData) -> StateType:
    """Return the charger status slug."""
    return charging_status(data.actual.get("carState"), data.actual.get("carSubState"))


def _status_attrs(data: VictronEvcsData) -> dict[str, Any]:
    """Return the raw state numbers plus how many phases are drawing power."""
    return {
        "active_phases": active_phase_count(
            data.actual.get("chargPowerL1"),
            data.actual.get("chargPowerL2"),
            data.actual.get("chargPowerL3"),
        ),
        "car_state": data.actual.get("carState"),
        "car_sub_state": data.actual.get("carSubState"),
    }


@dataclass(frozen=True, kw_only=True)
class VictronEvcsSensorDescription(SensorEntityDescription):
    """Describes a Victron EVCS sensor."""

    value_fn: Callable[[VictronEvcsData], StateType]
    attrs_fn: Callable[[VictronEvcsData], dict[str, Any]] | None = None


SENSORS: tuple[VictronEvcsSensorDescription, ...] = (
    VictronEvcsSensorDescription(
        key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUS_OPTIONS,
        value_fn=_status,
        attrs_fn=_status_attrs,
    ),
    VictronEvcsSensorDescription(
        key="charging_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=_number("actual", "chargPowerTotal"),
    ),
    VictronEvcsSensorDescription(
        key="charging_power_l1",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=_number("actual", "chargPowerL1"),
    ),
    VictronEvcsSensorDescription(
        key="charging_power_l2",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=_number("actual", "chargPowerL2"),
    ),
    VictronEvcsSensorDescription(
        key="charging_power_l3",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=_number("actual", "chargPowerL3"),
    ),
    VictronEvcsSensorDescription(
        key="charging_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=_number("actual", "chargCurrent"),
    ),
    VictronEvcsSensorDescription(
        key="session_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=_number("actual", "energyPerCharg"),
    ),
    VictronEvcsSensorDescription(
        key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=_number("actual", "totalEnergyCntr"),
    ),
    VictronEvcsSensorDescription(
        key="session_duration",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        value_fn=_number("actual", "timePerCharg"),
    ),
    VictronEvcsSensorDescription(
        key="session_cost",
        suggested_display_precision=2,
        value_fn=_number("actual", "costPerCharg"),
    ),
    VictronEvcsSensorDescription(
        key="session_saved_cost",
        suggested_display_precision=2,
        value_fn=_number("actual", "savedCostPerCharg"),
    ),
    VictronEvcsSensorDescription(
        key="cp_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_number("actual", "cpVoltage"),
    ),
    VictronEvcsSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_number("sensors", "ovhT"),
    ),
    VictronEvcsSensorDescription(
        key="cp_duty_cycle",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_number("sensors", "cpDuty"),
    ),
    VictronEvcsSensorDescription(
        key="configured_phases",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_number("actual", "evcsPhase"),
    ),
    VictronEvcsSensorDescription(
        key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_number("common", "wp"),
    ),
    VictronEvcsSensorDescription(
        key="uptime",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_text("common", "ut"),
    ),
    VictronEvcsSensorDescription(
        key="device_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_text("common", "dt"),
    ),
    VictronEvcsSensorDescription(
        key="error",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_fault_text("errCodeStr"),
    ),
    VictronEvcsSensorDescription(
        key="warning",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_fault_text("warnCodeStr"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VictronEvcsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        VictronEvcsSensor(coordinator, description) for description in SENSORS
    )


class VictronEvcsSensor(VictronEvcsEntity, SensorEntity):
    """A sensor reading one field from the charger."""

    entity_description: VictronEvcsSensorDescription

    @property
    def native_value(self) -> StateType:
        """Return the value of the sensor."""
        return self.entity_description.value_fn(self.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes, if this sensor has any."""
        if (attrs_fn := self.entity_description.attrs_fn) is None:
            return None
        return attrs_fn(self.data)
