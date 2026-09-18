"""Data update coordinator for the Victron EV Charging Station."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VictronEvcsClient, VictronEvcsError
from .const import (
    DEFAULT_MODEL,
    DOMAIN,
    MANUFACTURER,
    PRODUCT_MODELS,
    SLOW_UPDATE_CYCLES,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VictronEvcsData:
    """One poll's worth of charger data."""

    actual: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    sensors: dict[str, Any] = field(default_factory=dict)
    common: dict[str, Any] = field(default_factory=dict)


class VictronEvcsCoordinator(DataUpdateCoordinator[VictronEvcsData]):
    """Polls the charger and shares the result with every entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: VictronEvcsClient,
        scan_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.serial: str | None = None
        self.firmware: str | None = None
        self.model: str = DEFAULT_MODEL
        self.device_name: str | None = None
        self._cycle = 0
        self._sensors: dict[str, Any] = {}
        self._common: dict[str, Any] = {}

    async def _async_setup(self) -> None:
        """Read the charger's identity once, before the first refresh."""
        try:
            common = await self.client.async_common_data()
        except VictronEvcsError as err:
            raise UpdateFailed(str(err)) from err

        self._common = common
        self.serial = common.get("sn")
        self.firmware = common.get("fw")
        self.model = PRODUCT_MODELS.get(str(common.get("pid", "")).upper(), DEFAULT_MODEL)
        _LOGGER.debug(
            "Connected to %s (serial %s, firmware %s)", self.model, self.serial, self.firmware
        )

    async def _async_update_data(self) -> VictronEvcsData:
        """Fetch the current state of the charger."""
        try:
            actual = await self.client.async_actual_state()
            params = await self.client.async_charging_params()
            # The diagnostic endpoints change slowly and cost an extra round
            # trip each, so they are read on a slower cadence.
            if self._cycle % SLOW_UPDATE_CYCLES == 0:
                self._sensors = await self.client.async_sensors()
                self._common = await self.client.async_common_data()
        except VictronEvcsError as err:
            raise UpdateFailed(str(err)) from err

        self._cycle += 1
        if name := actual.get("deviceName"):
            self.device_name = name

        return VictronEvcsData(
            actual=actual,
            params=params,
            sensors=self._sensors,
            common=self._common,
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device entry for this charger."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial or self.client.host)},
            manufacturer=MANUFACTURER,
            model=self.model,
            name=self.device_name or self.model,
            serial_number=self.serial,
            sw_version=self.firmware,
            configuration_url=self.client.base_url,
        )
