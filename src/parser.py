import logging

from datetime import datetime, timedelta
from pathlib import Path
from dateutil.parser import parse as parse_datetime

logger = logging.getLogger(__name__)


def parse_log_entry(entry: str):
    """
    Parses a log entry to separate and convert the timestamp from the message.
    It assumes the format is '[timestamp] message'.

    Args:
        entry (str): The raw log line.

    Returns:
        A tuple containing (datetime_object, message) or (None, original_entry).
    """
    entry = entry.strip()
    if not entry:
        return (None, None)

    if entry.startswith("[") and "]" in entry:
        end_bracket_index = entry.find("]")
        timestamp_str = entry[1:end_bracket_index]
        message = entry[end_bracket_index + 1 :].strip()

        try:
            timestamp = parse_datetime(timestamp_str)
            return (timestamp, message)
        except ValueError:
            logger.error(f"Could not parse timestamp: {timestamp_str}")
            return (timestamp_str, message)

    return (datetime.now(), entry)


def process_log(cache: dict, source_file: Path, message: str, agg_window: timedelta):
    """
    Checks the cache for logs older than the time window, reports duplicates,
    and removes them from the cache.
    """
    from files import dump_log_to_file

    current_time = datetime.now()
    log_data = cache.get(message)
    if log_data and current_time - log_data["first_seen"] >= agg_window:
        if log_data["count"] >= 1:
            modified = f"{message} (occured {log_data['count']} times)"
            dump_log_to_file(
                source_file,
                timestamp=current_time.strftime("%Y-%m-%d %H:%M:%S"),
                message=modified,
            )
            logger.debug(f"Dumped '{modified}'")
        del cache[message]
    else:
        cache[message]["count"] += 1
