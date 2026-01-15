# GCP Log Transformer

**GCP Log Transformer** is a Python utility designed to aggregate and deduplicate service logs on Google Cloud Platform (GCP) virtual machines. It monitors multiple log files, aggregates duplicate log entries, and outputs them in a format suitable for ingestion by the [GCP Ops Agent](https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent).

## Features

- **Log Aggregation**: Monitors multiple log files (using glob patterns) and aggregates duplicate log entries within a configurable time window.
- **Deduplication**: Prevents repeated log messages from flooding the output.
- **Configurable**: All behavior is controlled via a YAML config file or command-line arguments.
- **Automatic Pruning**: Old log entries are pruned from memory to save resources.
- **Flexible Logging**: Supports both console and file logging with configurable log levels.
- **Windows Service Support**: Includes scripts to install and run the transformer as a Windows service using NSSM.
- **Log Simulation**: Includes a PowerShell script to generate test logs for development and testing.

## Project Structure

```
gcp-log-transformer/
├── app-config/
│   └── config.yaml         # Main configuration file
├── app-logs/               # (Ignored) Output logs directory
├── build/                  # Build artifacts
├── scripts/
│   ├── Logsim.ps1          # Log simulation script
│   └── service.ps1         # Windows service installer
├── src/
│   ├── config.py           # Config parsing and logging setup
│   ├── files.py            # File discovery and log dumping
│   ├── main.py             # Main application entrypoint
│   ├── parser.py           # Log parsing and processing
│   └── prune.py            # Cache pruning logic
└── ...
```

## Quick Start

### 1. Install Dependencies

Install all required Python packages using `pip`. This ensures the application has all necessary libraries to run.

```sh
pip install .
```

### 2. Configure

This app can be configured through a YAML file. By default, it looks for `app-config/config.yaml` in the project root. You can specify log file patterns, aggregation intervals, logging preferences, and more.

Look at [`app-config/config.yaml`](app-config/config.yaml) for more details.

### 3. Run the Transformer

Start the log transformer by running the main Python script. You can specify a custom config file path if needed.

```sh
python src/main.py --config-file app-config/config.yaml
```

### 4. Configure app on GCP

This app can be configure on any GCP windows VM as a service by running the provided script ['service'](scripts/service.ps1). This will setup the VM by installing all the required tools and eventually setup the app in windows as a service using nssm.

```powershell
.\scripts\service.ps1
```

This will install and start the transformer as a Windows service using NSSM.

### 5. (Optional) Simulate Logs

For development and testing, use the included PowerShell script to generate sample log files. This helps verify that log aggregation and streaming work as expected.

```powershell
.\scripts\Logsim.ps1
```

## How It Works

- Watches all files matching the configured patterns.
- Aggregates duplicate log entries within a time window (`agg-interval`).
- Writes aggregated logs to new files (e.g., `service-agg.log`) in the same directory.
- Prunes old entries from memory after `prune-interval` seconds.
- Designed to work seamlessly with the GCP Ops Agent for log streaming.

## Integration with GCP Ops Agent

Point the Ops Agent to the aggregated log files (e.g., `*-agg.log`) for efficient log streaming and reduced noise from duplicate entries.

---

**Note:** For more details, see the code in [`src/`](src/) and the configuration in [`app-config/config.yaml`](app-config/config.yaml).