import glob
import logging
import os
import threading
import time

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, TextIO
from config import Options

logger = logging.getLogger(__name__)

CacheTree = Dict[Path, Dict[str, Any]]
FilesMap = Dict[Path, TextIO]


def discover_files(
        patterns: list[str]
    ) -> list[Path]:
    """
    Finds all files matching the given glob pattern.

    Args:
        pattern (str): A glob pattern (e.g., 'service_*/*.log').

    Returns:
        A list of full paths to the matched files.
    """
    discovered: list[Path] = []
    for pattern in patterns:
        matched = glob.glob(pattern, recursive=True)
        for file in matched:
            p = Path(file).resolve()
            if "-agg" not in p.stem:
                discovered.append(p)
    return discovered


def dump_log_to_file(source_file: Path, timestamp: str, message: str):
    destination = source_file.parent / f"{source_file.stem}-agg.log"
    try:
        with destination.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] " + message + "\n")
    except Exception as e:
        logger.error(f"Failed to append to file {destination} ({source_file}): {e}")


def tail_file(
        file_path: Path, 
        cache_map: CacheTree, 
        cache_map_lock: threading.Lock,
        opts: Options, 
        stop_event: threading.Event
    ):
    """
    Tails a single file for new log entries and processes them.
    This function is executed in its own thread for each monitored file.
    """
    from parser import parse_log_entry, process_log

    logger = logging.getLogger(__name__)
    logger.debug(f"Worker started for: {file_path}")
    
    try:
        with open(file_path, 'r') as file_obj:
            file_obj.seek(0, os.SEEK_END)
            
            while not stop_event.is_set():
                line = file_obj.readline()
                if line:
                    timestamp, message = parse_log_entry(line)
                    if message:
                        with cache_map_lock:
                            cache = cache_map.setdefault(file_path, {})

                        if message in cache:
                            process_log(
                                cache=cache,
                                message=message,
                                agg_window=opts.agg_interval,
                                source_file=file_path,
                            )
                        else:
                            dump_log_to_file(
                                source_file=file_path,
                                timestamp=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                message=message,
                            )
                            cache[message] = {
                                "count": 1,
                                "first_seen": datetime.now(),
                            }
                            logger.debug(f"New entry for {file_path}: '{message}'")
                else:
                    time.sleep(opts.time_wait)

    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}. Thread will exit.")
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
    finally:
        logger.debug(f"Stopping tail for file: {file_path}")