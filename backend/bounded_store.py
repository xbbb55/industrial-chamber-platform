"""A tiny bounded mapping used for in-process command state (P0-4 / A4).

Command records, command results and command status events used to live in plain
dicts that never evicted, so a long-running control center grew without bound
while also returning the entire collection from the HTTP API.

This subclass keeps normal dict semantics (indexing, membership, len, clear) so
existing call sites and tests keep working, while enforcing a hard capacity
limit and dropping the oldest entry first.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Iterator

DEFAULT_MAX_ENTRIES = 1000


class BoundedCache(OrderedDict):
    """OrderedDict that evicts the oldest entry once maxsize is exceeded."""

    def __init__(self, maxsize: int = DEFAULT_MAX_ENTRIES, *args: Any, **kwargs: Any) -> None:
        self.maxsize = max(int(maxsize), 1)
        self.evicted = 0
        super().__init__(*args, **kwargs)
        self._trim()

    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self:
            # Re-insert so the entry counts as the newest one.
            super().__delitem__(key)
        super().__setitem__(key, value)
        self._trim()

    def _trim(self) -> None:
        while len(self) > self.maxsize:
            super().popitem(last=False)
            self.evicted += 1

    def newest(self, limit: int = 100) -> list[tuple[Any, Any]]:
        """Return up to limit entries, newest first."""
        count = max(int(limit), 0)
        if count == 0:
            return []
        return list(reversed(list(self.items())[-count:]))

    def newest_mapping(self, limit: int = 100) -> dict[Any, Any]:
        """Return the newest entries as a plain dict, keeping newest-first order."""
        return dict(self.newest(limit))

    def iter_newest(self, limit: int = 100) -> Iterator[Any]:
        for key, _ in self.newest(limit):
            yield key
