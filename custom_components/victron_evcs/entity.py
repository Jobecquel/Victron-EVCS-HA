"""Base entity for the Victron EV Charging Station."""

from __future__ import annotations

from time import monotonic
from typing import Any

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import VictronEvcsCoordinator, VictronEvcsData

# How long a locally applied value is trusted before the charger's own reading
# wins again. The charger needs roughly a second to reflect a command.
OPTIMISTIC_TTL = 3.0


class OptimisticValue:
    """Holds a value we just wrote until the charger confirms it.

    Without this a control snaps back to its old value for one poll after
    being changed, because the charger takes about a second to report the new
    one. The local value is dropped as soon as the charger agrees, and in any
    case once it expires, so a command the charger silently ignored cannot
    leave the entity showing something untrue indefinitely.
    """

    def __init__(self, ttl: float = OPTIMISTIC_TTL) -> None:
        """Initialise with no pending value."""
        self._value: Any = None
        self._expires = 0.0
        self._ttl = ttl

    def set(self, value: Any) -> None:
        """Record a value we just sent to the charger."""
        self._value = value
        self._expires = monotonic() + self._ttl

    def clear(self) -> None:
        """Forget any pending value."""
        self._value = None

    def get(self, reported: Any) -> Any:
        """Return the value to show, preferring ours while it is still valid."""
        if self._value is None:
            return reported
        if reported == self._value or monotonic() >= self._expires:
            self._value = None
            return reported
        return self._value


class VictronEvcsEntity(CoordinatorEntity[VictronEvcsCoordinator]):
    """Common behaviour for every Victron EVCS entity."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: VictronEvcsCoordinator, description: EntityDescription
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial}_{description.key}"
        self._attr_translation_key = description.translation_key or description.key
        self._attr_device_info = coordinator.device_info

    @property
    def data(self) -> VictronEvcsData:
        """Return the latest poll."""
        return self.coordinator.data

    @property
    def actual(self) -> dict[str, Any]:
        """Return the latest /actualStateRead payload."""
        return self.coordinator.data.actual

    @property
    def params(self) -> dict[str, Any]:
        """Return the latest /chargingParamsRead payload."""
        return self.coordinator.data.params
