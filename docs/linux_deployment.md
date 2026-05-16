# Linux Deployment Guide

## Assumptions

- Ubuntu or WSL
- Python 3.10+
- .NET 8 SDK
- SQLite available
- Local prototype deployment

## Install dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sqlite3 curl
```

Install .NET SDK using Microsoft instructions for your Linux distribution.

## Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run services

Terminal 1:

```bash
bash scripts/run_api.sh
```

Terminal 2:

```bash
cd acquisition-csharp/SensorCollector
dotnet run
```

Terminal 3:

```bash
python backend-python/src/data/preprocessing.py
python backend-python/src/models/train_all.py
```

Terminal 4:

```bash
bash scripts/run_dashboard.sh
```

## Production notes

For a real deployment, replace SQLite with a production database or historian, add authentication, configure TLS, set up process supervisors, and add logging/monitoring.
