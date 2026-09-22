"""Une fausse VMC InspirAIR Top derrière une passerelle Modbus TCP.

Reproduit ce qui a été mesuré sur une vraie machine : registres protégés à -1 tant que
le code installateur n'a pas été écrit dans le registre 16, FC06 refusé, esclave 2.
"""

from __future__ import annotations

import asyncio
import struct

UNIT = 2
UNLOCK_CODE = 34102

# Relevé réel (firmware 291), bypass ouvert, niveau « quotidien ».
SNAPSHOT = {
    12: 291, 257: 1, 258: 1, 259: 1, 261: 2, 267: 6, 278: 100,
    320: 3000, 321: 3350, 346: 2, 347: 125, 348: 1,
    350: 2604, 351: 2732, 352: 2795, 353: 2631,
    354: 1241, 355: 2474, 356: 120, 357: 120, 384: 0,
}
PROTECTED = {320, 321, 352, 353, 354, 355, 356, 357}


class FakeVmc:
    def __init__(self) -> None:
        self.registers = dict(SNAPSHOT)
        self.unlocked = False
        self.silent = False          # la passerelle ne reçoit plus de réponse de la VMC
        self.reject_writes = False   # la VMC renvoie une exception sur toute écriture
        self.writes: list[tuple[int, int, int]] = []  # (fonction, registre, valeur)
        self.port = 0
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def settings_writes(self) -> list[tuple[int, int]]:
        """Écritures hors déverrouillage."""
        return [(reg, value) for _, reg, value in self.writes if reg != 16]

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                tid, _, length, unit = struct.unpack(">HHHB", await reader.readexactly(7))
                pdu = await reader.readexactly(length - 1)
                if self.silent or unit != UNIT:
                    break  # une passerelle sans réponse de l'esclave finit par couper
                response = self._process(pdu)
                writer.write(struct.pack(">HHHB", tid, 0, len(response) + 1, unit) + response)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()

    def _process(self, pdu: bytes) -> bytes:
        function = pdu[0]
        if function == 3:
            address, count = struct.unpack(">HH", pdu[1:5])
            values = [self._read(a) & 0xFFFF for a in range(address, address + count)]
            return bytes([3, 2 * count]) + struct.pack(f">{count}H", *values)
        if function == 16:
            address, count, size = struct.unpack(">HHB", pdu[1:6])
            if self.reject_writes:
                return bytes([0x90, 4])
            for offset, value in enumerate(struct.unpack(f">{count}H", pdu[6 : 6 + size])):
                self._write(function, address + offset, value)
            return struct.pack(">BHH", 16, address, count)
        return bytes([function | 0x80, 1])  # FC06 & co : fonction illégale, comme la vraie

    def _read(self, address: int) -> int:
        if address in PROTECTED and not self.unlocked:
            return -1
        return self.registers.get(address, -1)

    def _write(self, function: int, address: int, value: int) -> None:
        self.writes.append((function, address, value))
        if address == 16:
            self.unlocked = value == UNLOCK_CODE
            return
        self.registers[address] = value - 0x10000 if value > 0x7FFF else value
