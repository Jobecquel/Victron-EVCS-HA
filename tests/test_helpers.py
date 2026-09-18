"""Tests for the Victron EVCS state derivation.

These cover the pure logic only, so they run without Home Assistant installed.
The payloads below were captured from a real EV Charging Station NS (product
C026, firmware v2.1).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

# Import the integration's leaf modules without executing its __init__, which
# would pull in Home Assistant.
_COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "victron_evcs"
_pkg = types.ModuleType("victron_evcs")
_pkg.__path__ = [str(_COMPONENT)]
sys.modules.setdefault("victron_evcs", _pkg)

from victron_evcs.helpers import (  # noqa: E402
    active_phase_count,
    charging_status,
    is_charging_enabled,
    sub_state_slug,
)

# A real /actualStateRead body, car disconnected.
IDLE_STATE = {
    "chargPowerL1": 0.00,
    "chargPowerL2": 0.00,
    "chargPowerL3": 0.00,
    "chargPowerTotal": 0.00,
    "chargCurrent": 0.00,
    "carState": 0,
    "carSubState": 255,
    "chCurrMin": 6,
    "chCurrMax": 32,
    "totalEnergyCntr": 351.75,
    "useModbus": 0,
    "useSched": 0,
}


class TestChargingStatus:
    """The status slug must match what the charger's own dashboard shows."""

    @pytest.mark.parametrize(
        ("car_state", "expected"),
        [
            (0, "disconnected"),
            (1, "connected"),
            (2, "waiting_for_start"),
            (3, "waiting_for_sun"),
            (4, "waiting_for_rfid"),
            (5, "low_soc"),
            (6, "charging"),
            (7, "charged"),
            (8, "limit"),
            (255, "disconnected"),
        ],
    )
    def test_plain_states(self, car_state: int, expected: str) -> None:
        """Each carState maps to its own label when no sub-state is active."""
        assert charging_status(car_state, 255) == expected

    def test_http_enum_is_not_the_modbus_enum(self) -> None:
        """Guard against someone substituting the published Modbus enum.

        Over Modbus register 5015, 2 means charging and 6 means waiting for
        start. Over this HTTP API they are the other way round.
        """
        assert charging_status(6, 255) == "charging"
        assert charging_status(2, 255) == "waiting_for_start"

    @pytest.mark.parametrize(
        ("sub_state", "expected"),
        [
            (0, "starting"),
            (1, "switching_to_3p"),
            (2, "switching_to_1p"),
            (3, "stopping"),
        ],
    )
    def test_sub_state_overrides(self, sub_state: int, expected: str) -> None:
        """An active sub-state replaces the state label."""
        assert charging_status(1, sub_state) == expected
        assert charging_status(6, sub_state) == expected

    def test_limit_ignores_sub_state(self) -> None:
        """Limit is the one state the dashboard never overrides."""
        assert charging_status(8, 0) == "limit"

    def test_disconnected_ignores_sub_state(self) -> None:
        """A disconnected car stays disconnected."""
        assert charging_status(0, 0) == "disconnected"

    def test_unknown_state_falls_back_to_connected(self) -> None:
        """Unrecognised states fall back the way the web UI does."""
        assert charging_status(99, 255) == "connected"

    def test_missing_state(self) -> None:
        """A missing carState yields no status rather than a wrong one."""
        assert charging_status(None, None) is None

    def test_captured_idle_payload(self) -> None:
        """The real idle payload reads as disconnected."""
        assert (
            charging_status(IDLE_STATE["carState"], IDLE_STATE["carSubState"])
            == "disconnected"
        )


class TestIsChargingEnabled:
    """Mirrors the charger's own Start/Stop button logic."""

    @pytest.mark.parametrize("car_state", [3, 4, 5, 6, 7, 8])
    def test_active_states_are_on(self, car_state: int) -> None:
        """These states show "Stop" regardless of sub-state."""
        assert is_charging_enabled(car_state, 255) is True

    @pytest.mark.parametrize("car_state", [1, 2])
    def test_pending_states_need_a_sub_state(self, car_state: int) -> None:
        """Connected and waiting-for-start only count while transitioning."""
        assert is_charging_enabled(car_state, 255) is False
        assert is_charging_enabled(car_state, 0) is True

    def test_disconnected_is_off(self) -> None:
        """A disconnected car is never on."""
        assert is_charging_enabled(0, 255) is False
        assert is_charging_enabled(0, 0) is False

    def test_missing_state_is_off(self) -> None:
        """Missing data is not treated as charging."""
        assert is_charging_enabled(None, None) is False

    def test_captured_idle_payload(self) -> None:
        """The real idle payload reads as off."""
        assert (
            is_charging_enabled(IDLE_STATE["carState"], IDLE_STATE["carSubState"])
            is False
        )


class TestSubStateSlug:
    """Only 0-3 are real sub-states."""

    def test_idle_sentinel(self) -> None:
        """The charger idles at 255, which is not a sub-state."""
        assert sub_state_slug(255) is None

    def test_missing(self) -> None:
        """Missing data is not a sub-state."""
        assert sub_state_slug(None) is None

    def test_known(self) -> None:
        """Known sub-states map to slugs."""
        assert sub_state_slug(0) == "starting"


class TestActivePhaseCount:
    """Counts how many phases are actually drawing power."""

    def test_idle(self) -> None:
        """Nothing drawing means zero phases."""
        assert active_phase_count(0.0, 0.0, 0.0) == 0

    def test_single_phase(self) -> None:
        """One phase drawing means 1P."""
        assert active_phase_count(3680.0, 0.0, 0.0) == 1

    def test_three_phase(self) -> None:
        """Three phases drawing means 3P."""
        assert active_phase_count(3680.0, 3680.0, 3680.0) == 3

    def test_missing_values_ignored(self) -> None:
        """Absent phases do not count."""
        assert active_phase_count(3680.0, None, None) == 1
