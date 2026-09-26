"""Minimal Modbus TCP writer for the few commands the HTTP API lacks.

The charger runs its Modbus TCP server independently of its web server, so a
command sent here still gets through when the HTTP API has stopped answering.
Only "write single register" (function 0x06) is needed, which is small enough
not to justify a dependency.
"""

from __future__ import annotations

import asyncio
import struct
from itertools import count

MODBUS_PORT = 502
MODBUS_UNIT_ID = 1
MODBUS_TIMEOUT = 5

FC_WRITE_SINGLE_REGISTER = 0x06

# EVCS register list: 5064 "EVCS reset", 1 = reset command.
REG_RESET = 5064

_transaction_ids = count(1)


class ModbusError(Exception):
    """A Modbus request failed or was rejected."""


def build_write_register(transaction_id: int, unit_id: int, register: int, value: int) -> bytes:
    """Return a Modbus TCP "write single register" request frame."""
    pdu = struct.pack(">BHH", FC_WRITE_SINGLE_REGISTER, register, value)
    # MBAP header: transaction id, protocol id 0, length (unit id + PDU), unit id.
    return struct.pack(">HHHB", transaction_id & 0xFFFF, 0, len(pdu) + 1, unit_id) + pdu


def check_write_register_reply(request: bytes, reply: bytes) -> None:
    """Raise ModbusError unless ``reply`` acknowledges ``request``.

    A successful "write single register" reply echoes the request exactly.
    An exception reply sets the high bit of the function code and carries the
    exception code in the next byte.
    """
    if len(reply) >= 9 and reply[7] == FC_WRITE_SINGLE_REGISTER | 0x80:
        raise ModbusError(f"Modbus exception code {reply[8]}")
    if reply != request:
        raise ModbusError(f"Unexpected Modbus reply: {reply.hex()}")


async def async_write_register(
    host: str,
    register: int,
    value: int,
    *,
    port: int = MODBUS_PORT,
    unit_id: int = MODBUS_UNIT_ID,
    timeout: float = MODBUS_TIMEOUT,
) -> None:
    """Write one holding register and wait for the charger's echo."""
    request = build_write_register(next(_transaction_ids), unit_id, register, value)
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection(host, port)
            try:
                writer.write(request)
                await writer.drain()
                header = await reader.readexactly(6)
                (length,) = struct.unpack(">H", header[4:6])
                reply = header + await reader.readexactly(length)
            finally:
                writer.close()
    except TimeoutError as err:
        raise ModbusError(f"Timeout writing register {register}") from err
    except (OSError, asyncio.IncompleteReadError) as err:
        raise ModbusError(f"Error writing register {register}: {err}") from err

    check_write_register_reply(request, reply)
