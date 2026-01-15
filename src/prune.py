import threading
import logging

from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from files import dump_log_to_file

CacheTree = Dict[Path, Dict[str, Any]]


class CachePruner:
    def __init__(
        self,
        cache: CacheTree,
        dt_window,
        lock: Optional[threading.lock] = None,
        interval: float = 5.0,
    ):
        self.cache = cache
        self.dt_window = dt_window
        self.lock = lock or threading.Lock()
        self.interval = float(interval)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._worker, name="log-cache-pruner", daemon=True
        )

    def start(self):
        if not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._worker, name="log-cache-pruner", daemon=True
            )
            self._thread.start()

    def stop(self, timeout: float = 1.0):
        self._stop_event.set()
        self._thread.join(timeout=timeout)

    def _worker(self):
        while not self._stop_event.wait(self.interval):
            self.prune_once()

    def prune_once(self):
        """
        One pass: remove entries older than TIME_WINDOW.
        For entries with count > 1 we print the report before removing.
        """
        logger = logging.getLogger(__name__)
        now = datetime.now()
        to_remove = []
        with self.lock:
            for path, cache in list(self.cache.items()):
                for msg, data in list(cache.items()):
                    first_seen = (
                        data.get("first_seen") if isinstance(data, dict) else None
                    )
                    if first_seen is None:
                        to_remove.append((path, msg, data))
                        continue
                    if now - first_seen > self.dt_window:
                        to_remove.append((path, msg, data))
            for path, msg, data in to_remove:
                removed = self.cache[path].pop(msg, None)
                if removed:
                    cnt = removed.get("count", 0)
                    if cnt > 1:
                        dump_log_to_file(
                            path,
                            now.strftime("%Y-%m-%d %H:%M:%S"),
                            f"{msg} (occurred {cnt} times)",
                        )
                        logger.debug(f"Pruned '{msg} (occurred {cnt} times)'")
