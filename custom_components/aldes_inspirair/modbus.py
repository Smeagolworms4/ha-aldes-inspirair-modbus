"""Client Modbus TCP minimal pour la VMC, sans dépendance externe.

La VMC n'accepte que FC03 en lecture et FC16 en écriture (FC06 est refusé).
"""

from __future__ import annotations

import asyncio
import struct

from .const import UNLOCK_CODE, UNLOCK_REGISTER


class AldesModbusError(Exception):
    """Erreur de communication ou exception Modbus."""


class AldesModbusClient:
    """Une connexion TCP par transaction, sérialisées par un verrou."""

    def __init__(self, host: str, port: int, slave: int, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.slave = slave
        self.timeout = timeout
        self._lock = asyncio.Lock()
        self._tid = 0

    async def _transact(self, pdu: bytes) -> bytes:
        async with self._lock:
            self._tid = (self._tid + 1) & 0xFFFF
            expected = self._tid
            frame = struct.pack(">HHHB", expected, 0, len(pdu) + 1, self.slave) + pdu
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), self.timeout
                )
            except (OSError, TimeoutError) as err:
                raise AldesModbusError(f"connexion à {self.host}:{self.port} impossible : {err}") from err
            try:
                writer.write(frame)
                await writer.drain()
                header = await asyncio.wait_for(reader.readexactly(7), self.timeout)
                tid, _, length, _ = struct.unpack(">HHHB", header)
                body = await asyncio.wait_for(reader.readexactly(length - 1), self.timeout)
            except (OSError, TimeoutError, asyncio.IncompleteReadError) as err:
                raise AldesModbusError(f"pas de réponse de la VMC : {err}") from err
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
            if tid != expected:
                raise AldesModbusError("réponse Modbus désynchronisée")
        if body[0] & 0x80:
            raise AldesModbusError(f"exception Modbus {body[1]} (fonction {body[0] & 0x7F})")
        return body

    async def read(self, address: int, count: int) -> list[int]:
        """Lit des registres de maintien (valeurs signées 16 bits)."""
        body = await self._transact(struct.pack(">BHH", 3, address, count))
        size = body[1]
        return list(struct.unpack(f">{size // 2}h", body[2 : 2 + size]))

    async def write(self, address: int, value: int) -> None:
        """Écrit un registre en FC16."""
        await self._transact(struct.pack(">BHHBH", 16, address, 1, 2, value & 0xFFFF))

    async def unlock(self) -> None:
        """Envoie le code installateur qui ouvre les registres protégés."""
        await self.write(UNLOCK_REGISTER, UNLOCK_CODE)
