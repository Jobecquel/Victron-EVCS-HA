"""Constants for the Victron EV Charging Station integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "victron_evcs"

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 5
MIN_SCAN_INTERVAL: Final = 1
MAX_SCAN_INTERVAL: Final = 300

# Fast cycles between reads of the slow/diagnostic endpoints.
SLOW_UPDATE_CYCLES: Final = 6

MANUFACTURER: Final = "Victron Energy"
DEFAULT_MODEL: Final = "EV Charging Station"

# /commonDataRead "pid" -> model name
PRODUCT_MODELS: Final[dict[str, str]] = {
    "C023": "EV Charging Station 32A V2",
    "C024": "EV Charging Station (AC22)",
    "C025": "EV Charging Station (AC22E)",
    "C026": "EV Charging Station NS (AC22NS)",
    "C027": "EV Charging Station NS 32A V2",
}

# Charging modes: /chargingParamsRead "chargingMode", written via /chargingModeSet
MODE_MANUAL: Final = 0
MODE_AUTO: Final = 1
MODE_SCHEDULED: Final = 2

MODE_SLUGS: Final[dict[int, str]] = {
    MODE_MANUAL: "manual",
    MODE_AUTO: "auto",
    MODE_SCHEDULED: "scheduled",
}
MODE_VALUES: Final[dict[str, int]] = {slug: mode for mode, slug in MODE_SLUGS.items()}

# carState, as used by the local HTTP API.
#
# WARNING: this enum is NOT the same as Modbus holding register 5015. The two
# agree only on 0 and 1 and diverge from 2 onwards -- over HTTP 6 is "charging"
# and 2 is "waiting for start", while over Modbus those numbers are swapped.
# Do not substitute the published Modbus enum here.
STATE_DISCONNECTED: Final = 0
STATE_CONNECTED: Final = 1
STATE_WAITING_FOR_START: Final = 2
STATE_WAITING_FOR_SUN: Final = 3
STATE_WAITING_FOR_RFID: Final = 4
STATE_LOW_SOC: Final = 5
STATE_CHARGING: Final = 6
STATE_CHARGED: Final = 7
STATE_LIMIT: Final = 8
STATE_UNDEFINED: Final = 255

# carSubState. Any other value (the charger idles at 255) means "no sub-state".
SUB_STATE_SLUGS: Final[dict[int, str]] = {
    0: "starting",
    1: "switching_to_3p",
    2: "switching_to_1p",
    3: "stopping",
}

STATUS_OPTIONS: Final[list[str]] = [
    "disconnected",
    "connected",
    "waiting_for_start",
    "waiting_for_sun",
    "waiting_for_rfid",
    "low_soc",
    "charging",
    "charged",
    "limit",
    "starting",
    "switching_to_3p",
    "switching_to_1p",
    "stopping",
]

# Charging current bounds, used when the charger does not report its own.
DEFAULT_MIN_CURRENT: Final = 6
DEFAULT_MAX_CURRENT: Final = 32
