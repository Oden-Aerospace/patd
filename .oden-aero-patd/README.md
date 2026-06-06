# PATD Automation Harness

This directory contains the reusable PATD specification, issue tracker, and an automation harness for validating X-Plane display and instrument configuration changes.

## Python

- Required version: Python 3.12 or newer
- Local environment path: `.oden-aero-patd/.venv`

## What the harness does

- launches X-Plane
- captures current Windows display inventory
- snapshots key X-Plane and RealSimGear configuration files
- scans logs for known crash and configuration error patterns
- validates the live configuration against a simple PATD spec
- writes per-run artifacts under `.oden-aero-patd/runs/`

## Quick start

Create the virtual environment:

```powershell
"$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .oden-aero-patd\.venv
```

Run a snapshot without launching X-Plane:

```powershell
.\.oden-aero-patd\.venv\Scripts\python.exe .\.oden-aero-patd\harness.py snapshot
```

Launch X-Plane, wait 45 seconds, capture results, and shut it down:

```powershell
.\.oden-aero-patd\.venv\Scripts\python.exe .\.oden-aero-patd\harness.py run --duration 45
```

## Current limits

- This first version does not drive the X-Plane UI.
- It validates configuration state and captures logs around launch and shutdown.
- For crash reproduction inside the Settings UI, use the harness to capture artifacts before and after a manual repro step.