from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


PATD_DIR = Path(__file__).resolve().parent
REPO_ROOT = PATD_DIR.parent
SPEC_PATH = PATD_DIR / "specs" / "patd_display_spec.json"
RUNS_DIR = PATD_DIR / "runs"
DEFAULT_XPLANE_EXE = REPO_ROOT / "X-Plane.exe"
WINDOW_POSITIONS = REPO_ROOT / "Output" / "preferences" / "X-Plane Window Positions.prf"
DEVICE_MAPPING = REPO_ROOT / "Resources" / "plugins" / "RealSimGear" / "DeviceMapping.ini"
COMMAND_MAPPING = REPO_ROOT / "Resources" / "plugins" / "RealSimGear" / "CommandMapping.ini"
MAIN_LOG = REPO_ROOT / "Log.txt"
ATC_LOG = REPO_ROOT / "Log_ATC.txt"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def collect_windows_displays() -> list[dict]:
    command = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "[System.Windows.Forms.Screen]::AllScreens | "
        "Select-Object DeviceName,Primary,"
        "@{N='X';E={$_.Bounds.X}},@{N='Y';E={$_.Bounds.Y}},"
        "@{N='Width';E={$_.Bounds.Width}},@{N='Height';E={$_.Bounds.Height}} | "
        "ConvertTo-Json -Depth 3"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    data = json.loads(result.stdout)
    if isinstance(data, dict):
        return [data]
    return data


def parse_window_positions(path: Path) -> dict:
    monitor_pattern = re.compile(r"^monitor/(\d+)/(m_usage|m_monitor|m_avionics_device|m_x_res_full|m_y_res_full)\s+(.+)$")
    monitors: dict[str, dict[str, str]] = {}
    for line in read_text(path).splitlines():
        match = monitor_pattern.match(line.strip())
        if not match:
            continue
        monitor_id, key, value = match.groups()
        monitors.setdefault(monitor_id, {})[key] = value
    return {"monitors": monitors, "count": len(monitors)}


def parse_device_mapping(path: Path) -> list[dict]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    devices: list[dict] = []
    for section in parser.sections():
        if not section.isdigit():
            continue
        entry = dict(parser.items(section))
        entry["section"] = section
        devices.append(entry)
    return devices


def scan_log_signals(log_text: str, spec: dict) -> dict:
    matches: dict[str, list[str]] = {}
    for pattern in spec["log_patterns"]["errors"]:
        matched_lines = [line for line in log_text.splitlines() if pattern in line]
        if matched_lines:
            matches[pattern] = matched_lines[-5:]
    crash_detected = "This application has crashed!" in log_text
    return {"crash_detected": crash_detected, "pattern_matches": matches}


def validate_state(spec: dict, window_state: dict, devices: list[dict], log_state: dict) -> list[dict]:
    findings: list[dict] = []
    monitors = list(window_state["monitors"].values())
    normal_visuals = [item for item in monitors if item.get("m_usage") == spec["xplane"]["normal_visual_usage"]]
    avionics = [item for item in monitors if item.get("m_usage") == spec["xplane"]["avionics_usage"]]
    if len(normal_visuals) != spec["outside_view_monitors"]:
        findings.append({
            "status": "fail",
            "check": "outside_view_count",
            "message": f"Expected {spec['outside_view_monitors']} outside-view monitors, found {len(normal_visuals)}.",
        })
    else:
        findings.append({
            "status": "pass",
            "check": "outside_view_count",
            "message": f"Found {len(normal_visuals)} outside-view monitors.",
        })

    avionics_devices = {item.get("m_avionics_device") for item in avionics}
    missing_devices = [
        device for device in spec["xplane"]["required_avionics_devices"] if device not in avionics_devices
    ]
    if missing_devices:
        findings.append({
            "status": "fail",
            "check": "required_avionics_devices",
            "message": f"Missing required avionics device assignments: {', '.join(missing_devices)}.",
        })
    else:
        findings.append({
            "status": "pass",
            "check": "required_avionics_devices",
            "message": "Required X-Plane avionics assignments are present.",
        })

    model_counts = Counter(device.get("Model") for device in devices)
    if model_counts.get("RealSimGear-G1000XFD", 0) != spec["realsimgear"]["g1000_xfd_count"]:
        findings.append({
            "status": "fail",
            "check": "g1000_count",
            "message": (
                f"Expected {spec['realsimgear']['g1000_xfd_count']} RealSimGear-G1000XFD devices, "
                f"found {model_counts.get('RealSimGear-G1000XFD', 0)}."
            ),
        })
    else:
        findings.append({
            "status": "pass",
            "check": "g1000_count",
            "message": "Expected RealSimGear G1000 device count detected.",
        })

    g5_devices = [device for device in devices if device.get("Model") == "RealSimGear-G5"]
    if len(g5_devices) != spec["realsimgear"]["g5_count"]:
        findings.append({
            "status": "fail",
            "check": "g5_count",
            "message": f"Expected {spec['realsimgear']['g5_count']} G5 devices, found {len(g5_devices)}.",
        })
    else:
        findings.append({
            "status": "pass",
            "check": "g5_count",
            "message": "Expected RealSimGear G5 count detected.",
        })

    ports = [device.get("Port") for device in g5_devices if device.get("Port")]
    duplicate_ports = [port for port, count in Counter(ports).items() if count > 1]
    if duplicate_ports and not spec["realsimgear"]["allow_duplicate_g5_ports"]:
        findings.append({
            "status": "fail",
            "check": "g5_duplicate_ports",
            "message": f"Duplicate G5 ports detected: {', '.join(duplicate_ports)}.",
        })
    else:
        findings.append({
            "status": "pass",
            "check": "g5_duplicate_ports",
            "message": "No unexpected duplicate G5 ports detected.",
        })

    if log_state["crash_detected"]:
        findings.append({
            "status": "fail",
            "check": "crash_detected",
            "message": "Crash marker found in X-Plane log.",
        })
    else:
        findings.append({
            "status": "pass",
            "check": "crash_detected",
            "message": "No crash marker found in X-Plane log.",
        })

    return findings


def copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def snapshot(run_dir: Path) -> dict:
    spec = load_spec()
    window_state = parse_window_positions(WINDOW_POSITIONS)
    devices = parse_device_mapping(DEVICE_MAPPING)
    displays = collect_windows_displays()
    log_text = read_text(MAIN_LOG)
    atc_log_text = read_text(ATC_LOG)
    log_state = scan_log_signals(log_text, spec)
    findings = validate_state(spec, window_state, devices, log_state)

    artifacts_dir = run_dir / "artifacts"
    copy_if_exists(WINDOW_POSITIONS, artifacts_dir / WINDOW_POSITIONS.name)
    copy_if_exists(DEVICE_MAPPING, artifacts_dir / DEVICE_MAPPING.name)
    copy_if_exists(COMMAND_MAPPING, artifacts_dir / COMMAND_MAPPING.name)
    copy_if_exists(MAIN_LOG, artifacts_dir / MAIN_LOG.name)
    copy_if_exists(ATC_LOG, artifacts_dir / ATC_LOG.name)

    state = {
        "timestamp": utc_stamp(),
        "windows_displays": displays,
        "window_positions": window_state,
        "device_mapping": devices,
        "log_state": log_state,
        "findings": findings,
    }
    write_json(run_dir / "snapshot.json", state)
    return state


def write_report(run_dir: Path, state: dict, launch_result: dict | None) -> None:
    lines = [
        "# PATD Harness Report",
        "",
        f"Generated: {state['timestamp']}",
        "",
    ]
    if launch_result is not None:
        lines.extend(
            [
                "## Launch",
                "",
                f"- executable: {launch_result['executable']}",
                f"- launched: {launch_result['launched']}",
                f"- exit_code: {launch_result['exit_code']}",
                f"- runtime_seconds: {launch_result['runtime_seconds']}",
                f"- terminated_by_harness: {launch_result['terminated_by_harness']}",
                "",
            ]
        )

    lines.extend(["## Findings", ""])
    for finding in state["findings"]:
        lines.append(f"- [{finding['status']}] {finding['check']}: {finding['message']}")
    lines.append("")

    lines.extend(["## Log Patterns", ""])
    if state["log_state"]["pattern_matches"]:
        for pattern, matches in state["log_state"]["pattern_matches"].items():
            lines.append(f"- {pattern}")
            for match in matches:
                lines.append(f"  - {match}")
    else:
        lines.append("- No configured log patterns matched.")
    lines.append("")

    lines.extend(["## Windows Displays", ""])
    for display in state["windows_displays"]:
        lines.append(
            f"- {display['DeviceName']}: primary={display['Primary']} "
            f"bounds=({display['X']},{display['Y']}) {display['Width']}x{display['Height']}"
        )
    lines.append("")

    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def launch_xplane(executable: Path, duration: int, leave_running: bool) -> dict:
    if not executable.exists():
        raise FileNotFoundError(f"X-Plane executable not found: {executable}")

    process = subprocess.Popen([str(executable)], cwd=REPO_ROOT)
    start = time.time()
    exit_code: int | None = None
    terminated_by_harness = False
    try:
        exit_code = process.wait(timeout=duration)
    except subprocess.TimeoutExpired:
        if not leave_running:
            process.terminate()
            terminated_by_harness = True
            try:
                exit_code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                exit_code = process.wait(timeout=20)
    runtime_seconds = round(time.time() - start, 2)
    return {
        "executable": str(executable),
        "launched": True,
        "exit_code": exit_code,
        "runtime_seconds": runtime_seconds,
        "terminated_by_harness": terminated_by_harness,
    }


def command_snapshot(_: argparse.Namespace) -> int:
    run_dir = RUNS_DIR / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    state = snapshot(run_dir)
    write_report(run_dir, state, launch_result=None)
    print(f"Snapshot complete: {run_dir}")
    return 0


def command_run(args: argparse.Namespace) -> int:
    run_dir = RUNS_DIR / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    launch_result = launch_xplane(Path(args.xplane_exe), args.duration, args.leave_running)
    state = snapshot(run_dir)
    write_report(run_dir, state, launch_result=launch_result)
    print(f"Run complete: {run_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PATD X-Plane configuration harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot", help="Capture the current PATD configuration state")
    snapshot_parser.set_defaults(func=command_snapshot)

    run_parser = subparsers.add_parser("run", help="Launch X-Plane, capture artifacts, and validate the configuration")
    run_parser.add_argument("--xplane-exe", default=str(DEFAULT_XPLANE_EXE), help="Path to X-Plane.exe")
    run_parser.add_argument("--duration", type=int, default=45, help="Seconds to wait before capturing the snapshot")
    run_parser.add_argument("--leave-running", action="store_true", help="Do not terminate X-Plane after the wait period")
    run_parser.set_defaults(func=command_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())