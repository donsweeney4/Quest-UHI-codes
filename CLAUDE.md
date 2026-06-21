# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Quest-UHI-codes** project — an Urban Heat Island (UHI) monitoring system for the Livermore, CA area. It collects temperature/humidity data from a network of stationary IoT sensors and weather stations, stores it in a MySQL database, and serves it through two Quart web applications.

## Running Scripts

All pipeline scripts are standalone Python 3 scripts run directly:

```bash
python3 ProcessIncomingMailAttachments_1.py   # or: python3 f1.py
python3 UnZipToCSV_2.py                        # or: python3 f2.py
python3 ProcessCSVtoSQL_3.py                   # or: python3 f3.py
python3 LLNL_data_to_SQL.py
python3 ReadExcelToSQL.py
python3 ExtractLatestDistinctRows.py
python3 AddWetBulbTemperature.py
```

Check recent log output (last 10 lines of each pipeline log):
```bash
bash logs.sh
```

Web servers (managed as systemd services, run via hypercorn):
```bash
# Stationary sensor dashboard — port 5001
cd /home/ubuntu/AWS-server-for-stationary-sensors
hypercorn app:app --config hypercorn_config.toml

# Mobile sensor dashboard — port 5002
cd /home/ubuntu/AWS-server-for-mobile-sensors
hypercorn app:app --config hypercorn_config.toml
```

View mobile server logs (logs only to systemd journal):
```bash
journalctl -u myapp-mobilesensors.service --no-pager -f
```

## Architecture

### Data Ingestion Pipeline (this repo, `/home/uhi/`)

Three scripts run sequentially (each feeds the next), triggered by cron every 5 minutes:

1. **ProcessIncomingMailAttachments_1.py** (`f1.py`) — Scans `/home/uhi/Maildir` for emails with ZIP attachments. Renames each attachment with a UUID prefix to avoid collisions, moves it to `/home/uhi/email_attachments/`, then deletes the email from Maildir.

2. **UnZipToCSV_2.py** (`f2.py`) — Extracts ZIP files from `email_attachments/`, processes contained CSVs (converts columns to float), saves cleaned CSVs to `SensorData/` (filename = sensor ID, e.g. `Sensor6.csv`), deletes the ZIP.

3. **ProcessCSVtoSQL_3.py** (`f3.py`) — Reads CSVs from `SensorData/`, inserts rows into the MySQL `sensor_data` table using `ON DUPLICATE KEY UPDATE` (keyed on sensorid + timestamp), then moves processed files to `archived_data/` with a Unix timestamp suffix.

Additional ingest scripts:
- **LLNL_data_to_SQL.py** — Fetches TSV data from the LLNL weather station HTTP API for 4 sensors at different heights (2m/10m/23m/52m), inserts into `LLNL_data`. Filters out readings below −10°C.
- **ReadExcelToSQL.py** — Downloads a sensor registry spreadsheet from Google Drive (service account: `/home/ubuntu/macro-scion-430418-m6-8786a0c80083.json`, file ID `1W7TP01gA4eWDeukHTwc8lMq4dYt5qTfg`) and upserts rows into `meta_data`.
- **ExtractLatestDistinctRows.py** — Rebuilds `latest_sensor_meta_data` table by finding the most recent `meta_data` row per `sensor_id`.
- **AddWetBulbTemperature.py** — Backfills `wetbulbtemperature` in `sensor_data` using the Stull formula for rows where it is NULL and timestamp > 2024-07-01.

The symlinks `f1.py`, `f2.py`, `f3.py` point to the three cron pipeline scripts.

### Web Servers (`/home/ubuntu/`)

Both are async **Quart** apps using `mysql.connector` for synchronous DB calls dispatched via `ThreadPoolExecutor`.

**AWS-server-for-stationary-sensors/** — Serves the main temperature dashboard with Plotly charts and a Folium map. Routes: `index` (chart rendering, fetches from `sensor_data`, `LLNL_data`, `davis_data`, `airport_data`) and `map_data` (sensor locations from `latest_sensor_meta_data`). Logs to `/home/ubuntu/StationaryNetworkServer/logs/quart_app.log`.

**AWS-server-for-mobile-sensors/** — Manages mobile measurement campaigns. Routes: `main`, `campaigns`, `files`, `processing`. Reads campaign location data from the S3 bucket `uhi-locations` (region `us-west-2`). Campaign results land in `mobile_metadata` and per-campaign tables (`mobile_uhi-<city>_metadata`). New campaigns are detected by the cron job `find_new_campaign_ids.py` (runs every minute). Logs only to systemd journal (no log file).

### MySQL Database (`uhi` on localhost)

Credentials: `host=localhost`, `database=uhi`, `user=uhi`, `password=uhi` (also set via env vars `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).

Key tables:
| Table | Primary Key | Purpose |
|---|---|---|
| `sensor_data` | `(sensorid, timestamp)` | Stationary sensor readings: temperature, humidity, pressure, wetbulbtemperature |
| `meta_data` | `(timestamp, sensor_id)` | Sensor registry with lat/lon, owner, install date |
| `latest_sensor_meta_data` | — | Materialized snapshot: newest meta_data row per sensor |
| `LLNL_data` | `(sensorid, timestamp)` | LLNL weather tower readings (4 heights) |
| `davis_data` | — | Davis/Quest weather station data |
| `airport_data` | — | Airport weather station data |
| `mobile_metadata` | — | Mobile campaign index |
| `mobile_uhi-*_metadata` | — | Per-campaign mobile readings |

### Logging

Each pipeline script writes its own log file in `/home/uhi/` (e.g. `ProcessCSVtoSQL_3.log`). `logs.sh` tails all three. The stationary web server logs to a file; the mobile server logs only to journald.
