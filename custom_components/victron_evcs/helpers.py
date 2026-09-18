"""State derivation helpers for the Victron EV Charging Station.

The logic here mirrors the charger's own web UI (``getCarState``,
``getCarSubState`` and ``getChargingButtonState``) so that Home Assistant shows
the same thing the charger's dashboard does.
"""

from __future__ import annotations

from .const import (
    STATE_CHARGED,
    STATE_CHARGING,
    STATE_CONNECTED,
    STATE_DISCONNECTED,
    STATE_LIMIT,
    STATE_LOW_SOC,
    STATE_UNDEFINED,
    STATE_WAITING_FOR_RFID,
    STATE_WAITING_FOR_START,
    STATE_WAITING_FOR_SUN,
    SUB_STATE_SLUGS,
)

# States in which the charger reports itself as switched on regardless of
# whether a sub-state transition is in progress.
_ACTIVE_STATES = frozenset(
    {
        STATE_WAITING_FOR_SUN,
        STATE_WAITING_FOR_RFID,
        STATE_LOW_SOC,
        STATE_CHARGING,
        STATE_CHARGED,
        STATE_LIMIT,
    }
)

# States that only count as switched on while a sub-state transition is active.
_PENDING_STATES = frozenset({STATE_CONNECTED, STATE_WAITING_FOR_START})

# Fallback labels per carState, used when no sub-state overrides them.
_STATE_SLUGS = {
    STATE_WAITING_FOR_START: "waiting_for_start",
    STATE_WAITING_FOR_SUN: "waiting_for_sun",
    STATE_WAITING_FOR_RFID: "waiting_for_rfid",
    STATE_LOW_SOC: "low_soc",
    STATE_CHARGING: "charging",
    STATE_CHARGED: "charged",
}


def sub_state_slug(car_sub_state: int | None) -> str | None:
    """Return the slug for an active sub-state, or None if there isn't one."""
    if car_sub_state is None:
        return None
    return SUB_STATE_SLUGS.get(car_sub_state)


def charging_status(car_state: int | None, car_sub_state: int | None) -> str | None:
    """Return the status slug shown by the charger's dashboard."""
    if car_state is None:
        return None
    if car_state in (STATE_DISCONNECTED, STATE_UNDEFINED):
        return "disconnected"
    # "Limit" is the one state the UI never lets a sub-state override.
    if car_state == STATE_LIMIT:
        return "limit"
    if (sub := sub_state_slug(car_sub_state)) is not None:
        return sub
    # Anything unrecognised falls back to "connected", as the web UI does.
    return _STATE_SLUGS.get(car_state, "connected")


def is_charging_enabled(car_state: int | None, car_sub_state: int | None) -> bool:
    """Return True when the charger's start/stop button reads "Stop"."""
    if car_state is None:
        return False
    if car_state in _ACTIVE_STATES:
        return True
    return car_state in _PENDING_STATES and sub_state_slug(car_sub_state) is not None


def active_phase_count(*phase_powers: float | None) -> int:
    """Return how many phases are currently drawing power."""
    return sum(1 for power in phase_powers if power is not None and power > 0)
