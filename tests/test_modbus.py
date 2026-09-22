"""Le client Modbus TCP face à la fausse VMC, sans Home Assistant."""

from __future__ import annotations

import pytest

from custom_components.aldes_inspirair.modbus import AldesModbusClient, AldesModbusError

from .fake_vmc import FakeVmc


async def test_reads_signed_values(vmc: FakeVmc) -> None:
    vmc.registers[350] = -512  # -5,12 °C
    client = AldesModbusClient("127.0.0.1", vmc.port, 2)
    assert await client.read(350, 2) == [-512, 2732]


async def test_protected_registers_need_unlock(vmc: FakeVmc) -> None:
    client = AldesModbusClient("127.0.0.1", vmc.port, 2)
    assert await client.read(356, 2) == [-1, -1]
    await client.unlock()
    assert await client.read(356, 2) == [120, 120]


async def test_write_uses_fc16_on_a_single_register(vmc: FakeVmc) -> None:
    client = AldesModbusClient("127.0.0.1", vmc.port, 2)
    await client.write(257, 3)
    assert vmc.writes == [(16, 257, 3)]
    assert vmc.registers[257] == 3


async def test_negative_values_are_written_as_two_complement(vmc: FakeVmc) -> None:
    client = AldesModbusClient("127.0.0.1", vmc.port, 2)
    await client.write(278, -10)
    assert vmc.registers[278] == -10


async def test_modbus_exception_is_raised(vmc: FakeVmc) -> None:
    vmc.reject_writes = True
    client = AldesModbusClient("127.0.0.1", vmc.port, 2)
    with pytest.raises(AldesModbusError, match="exception Modbus 4"):
        await client.write(257, 3)


async def test_wrong_slave_gets_no_answer(vmc: FakeVmc) -> None:
    client = AldesModbusClient("127.0.0.1", vmc.port, 7, timeout=1)
    with pytest.raises(AldesModbusError):
        await client.read(257, 1)


async def test_unreachable_gateway(vmc: FakeVmc) -> None:
    await vmc.stop()
    client = AldesModbusClient("127.0.0.1", vmc.port, 2, timeout=1)
    with pytest.raises(AldesModbusError, match="impossible"):
        await client.read(257, 1)
