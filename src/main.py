import time
import os
import threading
import logging

from pathlib import Path
from typing import Dict, Any
from config import parse_options
from prune import CachePruner
from files import discover_files, tail_file

CacheTree = Dict[Path, Dict[str, Any]]

CACHE_MAP: CacheTree = {}
CACHE_MAP_LOCK = threading.Lock()
STOP_EVENT = threading.Event()

def main():
    opts = parse_options()
    logger = logging.getLogger(__name__)
    logger.info("Application started with options:\n%s", opts)

    pruner = CachePruner(
        cache=CACHE_MAP,
        dt_window=opts.agg_interval,
        lock=CACHE_MAP_LOCK,
        interval=opts.prune_interval,
    )
    pruner.start()

    logger.info("Starting log monitor... Press Ctrl+C to stop.")
    threads: Dict[Path, threading.Thread] = {}
    
    try:
        while True:
            discovered_files = discover_files(opts.source_files)
            
            for file_path in discovered_files:
                if file_path not in threads or not threads[file_path].is_alive():
                    logger.info(f"Discovered new or inactive file, starting thread: {file_path}")
                    thread = threading.Thread(
                        target=tail_file, 
                        args=(file_path, CACHE_MAP, CACHE_MAP_LOCK, opts, STOP_EVENT), 
                        daemon=True,
                        name=f"Tail-{file_path.name}"
                    )
                    threads[file_path] = thread
                    thread.start()

            stale_files = set(threads.keys()) - set(discovered_files)
            for file_path in stale_files:
                logger.debug(f"File removed, cleaning up thread: {file_path}")
                # The thread will stop on its own due to FileNotFoundError or STOP_EVENT
                # We just need to remove it from our tracking dictionary
                # Optional: you could join it here, but it might block the main loop.
                # The final join() at shutdown is usually sufficient.
                del threads[file_path]
                with CACHE_MAP_LOCK:
                    if file_path in CACHE_MAP:
                        del CACHE_MAP[file_path]

            time.sleep(opts.time_wait)

    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Stopping all threads...")
    finally:
        STOP_EVENT.set()
        logger.info("Waiting for file tailing threads to complete...")
        active_threads = list(threads.values())
        for thread in active_threads:
            thread.join(timeout=5.0) 
            if thread.is_alive():
                logger.warning(f"Thread {thread.name} did not exit gracefully.")

        logger.info("Stopping cache pruner...")
        pruner.stop()
        logger.info("Application shut down successfully.")


if __name__ == "__main__":
    main()
