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


class LinkMonitor:
    """Tracks how long the charger's HTTP API has been unreachable.

    Times are plain seconds from a monotonic clock, passed in by the caller so
    the logic can be tested without waiting.
    """

    def __init__(self, grace: float, failsafe_after: float, failsafe_retry: float) -> None:
        """Initialise with the link up."""
        self._grace = grace
        self._failsafe_after = failsafe_after
        self._failsafe_retry = failsafe_retry
        self._lost_since: float | None = None
        self._last_failsafe: float | None = None

    @property
    def connected(self) -> bool:
        """Return True while the last poll succeeded."""
        return self._lost_since is None

    def success(self) -> None:
        """Record a successful poll."""
        self._lost_since = None
        self._last_failsafe = None

    def failure(self, now: float) -> None:
        """Record a failed poll."""
        if self._lost_since is None:
            self._lost_since = now

    def lost_for(self, now: float) -> float:
        """Return how long the link has been down, 0 if it is up."""
        return 0.0 if self._lost_since is None else now - self._lost_since

    def within_grace(self, now: float) -> bool:
        """Return True while a failure is still short enough to ride out."""
        return self.lost_for(now) < self._grace

    def failsafe_due(self, now: float) -> bool:
        """Return True when the failsafe reboot should be sent now."""
        if self.lost_for(now) < self._failsafe_after:
            return False
        return self._last_failsafe is None or now - self._last_failsafe >= self._failsafe_retry

    def failsafe_sent(self, now: float) -> None:
        """Record that the failsafe reboot was sent."""
        self._last_failsafe = now
