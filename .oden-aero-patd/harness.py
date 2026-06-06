from __future__ import annotations

import argparse
import configparser
import json
import re
import shutil
import subprocess
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
SCREEN_RES_PREFS = REPO_ROOT / "Output" / "preferences" / "X-Plane Screen Res.prf"
ANALYTICS_PREFS = REPO_ROOT / "Output" / "preferences" / "X-Plane Analytics.prf"
MISC_PREFS = REPO_ROOT / "Output" / "preferences" / "Miscellaneous.prf"
SERVER_LIST_PREFS = REPO_ROOT / "Output" / "preferences" / "server_list_12.txt"
DEVICE_MAPPING = REPO_ROOT / "Resources" / "plugins" / "RealSimGear" / "DeviceMapping.ini"
COMMAND_MAPPING = REPO_ROOT / "Resources" / "plugins" / "RealSimGear" / "CommandMapping.ini"
MAIN_LOG = REPO_ROOT / "Log.txt"
ATC_LOG = REPO_ROOT / "Log_ATC.txt"
MONITOR_RESET_PREFS = [WINDOW_POSITIONS, SCREEN_RES_PREFS]


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def parse_resolution(value: str) -> tuple[int, int]:
    width_text, height_text = value.split("x", maxsplit=1)
    return int(width_text), int(height_text)


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def current_xplane_version_from_log() -> tuple[str, str] | None:
    first_line = read_text(MAIN_LOG).splitlines()
    if not first_line:
        return None
    match = re.search(r"Log\.txt for (X-Plane\s+[^\(]+) \(build\s+(\d+)", first_line[0])
    if not match:
        return None
    return match.group(1).strip(), match.group(2)


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
    monitor_pattern = re.compile(
        r"^monitor/(\d+)/(m_usage|m_monitor|m_avionics_device|m_x_res_full|m_y_res_full|proj/off_lat_deg|proj/off_vrt_deg|m_window_bounds/[0-3])\s+(.+)$"
    )
    monitors: dict[str, dict[str, str]] = {}
    for line in read_text(path).splitlines():
        match = monitor_pattern.match(line.strip())
        if not match:
            continue
        monitor_id, key, value = match.groups()
        monitors.setdefault(monitor_id, {})[key] = value
        monitors[monitor_id]["monitor_id"] = monitor_id

    for monitor in monitors.values():
        bounds = []
        for index in range(4):
            value = monitor.get(f"m_window_bounds/{index}")
            if value is None:
                bounds = []
                break
            bounds.append(int(float(value)))
        if bounds:
            monitor["window_bounds"] = bounds
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


def resolve_loaded_situation_path() -> Path | None:
    misc_text = read_text(MISC_PREFS)
    default_match = re.search(r"^default_situation\s+(.+)\s*$", misc_text, flags=re.MULTILINE)
    if default_match:
        candidate = REPO_ROOT / default_match.group(1).strip()
        if candidate.exists() and candidate.suffix.lower() == ".sit":
            return candidate

    log_text = read_text(MAIN_LOG)
    log_matches = re.findall(r"Output/situations/[^\r\n]+?\.sit", log_text)
    if log_matches:
        candidate = REPO_ROOT / log_matches[-1]
        if candidate.exists():
            return candidate
    return None


def scan_log_signals(log_text: str, spec: dict) -> dict:
    matches: dict[str, list[str]] = {}
    for pattern in spec["log_patterns"]["errors"]:
        matched_lines = [line for line in log_text.splitlines() if pattern in line]
        if matched_lines:
            matches[pattern] = matched_lines[-5:]
    crash_detected = "This application has crashed!" in log_text
    return {"crash_detected": crash_detected, "pattern_matches": matches}


def add_result(findings: list[dict], status: str, check: str, message: str) -> None:
    findings.append({"status": status, "check": check, "message": message})


def validate_state(spec: dict, window_state: dict, devices: list[dict], log_state: dict) -> list[dict]:
    findings: list[dict] = []
    monitors = list(window_state["monitors"].values())
    normal_visuals = [item for item in monitors if item.get("m_usage") == spec["xplane"]["normal_visual_usage"]]
    avionics = [item for item in monitors if item.get("m_usage") == spec["xplane"]["avionics_usage"]]
    if window_state["count"] != spec["xplane"]["expected_monitor_count"]:
        add_result(
            findings,
            "fail",
            "xplane_monitor_count",
            f"Expected {spec['xplane']['expected_monitor_count']} X-Plane monitor slots, found {window_state['count']}.",
        )
    else:
        add_result(findings, "pass", "xplane_monitor_count", "Expected X-Plane monitor slot count detected.")

    if len(normal_visuals) != spec["outside_view_monitors"]:
        add_result(
            findings,
            "fail",
            "outside_view_count",
            f"Expected {spec['outside_view_monitors']} outside-view monitors, found {len(normal_visuals)}.",
        )
    else:
        add_result(findings, "pass", "outside_view_count", f"Found {len(normal_visuals)} outside-view monitors.")

    current_outside_views = sorted(
        normal_visuals,
        key=lambda item: float(item.get("proj/off_lat_deg", "0")),
    )
    for index, expected in enumerate(spec["xplane"]["expected_outside_views"]):
        if index >= len(current_outside_views):
            break
        current = current_outside_views[index]
        off_lat = float(current.get("proj/off_lat_deg", "0"))
        off_vrt = float(current.get("proj/off_vrt_deg", "0"))
        resolution = f"{current.get('m_x_res_full', '0')}x{current.get('m_y_res_full', '0')}"
        lat_ok = abs(off_lat - expected["off_lat_deg"]) < 0.25
        vrt_ok = abs(off_vrt - expected["off_vrt_deg"]) < 0.25
        if lat_ok and vrt_ok:
            add_result(
                findings,
                "pass",
                f"outside_view_geometry_{index}",
                f"Outside-view slot {index} geometry matches expected offsets ({off_lat}, {off_vrt}).",
            )
        else:
            add_result(
                findings,
                "fail",
                f"outside_view_geometry_{index}",
                f"Outside-view slot {index} offsets are ({off_lat}, {off_vrt}) but expected ({expected['off_lat_deg']}, {expected['off_vrt_deg']}).",
            )

        min_resolution = expected.get("min_resolution")
        if min_resolution is not None:
            current_width, current_height = parse_resolution(resolution)
            minimum_width, minimum_height = parse_resolution(min_resolution)
            if current_width < minimum_width or current_height < minimum_height:
                add_result(
                    findings,
                    "fail",
                    f"outside_view_resolution_{index}",
                    f"Outside-view slot {index} has persisted full resolution {resolution}, below expected minimum {min_resolution}.",
                )
            else:
                add_result(
                    findings,
                    "pass",
                    f"outside_view_resolution_{index}",
                    f"Outside-view slot {index} full resolution {resolution} satisfies expected minimum {min_resolution}.",
                )

    avionics_devices = {item.get("m_avionics_device") for item in avionics}
    missing_devices = [
        device for device in spec["xplane"]["required_avionics_devices"] if device not in avionics_devices
    ]
    if missing_devices:
        add_result(
            findings,
            "fail",
            "required_avionics_devices",
            f"Missing required avionics device assignments: {', '.join(missing_devices)}.",
        )
    else:
        add_result(findings, "pass", "required_avionics_devices", "Required X-Plane avionics assignments are present.")

    model_counts = Counter(device.get("Model") for device in devices)
    if model_counts.get("RealSimGear-G1000XFD", 0) != spec["realsimgear"]["g1000_xfd_count"]:
        add_result(
            findings,
            "fail",
            "g1000_count",
            (
                f"Expected {spec['realsimgear']['g1000_xfd_count']} RealSimGear-G1000XFD devices, "
                f"found {model_counts.get('RealSimGear-G1000XFD', 0)}."
            ),
        )
    else:
        add_result(findings, "pass", "g1000_count", "Expected RealSimGear G1000 device count detected.")

    g5_devices = [device for device in devices if device.get("Model") == "RealSimGear-G5"]
    if len(g5_devices) != spec["realsimgear"]["g5_count"]:
        add_result(
            findings,
            "fail",
            "g5_count",
            f"Expected {spec['realsimgear']['g5_count']} G5 devices, found {len(g5_devices)}.",
        )
    else:
        add_result(findings, "pass", "g5_count", "Expected RealSimGear G5 count detected.")

    ports = [device.get("Port") for device in g5_devices if device.get("Port")]
    duplicate_ports = [port for port, count in Counter(ports).items() if count > 1]
    if duplicate_ports and not spec["realsimgear"]["allow_duplicate_g5_ports"]:
        add_result(findings, "fail", "g5_duplicate_ports", f"Duplicate G5 ports detected: {', '.join(duplicate_ports)}.")
    else:
        add_result(findings, "pass", "g5_duplicate_ports", "No unexpected duplicate G5 ports detected.")

    if log_state["crash_detected"]:
        add_result(findings, "fail", "crash_detected", "Crash marker found in X-Plane log.")
    else:
        add_result(findings, "pass", "crash_detected", "No crash marker found in X-Plane log.")

    return findings


def validate_windows_inventory(spec: dict, displays: list[dict]) -> list[dict]:
    findings: list[dict] = []
    actual_resolutions = sorted(f"{display['Width']}x{display['Height']}" for display in displays)
    expected_resolutions = sorted(spec["windows"]["expected_display_resolutions"])
    if actual_resolutions == expected_resolutions:
        add_result(findings, "pass", "windows_display_inventory", "Windows display resolution inventory matches the PATD spec.")
    else:
        add_result(
            findings,
            "fail",
            "windows_display_inventory",
            f"Windows display inventory mismatch. Expected {expected_resolutions}, found {actual_resolutions}.",
        )
    return findings


def draft_safe_window_config(spec: dict, window_state: dict, displays: list[dict]) -> dict:
    normal_visuals = sorted(
        [item for item in window_state["monitors"].values() if item.get("m_usage") == spec["xplane"]["normal_visual_usage"]],
        key=lambda item: float(item.get("proj/off_lat_deg", "0")),
    )
    large_displays = sorted(
        [display for display in displays if display["Width"] >= 3840 and display["Height"] >= 2160],
        key=lambda display: display["X"],
    )
    proposed = {
        "strategy": "Draft only. Review before applying to Output/preferences/X-Plane Window Positions.prf.",
        "outside_views": [],
        "notes": [
            "Use the left-to-right 3840x2160 displays as left/center/right outside views.",
            "Reset the persisted center outside-view full resolution if it remains below 3840x2160.",
            "Do not overwrite live X-Plane preferences automatically until G5 duplicate target issues are understood.",
        ],
    }
    for index, expected in enumerate(spec["xplane"]["expected_outside_views"]):
        current = normal_visuals[index] if index < len(normal_visuals) else {}
        proposed_display = large_displays[index] if index < len(large_displays) else None
        proposed["outside_views"].append(
            {
                "slot": index,
                "current_monitor_index": current.get("m_monitor"),
                "current_full_resolution": f"{current.get('m_x_res_full', '?')}x{current.get('m_y_res_full', '?')}",
                "expected_off_lat_deg": expected["off_lat_deg"],
                "expected_off_vrt_deg": expected["off_vrt_deg"],
                "suggested_windows_display": proposed_display["DeviceName"] if proposed_display else None,
                "suggested_full_resolution": f"{proposed_display['Width']}x{proposed_display['Height']}" if proposed_display else None,
            }
        )
    return proposed


def replace_monitor_setting(text: str, monitor_id: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^(monitor/{re.escape(monitor_id)}/{re.escape(key)})\s+.+$", re.MULTILINE)
    replacement = rf"\1 {value}"
    updated_text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError(f"Could not uniquely update monitor/{monitor_id}/{key} in {WINDOW_POSITIONS}")
    return updated_text


def build_safe_resolution_updates(spec: dict, window_state: dict) -> list[dict]:
    normal_visuals = sorted(
        [item for item in window_state["monitors"].values() if item.get("m_usage") == spec["xplane"]["normal_visual_usage"]],
        key=lambda item: float(item.get("proj/off_lat_deg", "0")),
    )
    updates: list[dict] = []
    for index, expected in enumerate(spec["xplane"]["expected_outside_views"]):
        if index >= len(normal_visuals):
            break
        minimum_resolution = expected.get("min_resolution")
        if minimum_resolution is None:
            continue
        current = normal_visuals[index]
        current_width = int(current.get("m_x_res_full", "0"))
        current_height = int(current.get("m_y_res_full", "0"))
        minimum_width, minimum_height = parse_resolution(minimum_resolution)
        if current_width >= minimum_width and current_height >= minimum_height:
            continue
        target_width = minimum_width
        target_height = minimum_height
        window_bounds = current.get("window_bounds") or []
        if len(window_bounds) == 4:
            target_width = max(target_width, int(window_bounds[2]))
            target_height = max(target_height, int(window_bounds[3]))
        updates.append(
            {
                "slot": index,
                "monitor_id": current["monitor_id"],
                "from": f"{current_width}x{current_height}",
                "to": f"{target_width}x{target_height}",
                "reason": f"Outside-view slot {index} is below required minimum {minimum_resolution}.",
            }
        )
    return updates


def apply_safe_window_config(spec: dict, window_state: dict, run_dir: Path) -> dict:
    updates = build_safe_resolution_updates(spec, window_state)
    result = {
        "strategy": "Apply only minimal outside-view full-resolution repairs with a backup.",
        "backup_file": None,
        "applied": [],
        "skipped": [],
    }
    if not updates:
        result["skipped"].append("No safe resolution updates were needed.")
        return result

    backup_dir = run_dir / "artifacts"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / WINDOW_POSITIONS.name
    shutil.copy2(WINDOW_POSITIONS, backup_path)
    result["backup_file"] = str(backup_path)

    updated_text = read_text(WINDOW_POSITIONS)
    for update in updates:
        width_text, height_text = update["to"].split("x", maxsplit=1)
        updated_text = replace_monitor_setting(updated_text, update["monitor_id"], "m_x_res_full", width_text)
        updated_text = replace_monitor_setting(updated_text, update["monitor_id"], "m_y_res_full", height_text)
        result["applied"].append(update)

    WINDOW_POSITIONS.write_text(updated_text, encoding="utf-8")
    return result


def reset_monitor_config(run_dir: Path) -> dict:
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "strategy": "Back up and remove persisted monitor layout prefs so X-Plane can rebuild them from scratch.",
        "files": [],
        "notes": [
            "Launch X-Plane and let it rebuild monitor prefs from scratch.",
            "Use the manual interaction window to dismiss dialogs and position displays.",
            "Capture a new snapshot after the operator confirms the layout is correct.",
        ],
    }
    for path in MONITOR_RESET_PREFS:
        entry = {
            "path": str(path),
            "backup": None,
            "removed": False,
            "exists_before": path.exists(),
        }
        if path.exists():
            backup_path = artifacts_dir / path.name
            shutil.copy2(path, backup_path)
            entry["backup"] = str(backup_path)
            path.unlink()
            entry["removed"] = True
        result["files"].append(entry)
    return result


def sanitize_startup_prompts(run_dir: Path, output_name: str = "startup_prompt_sanitization.json") -> dict:
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "screen_res_backup": None,
        "analytics_backup": None,
        "removed_unsafe_markers": 0,
        "warn_update_before": None,
        "warn_update_after": None,
        "server_list_backup": None,
        "server_list_version_before": None,
        "server_list_version_after": None,
        "misc_backup": None,
        "default_situation_before": None,
        "default_situation_cleared": False,
    }

    if SCREEN_RES_PREFS.exists():
        screen_res_backup = artifacts_dir / SCREEN_RES_PREFS.name
        shutil.copy2(SCREEN_RES_PREFS, screen_res_backup)
        result["screen_res_backup"] = str(screen_res_backup)
        screen_res_text = read_text(SCREEN_RES_PREFS)
        unsafe_count = len(re.findall(r"^UNSAFE\s*$", screen_res_text, flags=re.MULTILINE))
        if unsafe_count:
            sanitized_text = re.sub(r"^UNSAFE\s*$\n?", "", screen_res_text, flags=re.MULTILINE)
            SCREEN_RES_PREFS.write_text(sanitized_text, encoding="utf-8")
        result["removed_unsafe_markers"] = unsafe_count

    if ANALYTICS_PREFS.exists():
        analytics_backup = artifacts_dir / ANALYTICS_PREFS.name
        shutil.copy2(ANALYTICS_PREFS, analytics_backup)
        result["analytics_backup"] = str(analytics_backup)
        analytics_text = read_text(ANALYTICS_PREFS)
        warn_match = re.search(r"^_warn_update\s+(\S+)\s*$", analytics_text, flags=re.MULTILINE)
        if warn_match:
            result["warn_update_before"] = warn_match.group(1)
            analytics_text = re.sub(r"^(_warn_update\s+)\S+\s*$", r"\g<1>0", analytics_text, flags=re.MULTILINE)
            ANALYTICS_PREFS.write_text(analytics_text, encoding="utf-8")
            result["warn_update_after"] = "0"

    if SERVER_LIST_PREFS.exists():
        server_list_backup = artifacts_dir / SERVER_LIST_PREFS.name
        shutil.copy2(SERVER_LIST_PREFS, server_list_backup)
        result["server_list_backup"] = str(server_list_backup)
        server_list_text = read_text(SERVER_LIST_PREFS)
        current_version = current_xplane_version_from_log()
        if current_version is not None:
            version_name, build_number = current_version
            final_version_match = re.search(r"^FINAL_VERSION\s+(\d+)\s*$", server_list_text, flags=re.MULTILINE)
            if final_version_match:
                result["server_list_version_before"] = final_version_match.group(1)
            replacements = {
                r"^(BETA\s+).+$": rf"\g<1>{version_name}",
                r"^(FINAL\s+).+$": rf"\g<1>{version_name}",
                r"^(FULL\s+).+$": rf"\g<1>{version_name}",
                r"^(BETA_VERSION\s+)\d+\s*$": rf"\g<1>{build_number}",
                r"^(FINAL_VERSION\s+)\d+\s*$": rf"\g<1>{build_number}",
            }
            for pattern, replacement in replacements.items():
                server_list_text = re.sub(pattern, replacement, server_list_text, flags=re.MULTILINE)

            def replace_branch(match: re.Match[str]) -> str:
                return (
                    f"BRANCH {match.group(1)}\n"
                    f"BRANCH_BUILD_NUMBER {build_number}\n"
                    f"BRANCH_NAME {version_name}\n"
                    f"BRANCH_PATH {version_name}"
                )

            server_list_text = re.sub(
                r"BRANCH (Final|Beta)\nBRANCH_BUILD_NUMBER \d+\nBRANCH_NAME .+\nBRANCH_PATH .+",
                replace_branch,
                server_list_text,
                flags=re.MULTILINE,
            )
            SERVER_LIST_PREFS.write_text(server_list_text, encoding="utf-8")
            result["server_list_version_after"] = build_number

    if MISC_PREFS.exists():
        misc_backup = artifacts_dir / MISC_PREFS.name
        shutil.copy2(MISC_PREFS, misc_backup)
        result["misc_backup"] = str(misc_backup)
        misc_text = read_text(MISC_PREFS)
        default_situation_match = re.search(r"^default_situation\s+(.+)\s*$", misc_text, flags=re.MULTILINE)
        if default_situation_match:
            result["default_situation_before"] = default_situation_match.group(1)
            misc_text = re.sub(r"^default_situation\s+.+\n?", "", misc_text, flags=re.MULTILINE)
            MISC_PREFS.write_text(misc_text, encoding="utf-8")
            result["default_situation_cleared"] = True

    write_json(run_dir / output_name, result)
    return result


def ensure_xplane_not_running() -> dict:
    command = (
        "$proc = Get-Process -Name 'X-Plane' -ErrorAction SilentlyContinue; "
        "if ($proc) { "
        "  $ids = @($proc | ForEach-Object { $_.Id }); "
        "  $proc | Stop-Process -Force; "
        "  Start-Sleep -Milliseconds 500; "
        "  $remaining = Get-Process -Name 'X-Plane' -ErrorAction SilentlyContinue; "
        "  [pscustomobject]@{ found = $true; killed_ids = $ids; still_running = [bool]$remaining } | ConvertTo-Json -Compress "
        "} else { "
        "  [pscustomobject]@{ found = $false; killed_ids = @(); still_running = $false } | ConvertTo-Json -Compress "
        "}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {"found": False, "killed_ids": [], "still_running": False, "error": result.stderr.strip()}
    return json.loads(result.stdout)


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
    findings = []
    findings.extend(validate_windows_inventory(spec, displays))
    findings.extend(validate_state(spec, window_state, devices, log_state))

    artifacts_dir = run_dir / "artifacts"
    copy_if_exists(WINDOW_POSITIONS, artifacts_dir / WINDOW_POSITIONS.name)
    copy_if_exists(DEVICE_MAPPING, artifacts_dir / DEVICE_MAPPING.name)
    copy_if_exists(COMMAND_MAPPING, artifacts_dir / COMMAND_MAPPING.name)
    copy_if_exists(MAIN_LOG, artifacts_dir / MAIN_LOG.name)
    copy_if_exists(ATC_LOG, artifacts_dir / ATC_LOG.name)
    loaded_situation = resolve_loaded_situation_path()
    loaded_situation_artifact = None
    if loaded_situation is not None:
        loaded_situation_artifact = artifacts_dir / loaded_situation.name
        copy_if_exists(loaded_situation, loaded_situation_artifact)

    state = {
        "timestamp": utc_stamp(),
        "windows_displays": displays,
        "window_positions": window_state,
        "device_mapping": devices,
        "log_state": log_state,
        "findings": findings,
        "loaded_situation": str(loaded_situation) if loaded_situation is not None else None,
        "loaded_situation_artifact": str(loaded_situation_artifact) if loaded_situation_artifact is not None else None,
    }
    write_json(run_dir / "snapshot.json", state)
    return state


def command_draft_safe_config(_: argparse.Namespace) -> int:
    run_dir = RUNS_DIR / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    spec = load_spec()
    window_state = parse_window_positions(WINDOW_POSITIONS)
    displays = collect_windows_displays()
    draft = draft_safe_window_config(spec, window_state, displays)
    write_json(run_dir / "safe_config_draft.json", draft)
    print(f"Safe config draft complete: {run_dir / 'safe_config_draft.json'}")
    return 0


def command_apply_safe_config(_: argparse.Namespace) -> int:
    run_dir = RUNS_DIR / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    spec = load_spec()
    window_state = parse_window_positions(WINDOW_POSITIONS)
    result = apply_safe_window_config(spec, window_state, run_dir)
    write_json(run_dir / "safe_config_apply.json", result)
    print(f"Safe config apply complete: {run_dir / 'safe_config_apply.json'}")
    return 0


def command_reset_monitor_config(_: argparse.Namespace) -> int:
    run_dir = RUNS_DIR / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    cleanup = ensure_xplane_not_running()
    result = reset_monitor_config(run_dir)
    result["xplane_process_cleanup"] = cleanup
    write_json(run_dir / "monitor_reset.json", result)
    print(f"Monitor reset complete: {run_dir / 'monitor_reset.json'}")
    return 0


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
                f"- manual_wait_seconds: {launch_result['manual_wait_seconds']}",
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


def launch_xplane(executable: Path, duration: int, leave_running: bool, manual_wait_seconds: int) -> dict:
    if not executable.exists():
        raise FileNotFoundError(f"X-Plane executable not found: {executable}")

    process = subprocess.Popen([str(executable)], cwd=REPO_ROOT)
    start = time.time()
    exit_code: int | None = None
    terminated_by_harness = False
    if manual_wait_seconds > 0:
        time.sleep(manual_wait_seconds)
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
        "manual_wait_seconds": manual_wait_seconds,
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
    state: dict = {"timestamp": utc_stamp()}
    state["xplane_process_cleanup"] = ensure_xplane_not_running()
    startup_prompt_result = sanitize_startup_prompts(run_dir)
    state["startup_prompt_sanitization"] = startup_prompt_result
    launch_result: dict | None = None
    try:
        launch_result = launch_xplane(Path(args.xplane_exe), args.duration, args.leave_running, args.manual_wait)
        state.update(snapshot(run_dir))
    except Exception as exc:
        state["run_error"] = repr(exc)
    finally:
        if not args.leave_running:
            state["post_run_prompt_cleanup"] = sanitize_startup_prompts(
                run_dir,
                output_name="post_run_prompt_cleanup.json",
            )
        write_json(run_dir / "snapshot.json", state)
        if launch_result is not None and "findings" in state and "log_state" in state and "windows_displays" in state:
            write_report(run_dir, state, launch_result=launch_result)
    print(f"Run complete: {run_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PATD X-Plane configuration harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot", help="Capture the current PATD configuration state")
    snapshot_parser.set_defaults(func=command_snapshot)

    draft_parser = subparsers.add_parser(
        "draft-safe-config",
        help="Generate a safe monitor-reset draft without overwriting the live X-Plane preference file",
    )
    draft_parser.set_defaults(func=command_draft_safe_config)

    apply_parser = subparsers.add_parser(
        "apply-safe-config",
        help="Back up and apply the minimal safe outside-view resolution fixes to the live X-Plane preference file",
    )
    apply_parser.set_defaults(func=command_apply_safe_config)

    reset_parser = subparsers.add_parser(
        "reset-monitor-config",
        help="Back up and remove persisted X-Plane monitor layout prefs so displays can be repositioned from scratch",
    )
    reset_parser.set_defaults(func=command_reset_monitor_config)

    run_parser = subparsers.add_parser("run", help="Launch X-Plane, capture artifacts, and validate the configuration")
    run_parser.add_argument("--xplane-exe", default=str(DEFAULT_XPLANE_EXE), help="Path to X-Plane.exe")
    run_parser.add_argument("--duration", type=int, default=45, help="Seconds to wait after the manual interaction window before capturing the snapshot")
    run_parser.add_argument("--manual-wait", type=int, default=30, help="Seconds to leave X-Plane alone at startup so the operator can dismiss dialogs and position windows")
    run_parser.add_argument("--leave-running", action="store_true", help="Do not terminate X-Plane after the wait period")
    run_parser.set_defaults(func=command_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())