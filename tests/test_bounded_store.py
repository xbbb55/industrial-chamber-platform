"""Tests for the bounded in-process cache (P0-4 / A4)."""

import contextlib
import io
import unittest

from backend import memory_router
from backend.bounded_store import BoundedCache


class BoundedCacheTests(unittest.TestCase):
    def test_evicts_oldest_and_keeps_newest(self):
        cache = BoundedCache(3)
        for index in range(5):
            cache[f"k{index}"] = index
        self.assertEqual(len(cache), 3)
        self.assertEqual(list(cache), ["k2", "k3", "k4"])
        self.assertEqual(cache.evicted, 2)

    def test_overwrite_refreshes_recency(self):
        cache = BoundedCache(2)
        cache["a"] = 1
        cache["b"] = 2
        cache["a"] = 3
        cache["c"] = 4
        self.assertEqual(list(cache), ["a", "c"])
        self.assertEqual(cache["a"], 3)

    def test_newest_is_descending_and_limited(self):
        cache = BoundedCache(10)
        for index in range(5):
            cache[index] = index
        self.assertEqual(cache.newest(2), [(4, 4), (3, 3)])
        self.assertEqual(cache.newest(0), [])
        self.assertEqual(list(cache.newest_mapping(2)), [4, 3])

    def test_dict_semantics_are_preserved(self):
        cache = BoundedCache(2)
        cache["x"] = {"be_r": {"successMessage": "Run"}}
        self.assertIn("x", cache)
        self.assertEqual(cache["x"]["be_r"]["successMessage"], "Run")
        self.assertEqual(len(cache), 1)
        cache.clear()
        self.assertEqual(len(cache), 0)

    def test_maxsize_is_at_least_one(self):
        cache = BoundedCache(0)
        self.assertEqual(cache.maxsize, 1)
        cache["a"] = 1
        cache["b"] = 2
        self.assertEqual(list(cache), ["b"])


class PendingQueueCapTests(unittest.TestCase):
    def setUp(self):
        self._limit = memory_router.EDGE_PENDING_COMMAND_LIMIT
        self._records = memory_router.command_records
        self._pending = memory_router.pending_edge_commands

    def tearDown(self):
        memory_router.EDGE_PENDING_COMMAND_LIMIT = self._limit
        memory_router.command_records = self._records
        memory_router.pending_edge_commands = self._pending

    def test_queue_drops_oldest_beyond_limit(self):
        memory_router.EDGE_PENDING_COMMAND_LIMIT = 2
        memory_router.command_records = BoundedCache(50)
        memory_router.pending_edge_commands = {}
        with contextlib.redirect_stdout(io.StringIO()):
            for index in range(5):
                memory_router.queue_edge_command(
                    "EDGE-CAP",
                    {"command_id": f"CMD-{index}", "device_id": "CH-1"},
                )
        queue = memory_router.pending_edge_commands["EDGE-CAP"]
        self.assertEqual([item["command_id"] for item in queue], ["CMD-3", "CMD-4"])
        self.assertEqual(memory_router.command_records["CMD-0"]["status"], "DROPPED")


class ModuleCacheTests(unittest.TestCase):
    def test_command_caches_are_bounded(self):
        self.assertIsInstance(memory_router.command_records, BoundedCache)
        self.assertIsInstance(memory_router.command_results, BoundedCache)
        self.assertIsInstance(memory_router.command_status_events, BoundedCache)
        self.assertEqual(memory_router.command_status_events.maxsize, memory_router.COMMAND_EVENT_CACHE_MAX_ENTRIES)

    def test_status_event_cache_keeps_only_newest(self):
        cache = memory_router.command_status_events
        original = cache.newest_mapping(cache.maxsize)
        try:
            for index in range(cache.maxsize + 5):
                memory_router._remember_command_status_event(f"EV-{index}", {"event_id": f"EV-{index}"})
            self.assertLessEqual(len(cache), cache.maxsize)
            self.assertNotIn("EV-0", cache)
        finally:
            cache.clear()
            for key, value in reversed(list(original.items())):
                cache[key] = value


if __name__ == "__main__":
    unittest.main()
