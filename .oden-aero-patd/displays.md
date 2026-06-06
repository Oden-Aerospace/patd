# PATD Display and Instrument Specification

## Purpose

This document captures the current PATD display and instrument configuration as observed from Windows, X-Plane 12 preference files, and RealSimGear plugin configuration. It is the baseline specification for troubleshooting and future repeatable setup.

## Manual setup checkpoint (2026-06-06)

Operator-confirmed state during live setup session:

- All instrument displays are currently on the correct screens.
- All three exterior monitors are assigned as external visuals.
- Exterior perspective alignment is still in progress and needs further tuning for a seamless wraparound view.

Saved checkpoint artifacts:

- Snapshot directory: `.oden-aero-patd/runs/20260606T210603Z`
- Summary report: `.oden-aero-patd/runs/20260606T210603Z/report.md`
- Raw snapshot: `.oden-aero-patd/runs/20260606T210603Z/snapshot.json`

Notes from this checkpoint:

- Current geometry values in the snapshot show left/right outside-view offsets still at 0.0, which matches the operator note that perspective blending is not finished yet.
- This checkpoint should be treated as the temporary baseline for instrument placement while outside-view perspective tuning continues.

## Wrap-around tuning checkpoint (2026-06-06)

Operator-confirmed update during the same session:

- Wrap-around alignment is significantly closer than the prior checkpoint.
- Instruments remain on the correct screens.
- Exterior displays remain assigned as external visuals.

Saved checkpoint artifacts:

- Snapshot directory: `.oden-aero-patd/runs/20260606T211338Z`
- Summary report: `.oden-aero-patd/runs/20260606T211338Z/report.md`
- Raw snapshot: `.oden-aero-patd/runs/20260606T211338Z/snapshot.json`
- Captured loaded situation file artifact: `.oden-aero-patd/runs/20260606T211338Z/artifacts/Cessna Skyhawk (G1000) Situation 50.sit`

Notes from this checkpoint:

- Perspective offsets are improved but not yet final for fully seamless exterior blending.
- Treat this as the latest in-progress geometry baseline before final fine tuning.

## Active startup baseline

The currently promoted deterministic startup baseline is:

- Baseline marker: `.oden-aero-patd/baselines/current.json`
- Baseline run: `.oden-aero-patd/runs/20260606T212417Z`

Use this command to restore and launch from that baseline:

- `./.oden-aero-patd/.venv/Scripts/python.exe ./.oden-aero-patd/harness.py start-from-baseline`

## Intended physical layout

Reported target layout:

- 3 outside-view cockpit monitors: left, center, right
- 1 RealSimGear G1000 PFD display
- 1 RealSimGear G1000 MFD display
- 3 RealSimGear G5 displays
- G5 intended roles:
  - one configured as nav compass / HSI
  - one configured as backup display
  - one configured as nav compass / HSI
- G5 units are intended to be switchable using their hardware toggle buttons

## Windows display inventory

Observed from the current OS session on 2026-06-06:

| Windows display | Primary | Bounds | Resolution |
| --- | --- | --- | --- |
| DISPLAY1 | yes | X=0, Y=0 | 3840x2160 |
| DISPLAY2 | no | X=3840, Y=0 | 3840x2160 |
| DISPLAY9 | no | X=7680, Y=0 | 640x480 |
| DISPLAY7 | no | X=8320, Y=0 | 640x480 |
| DISPLAY8 | no | X=8960, Y=0 | 640x480 |
| DISPLAY5 | no | X=9600, Y=0 | 1024x768 |
| DISPLAY3 | no | X=10624, Y=0 | 1024x768 |
| DISPLAY4 | no | X=11648, Y=0 | 3840x2160 |

Interpretation:

- Windows currently exposes 8 active displays.
- Three of those are 3840x2160 and are the most likely candidates for the outside-view monitors.
- Two displays are 1024x768 and are the most likely candidates for the dedicated G1000 monitor outputs.
- Three displays are 640x480 and may correspond to auxiliary or instrument-class outputs.

## X-Plane 12 display configuration

Observed in Output/preferences/X-Plane Window Positions.prf:

- `num_monitors 5`
- X-Plane currently defines 5 monitor slots total.
- Of those 5 slots:
  - 3 are configured as `wmgr_usage_normal_visuals`
  - 2 are configured as `wmgr_usage_avionics`

### X-Plane outside-view monitors

| X-Plane slot | Monitor index | Usage | Resolution | Notes |
| --- | --- | --- | --- | --- |
| monitor/0 | 0 | normal_visuals | 2560x1440 full, 1280x720 window | lateral offset -61.0 deg, likely left outside view |
| monitor/1 | 2 | normal_visuals | 640x480 full, 3840x2160 window | lateral offset 0.0 deg, likely center outside view but currently inconsistent |
| monitor/2 | 7 | normal_visuals | 3840x2160 full, 3840x2160 window | lateral offset 61.0 deg, likely right outside view |

### X-Plane avionics monitors

| X-Plane slot | Monitor index | Usage | Avionics device | Resolution |
| --- | --- | --- | --- | --- |
| monitor/3 | 3 | avionics | G1000_MFD | 1024x768 |
| monitor/4 | 1 | avionics | G1000_PFD1 | 1024x768 |

Interpretation:

- X-Plane is currently aware of only 2 avionics monitor windows.
- Those 2 avionics windows are assigned to G1000 MFD and G1000 PFD1.
- There are no separate X-Plane monitor-window assignments for any G5 displays in this file.
- The center outside-view slot appears suspect because its full resolution is recorded as 640x480 even though the window bounds are 3840x2160.

## RealSimGear plugin configuration

Observed in Resources/plugins/RealSimGear/README.txt:

- `RealSimGear-G1000XFD` supports personas `PFD`, `MFD`, and `PFD2`
- `RealSimGear-G5` supports personas `PFD` and `HSI`
- In the RealSimGear UI, `PFD1` maps to persona `PFD`

Observed in Resources/plugins/RealSimGear/CommandMapping.ini:

- G1000 PFD mapping section exists
- G1000 PFD2 mapping section exists
- G5 PFD mapping section exists
- G5 HSI mapping section exists
- G1000 and G5 mappings include `BTN_REVERSION=sim/GPS/G1000_display_reversion`

Observed in Resources/plugins/RealSimGear/DeviceMapping.ini:

| Entry | Port | Model | Function | Notes |
| --- | --- | --- | --- | --- |
| 0 | COM12 | RealSimGear-G1000XFD | 3 | G1000 display |
| 1 | COM11 | RealSimGear-G1000XFD | 4 | G1000 display |
| 2 | COM5 | RealSimGear-G5 | 5 | G5 display |
| 3 | COM6 | RealSimGear-G5 | 3 | G5 display |
| 4 | COM6 | RealSimGear-G5 | 3 | G5 display, duplicates COM6 mapping |
| 5 | COM10 | RealSimGear-GMA-Addon | 0 | audio addon |

Additional plugin setting:

- `probe_legacy=true`

Interpretation:

- The RealSimGear plugin sees 2 G1000 displays and 3 G5 displays, which matches the intended hardware count.
- The plugin mapping file currently contains 3 G5 devices, but 2 of them are mapped to the same COM6 port.
- The RealSimGear files available in this repo do not document the numeric meaning of `Function=3`, `Function=4`, and `Function=5` in DeviceMapping.ini, so those values need to be cross-checked in the plugin UI or logs.

## Current mismatches to investigate

1. Physical setup includes 3 outside-view monitors, but one X-Plane outside-view slot is recorded at 640x480 full resolution.
2. Physical setup includes 3 G5 displays, but X-Plane window config only shows 2 avionics monitor slots and both are assigned to G1000 devices.
3. RealSimGear DeviceMapping.ini contains two G5 entries using the same COM6 port.
4. The desired G5 behavior includes switching roles via hardware toggle buttons, but the persisted config here does not yet make that role-switch behavior explicit.

## Known-good facts from the current snapshot

- The aircraft recently used in X-Plane is the Oden Aerospace C172 G1000 variant.
- RealSimGear command mappings for G1000 PFD, G1000 PFD2, G5 PFD, and G5 HSI are present.
- X-Plane is currently configured for 3 outside-view render windows and 2 dedicated avionics monitor windows.

## Open questions

1. Which Windows display IDs correspond to the left, center, and right outside-view monitors physically?
2. Which numeric RealSimGear function IDs correspond to PFD, MFD, HSI, and backup-display roles?
3. Is the duplicate COM6 mapping intentional, stale, or the direct cause of the reconfiguration crash?
4. Does the crash occur in X-Plane, in the RealSimGear plugin UI, or when switching persona assignments on the hardware itself?
