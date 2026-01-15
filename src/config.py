import argparse
import logging
import json
import yaml
import os

from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import timedelta

DEFAULT_CONFIGS = {
    "source-files": ["examples/service_*/*.log"],
    "agg-interval": 20,
    "log-level": "INFO",
    "prune-interval": 5.0,
    "time-wait": 0.5,
    "console-log": True,
    "output-log": False,
    "output-path": "./app-logs/gcp-transformer.log",
}


class Options:
    source_files: list[str]
    agg_interval: timedelta
    log_level: str
    prune_interval: float
    time_wait: float
    console_log: bool = True
    output_log: bool = False
    output_path: Path = Path("./app-logs/gcp-transformer.log")

    def __init__(
        self,
        files: list[str],
        agg_interval: timedelta,
        log_level: str,
        prune_interval: float,
        time_wait: float,
        console_log: bool,
        output_log: bool,
        output_path: Path,
    ):
        self.source_files = files
        self.agg_interval = agg_interval
        self.prune_interval = prune_interval
        self.time_wait = time_wait
        self.log_level = log_level
        self.console_log = console_log
        self.output_log = output_log
        self.output_path = output_path

        self.configure_logging(log_level)

    def configure_logging(self, log_level: str):
        lvl = getattr(logging, log_level.upper(), logging.INFO)
        formater = logging.Formatter(
            "[%(asctime)s - %(levelname)s - %(filename)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        root = logging.getLogger()

        for handler in root.handlers[:]:
            root.removeHandler(handler)

        root.setLevel(lvl)

        if self.console_log:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(lvl)
            stream_handler.setFormatter(formater)
            root.addHandler(stream_handler)

        if self.output_log:
            output_path = self.output_path.expanduser()
            if not output_path.parent.exists():
                try:
                    os.makedirs(output_path.parent, exist_ok=True)
                except Exception:
                    logging.getLogger().error(
                        "Unable to create log directory %s; file logging disabled",
                        output_path.parent,
                    )
                    return
            try:
                output_path.open("w", encoding="utf-8")
                output_file = RotatingFileHandler(
                    filename=str(output_path),
                    mode="a",
                    maxBytes=10 * 1024 * 1024,
                    backupCount=5,
                    encoding="utf-8",
                )
                output_file.setLevel(lvl)
                output_file.setFormatter(formater)
                root.addHandler(output_file)
                logging.getLogger().info(
                    "Logger configured to write to file: %s", output_path.resolve()
                )
            except Exception as e:
                logging.getLogger().warning(
                    f"Failed to create file handler for {output_path}: %s", e
                )

    def __repr__(self):
        return json.dumps(self.to_dict(), indent=4)

    def __str__(self):
        return self.__repr__()

    def to_dict(self):
        return {
            "source_files": self.source_files,
            "aggregation_interval": self.agg_interval.seconds.__str__() + "s",
            "prune_interval": self.prune_interval.__str__() + "s",
            "log_level": logging.getLevelName(logging.getLogger().level),
            "console_logging": self.console_log,
            "file_logging": self.output_log,
            "log_file_path": str(self.output_path.resolve()),
        }


def load_yaml_config(file_path: str | Path):
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")
    with path.open("r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    if not isinstance(config_data, dict):
        raise ValueError(f"Invalid config format in file: {file_path}")
    return config_data


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Process source files with specified interval and logging level."
    )
    parser.add_argument(
        "--config-file",
        "-c",
        default="./app-config/config.yaml",
        help="Path to config file, if provided, it overrides the provided default options.",
    )

    parser.add_argument(
        "--source-files",
        "-s",
        nargs="+",
        default=DEFAULT_CONFIGS["source-files"],
        help="Paths to source files.",
    )

    parser.add_argument(
        "--agg-interval",
        "-i",
        type=float,
        default=DEFAULT_CONFIGS["agg-interval"],
        help="Time interval in seconds.",
    )

    parser.add_argument(
        "--log-level",
        "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=DEFAULT_CONFIGS["log-level"],
        help="Logging level.",
    )

    parser.add_argument(
        "--prune-interval",
        "-p",
        type=float,
        default=DEFAULT_CONFIGS["prune-interval"],
        help="Cache prune interval in seconds.",
    )

    parser.add_argument(
        "--time-wait",
        "-w",
        type=float,
        default=DEFAULT_CONFIGS["time-wait"],
        help="Amount of app has to wait before each iteration.",
    )

    parser.add_argument(
        "--console-log",
        type=bool,
        default=DEFAULT_CONFIGS["console-log"],
        help="Whether to enable console logging.",
    )

    parser.add_argument(
        "--output-log",
        type=bool,
        default=DEFAULT_CONFIGS["output-log"],
        help="Whether to enable output logging to a file.",
    )

    parser.add_argument(
        "--output-path",
        type=str,
        default=DEFAULT_CONFIGS["output-path"],
        help="Path to store the application log file.",
    )

    return parser.parse_args()


def parse_options():
    args = parse_arguments()
    if args.config_file:
        try:
            config_data = load_yaml_config(args.config_file)
            merged_configs = {**DEFAULT_CONFIGS, **config_data}
            return Options(
                files=merged_configs["source-files"],
                agg_interval=timedelta(seconds=merged_configs["agg-interval"]),
                log_level=merged_configs["log-level"],
                prune_interval=merged_configs["prune-interval"],
                time_wait=merged_configs["time-wait"],
                console_log=merged_configs["console-log"],
                output_log=merged_configs["output-log"],
                output_path=Path(merged_configs["output-path"]),
            )
        except Exception as _:
            pass

    return Options(
        files=args.source_files,
        agg_interval=timedelta(seconds=args.agg_interval),
        log_level=args.log_level,
        prune_interval=args.prune_interval,
        time_wait=args.time_wait,
        console_log=args.console_log,
        output_log=args.output_log,
        output_path=Path(args.output_path),
    )
