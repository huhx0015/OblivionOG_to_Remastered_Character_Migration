"""Little-endian binary reader for Oblivion ESS files."""

from __future__ import annotations

import struct
from io import BytesIO


class BinaryReader:
    def __init__(self, data: bytes | BytesIO) -> None:
        self._buf = BytesIO(data) if isinstance(data, (bytes, bytearray)) else data

    @property
    def pos(self) -> int:
        return self._buf.tell()

    @property
    def remaining(self) -> int:
        cur = self._buf.tell()
        self._buf.seek(0, 2)
        end = self._buf.tell()
        self._buf.seek(cur)
        return end - cur

    def seek(self, pos: int) -> None:
        self._buf.seek(pos)

    def skip(self, n: int) -> None:
        self._buf.seek(n, 1)

    def read(self, n: int) -> bytes:
        data = self._buf.read(n)
        if len(data) != n:
            raise EOFError(f"needed {n} bytes at {self.pos - len(data)}, got {len(data)}")
        return data

    def u8(self) -> int:
        return self.read(1)[0]

    def i8(self) -> int:
        return struct.unpack("<b", self.read(1))[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.read(2))[0]

    def i16(self) -> int:
        return struct.unpack("<h", self.read(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.read(4))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self.read(4))[0]

    def f64(self) -> float:
        return struct.unpack("<d", self.read(8))[0]

    def bstring(self) -> str:
        """Byte-length prefixed string (plugin names, most ESS strings)."""
        n = self.u8()
        raw = self.read(n) if n else b""
        return raw.split(b"\x00", 1)[0].decode("latin-1", errors="replace")

    def peek(self, n: int) -> bytes:
        data = self._buf.read(n)
        self._buf.seek(-len(data), 1)
        return data
