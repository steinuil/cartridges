import os
from pathlib import Path
from typing import BinaryIO, ContextManager, TypedDict


class Pcsx2Error(Exception):
    pass


class Pcsx2InvalidCacheError(Pcsx2Error):
    pass


class Pcsx2InvalidCacheEntryError(Pcsx2Error):
    pass


class Pcsx2GameCacheEntry(TypedDict):
    path: Path
    serial: str
    name: str


def _read_int(f: BinaryIO, size: int) -> int:
    return int.from_bytes(f.read(size), "little")


def _read_length_prefixed_string(f: BinaryIO) -> bytes:
    len = _read_int(f, 4)
    string = f.read(len)
    return string


# Based on https://github.com/PCSX2/pcsx2/blob/671255c68444359a96f90d7719c01d0a589f8c30/pcsx2/GameList.cpp
class Pcsx2GameCacheReader:
    def __init__(self, gamelist_path: Path):
        self.stream = open(gamelist_path, "rb")
        magic = self.stream.read(4)

        if magic != b"GLCE":
            raise Pcsx2InvalidCacheError

        self.stream_length = self.stream.seek(0, os.SEEK_END)
        self.stream.seek(8)

    def __enter__(self) -> ContextManager:
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.stream.close()

    def get_game_data(self) -> Pcsx2GameCacheEntry | None:
        if self.stream.tell() >= self.stream_length:
            raise StopIteration

        path = _read_length_prefixed_string(self.stream)
        serial = _read_length_prefixed_string(self.stream)
        title = _read_length_prefixed_string(self.stream)
        _title_sort = _read_length_prefixed_string(self.stream)
        title_english = _read_length_prefixed_string(self.stream)
        _type = _read_int(self.stream, 1)
        _region = _read_int(self.stream, 1)
        _total_size = _read_int(self.stream, 8)
        _last_modified_time = _read_int(self.stream, 8)
        _crc32 = _read_int(self.stream, 4)
        _compatibility_rating = _read_int(self.stream, 1)

        try:
            path = Path(path.decode())
            serial = serial.decode()
            name = (title_english or title).decode()
        except UnicodeError:
            raise Pcsx2InvalidCacheEntryError

        # The game cache file may contain older entries for files that have been moved.
        if not path.exists():
            return None

        return Pcsx2GameCacheEntry(
            path=path,
            serial=serial,
            name=name,
        )
