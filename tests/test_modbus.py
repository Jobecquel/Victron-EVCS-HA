"""Tests for the minimal Modbus TCP writer used for the reboot command."""

from __future__ import annotations

import asyncio
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

from victron_evcs.modbus import (  # noqa: E402
    REG_RESET,
    ModbusError,
    async_write_register,
    build_write_register,
    check_write_register_reply,
)


def test_build_reset_frame() -> None:
    """Writing 1 to register 5064 (0x13C8) on unit 1."""
    frame = build_write_register(7, 1, REG_RESET, 1)
    assert frame.hex() == "000700000006" "01" "06" "13c8" "0001"


def test_echo_reply_is_accepted() -> None:
    frame = build_write_register(1, 1, REG_RESET, 1)
    check_write_register_reply(frame, frame)


def test_exception_reply_is_rejected() -> None:
    frame = build_write_register(1, 1, REG_RESET, 1)
    reply = bytes.fromhex("000100000003" "01" "86" "02")
    with pytest.raises(ModbusError, match="exception code 2"):
        check_write_register_reply(frame, reply)


def test_mismatched_reply_is_rejected() -> None:
    frame = build_write_register(1, 1, REG_RESET, 1)
    other = build_write_register(1, 1, REG_RESET, 0)
    with pytest.raises(ModbusError, match="Unexpected"):
        check_write_register_reply(frame, other)


def _serve(reply_for):
    """Start a one-shot fake Modbus server; reply_for(request) -> bytes."""
    received: list[bytes] = []

    async def handle(reader, writer):
        request = await reader.readexactly(12)
        received.append(request)
        writer.write(reply_for(request))
        await writer.drain()
        writer.close()

    return received, handle


def test_write_register_roundtrip() -> None:
    async def run():
        received, handle = _serve(lambda request: request)
        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            await async_write_register("127.0.0.1", REG_RESET, 1, port=port)
        return received

    received = asyncio.run(run())
    assert received[0][6:] == bytes.fromhex("010613c80001")


def test_write_register_exception() -> None:
    async def run():
        _, handle = _serve(lambda request: request[:4] + bytes.fromhex("0003018604"))
        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            await async_write_register("127.0.0.1", REG_RESET, 1, port=port)

    with pytest.raises(ModbusError, match="exception code 4"):
        asyncio.run(run())


def test_write_register_unreachable() -> None:
    with pytest.raises(ModbusError):
        asyncio.run(async_write_register("127.0.0.1", REG_RESET, 1, port=1, timeout=2))
