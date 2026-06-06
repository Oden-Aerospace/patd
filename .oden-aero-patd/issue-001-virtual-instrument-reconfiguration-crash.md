# Issue 001: Virtual instrument reconfiguration crashes X-Plane

## Summary

X-Plane is not reliably loading the intended virtual instrument configuration for the PATD. Attempting to reconfigure the instrument displays causes a crash.

## Desired state

- 3 outside-view monitors for left, center, and right cockpit views
- 1 RealSimGear G1000 PFD
- 1 RealSimGear G1000 MFD
- 3 RealSimGear G5 displays
- G5 displays should be reconfigurable via hardware toggle buttons

## Observed state

- Windows currently reports 8 active displays.
- X-Plane currently defines 5 monitor slots: 3 outside-view slots and 2 avionics slots.
- The two X-Plane avionics slots are assigned to `G1000_MFD` and `G1000_PFD1`.
- RealSimGear plugin config shows 2 G1000 displays and 3 G5 displays.
- Two of the 3 G5 entries in DeviceMapping.ini are assigned to the same COM6 port.
- The previously bad center outside-view persisted full resolution has been repaired from 640x480 to 3840x2160 using the PATD safe-config harness path.

## Current hypothesis

The crash is likely caused by one of these persisted-configuration conflicts:

1. The RealSimGear device map contains duplicate or stale G5 serial/port assignments.
2. X-Plane monitor assignment state is out of sync with the actual Windows display layout.
3. X-Plane and the RealSimGear plugin disagree about which devices are active instrument displays versus switchable personas.
4. The plugin supports G5 personas, but the current persisted config does not cleanly represent the intended three-G5 switching model.

## Evidence

- Output/preferences/X-Plane Window Positions.prf records:
  - `num_monitors 5`
  - 3 `wmgr_usage_normal_visuals` windows
  - 2 `wmgr_usage_avionics` windows
  - avionics devices `G1000_MFD` and `G1000_PFD1`
- Resources/plugins/RealSimGear/README.txt documents:
  - G1000 personas: `PFD`, `MFD`, `PFD2`
  - G5 personas: `PFD`, `HSI`
- Resources/plugins/RealSimGear/DeviceMapping.ini records 3 G5 entries, including two on COM6.

## Crash log findings from 2026-06-06 session

Observed in Log.txt:

- X-Plane fails early while restoring monitor configuration:
  - `Failed to restore custom screen resolution. Monitor 2 does not appear to support a resolution of 3840x2160.`
- The RealSimGear and aircraft-specific command maps both load successfully.
- The RealSimGear plugin opens COM10, COM11, COM12, and COM6.
- The G5 plugin initializes duplicate popup instances:
  - `Init G5 Popup (A) No Bezel Duplicate`
  - `Init G5 Popup (B) No Bezel Duplicate`
- The G5 plugin later reports monitor assignment conflicts:
  - `RSG: G5 A already has existing target monitor ID set`
  - `RSG: G5 B already has existing target monitor ID set`
  - `RSG: G5 B DUP already has existing target monitor ID set`
- During reconfiguration, X-Plane cannot save the window-layout preference file:
  - `The file could not be saved... C:\X-Plane 12\Output\preferences\X-Plane Window Positions.prf`
- The file is not currently marked read-only at the Windows file-attribute level, so this save failure is likely due to a transient lock, failed write path, or X-Plane/plugin state rather than the simple read-only attribute bit.
- Shortly before the crash, X-Plane reports:
  - `Opened window Settings`
  - `Runloop is backed up. Current task count: 440, estimated runtime: 64.953s`
- The crash footer appears immediately after the Settings window interaction.

Observed in Log_ATC.txt:

- No instrument-specific crash cause is visible there.
- The crash report footer points to Log_ATC.txt, but the meaningful instrument and monitor clues are in Log.txt.

## Reproduction notes

Current reproduction statement from operator:

- X-Plane crashes when trying to change instrument display configuration.

The exact reconfiguration path still needs to be pinned down:

1. Does the crash happen in X-Plane display settings?
2. Does it happen in the RealSimGear plugin UI?
3. Does it happen when pressing a G5 hardware toggle?
4. Does it happen only in the Oden Aerospace C172 G1000 aircraft?

## Next checks

1. Capture the exact X-Plane or plugin action that triggers the crash.
2. Correlate each physical monitor to its Windows display ID, with special attention to the display X-Plane calls monitor 2.
3. Correlate each physical G5 to its COM port and intended persona.
4. Determine whether one of the duplicate COM6 G5 entries should be removed or re-enumerated.
5. Verify whether the G5 popup target monitors can be reset cleanly by removing stale popup or monitor-assignment state.
6. Verify whether X-Plane should expose separate monitor windows for G5s, or whether those are fully plugin-driven and should not appear in X-Plane monitor assignments.
7. Reproduce once more and capture the exact click path inside the Settings window that immediately precedes the crash.

## Progress update

- The PATD harness now supports `apply-safe-config` with automatic backup of `Output/preferences/X-Plane Window Positions.prf`.
- That repair path updated the persisted center outside-view full resolution from 640x480 to 3840x2160.
- A post-apply harness snapshot now passes the `outside_view_resolution_1` check.
- The harness now sanitizes startup prompts before launch by clearing `default_situation`, setting `_warn_update 0`, and removing `UNSAFE` from `Output/preferences/X-Plane Screen Res.prf`.
- A fresh static snapshot at `.oden-aero-patd/runs/20260606T203802Z` shows the PATD spec checks passing for monitor count, outside-view geometry, outside-view resolution, avionics assignments, and device counts.
- The stale `Output/situations/Cessna Skyhawk (G1000) Situation 49.sit` startup popup is no longer present after removing `default_situation` from `Output/preferences/Miscellaneous.prf`.
- The cached-update suppression is not sufficient to prevent the upgrade dialog from appearing during live startup, so that prompt remains an outstanding issue.
- The remaining leading suspects are now the duplicate G5 COM6 mapping, duplicate G5 popup target-monitor assignment state, the lingering `Failed to restore custom screen resolution` log entry for monitor 2, and whatever live path still raises the upgrade dialog.

## Current operator workflow

1. Reset persisted monitor layout prefs and let X-Plane rebuild them from scratch.
2. Allow up to 30 seconds at startup for the operator to dismiss dialogs and manually position windows.
3. Capture a new snapshot only after the operator confirms the layout is correct.

## Exit criteria

This issue can move to resolved when:

- X-Plane starts without display-assignment errors
- instrument displays load in the intended roles
- G5 hardware role switching works without crashing
- the documented config in displays.md matches the live setup
