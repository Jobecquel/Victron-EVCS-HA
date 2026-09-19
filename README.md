# Victron EV Charging Station for Home Assistant

**Built by [becquel.com](https://becquel.com)**

> ## ⚠️ Experimental — do not deploy this
>
> This is an **experimental test** of connecting a Victron EV Charging Station to Home
> Assistant. It is **not meant to be deployed** and we **warn against using it**.
>
> It is **not tested**. Neither **becquel.com** nor **Victron Energy** has validated,
> approved or tested this integration in any way. It carries no warranty, no support and
> no guarantee of correctness, and it may stop working or behave unexpectedly at any time.
>
> It controls mains-connected EV charging equipment. Use it at your own risk.

A HACS custom integration that adds a Victron EV Charging Station to Home Assistant as a
proper device, with start/stop control, a charging-current setpoint, live power, and a
set of extra sensors.

It talks to the **charger directly over your LAN** using the local HTTP API that the
charger's own web interface uses. No GX device, no Cerbo, no VRM cloud account, and no
MQTT broker are involved.

![local polling](https://img.shields.io/badge/iot__class-local__polling-blue)

## Compatibility

Developed against an **EV Charging Station NS (product `C026`, firmware `v2.1`)**.
It may work on any EVCS whose web UI serves the same endpoints — products `C023`,
`C024`, `C025`, `C026` and `C027` are recognised by name.

A charger firmware update may change the behaviour this relies on. If that happens the
integration will mark its entities unavailable and log the failure rather than quietly
reporting stale values.

## Installation

### HACS

1. In HACS, go to **Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/Jobecquel/Victron-EVCS-HA` with category **Integration**.
3. Install **Victron EV Charging Station**, then restart Home Assistant.

### Manual

Copy `custom_components/victron_evcs/` into your Home Assistant `config/custom_components/`
directory and restart.

## Setup

**Settings → Devices & Services → Add Integration → Victron EV Charging Station**.

Enter the charger's IP address or hostname — the address of the **charger itself**, not of
a GX device. The polling interval defaults to 5 seconds and can be changed later under the
integration's **Configure** option. The charger's own web UI polls at 1 second, so short
intervals are fine.

The charger is identified by its serial number, so its entities survive a change of IP
address.

## Entities

### Controls

| Entity | Description |
| --- | --- |
| `switch.*_charging` | Starts and stops charging |
| `number.*_charging_current` | Charging current setpoint, in amps, bounded by the charger's own reported minimum and maximum |
| `select.*_charging_mode` | Manual / Auto / Scheduled |

### Sensors

| Entity | Notes |
| --- | --- |
| `sensor.*_status` | Disconnected, Connected, Waiting for start, Waiting for sun, Waiting for RFID, Low battery SoC, Charging, Charged, Charging limit, plus the transitional Starting / Stopping / Switching states |
| `sensor.*_charging_power` | Total charging power, in watts |
| `sensor.*_charging_power_l1/l2/l3` | Per-phase power |
| `sensor.*_charging_current` | Measured charging current |
| `sensor.*_session_energy` | Energy delivered this session |
| `sensor.*_total_energy` | Lifetime counter, suitable for the Energy dashboard |
| `sensor.*_session_duration` | Length of the current session |
| `sensor.*_session_cost`, `sensor.*_session_saved_cost` | As calculated by the charger, in its own configured currency |
| `binary_sensor.*_car_connected`, `binary_sensor.*_charging` | Plug and charging state |
| `binary_sensor.*_problem`, `binary_sensor.*_warning` | Fault flags |

Diagnostic entities cover control-pilot voltage and duty cycle, temperature, configured
phases, Wi-Fi signal, uptime, device clock, and the active error and warning text. Some
are disabled by default; enable them from the device page.

## Notes

- **Charging modes are gated by the charger.** *Auto* requires a paired GX device and
  *Scheduled* requires a configured schedule; the mode select only offers what your
  charger will actually accept.
- **The current setpoint is per mode.** The charger keeps separate manual, auto and
  scheduled setpoints. The number entity shows and writes the one belonging to the active
  mode, and its `charging_mode` attribute says which that is. In Auto mode the charger
  manages the current itself and will override a value you set.
- **Turning the switch on with no car connected does nothing.** The charger only enters a
  charging-enabled state once the control pilot sees a vehicle, so the switch will bounce
  back to off. That is the charger's behaviour, not a bug in the integration.
- **The local API is unauthenticated.** Anyone on your network can read from and control
  this charger over plain HTTP. That is true of the device itself regardless of this
  integration, but it is worth knowing.

## About becquel.com

This is an experiment from **[becquel.com](https://becquel.com)**, where we work on
solar, storage and EV charging systems.

It is a test of what a Victron charger could look like as a first-class Home Assistant
device. It is **not a becquel.com product**, it is not supported or maintained, and it has
not been validated or approved by becquel.com or by Victron Energy.

## Development

The state-derivation logic is pure and tested without Home Assistant installed:

```bash
python -m pytest tests/
```

## License

MIT — see [LICENSE](LICENSE). © [becquel.com](https://becquel.com)

---

<p align="center"><sub>Made with care by <a href="https://becquel.com">becquel.com</a></sub></p>
