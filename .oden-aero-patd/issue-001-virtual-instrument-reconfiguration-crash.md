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
- One X-Plane outside-view slot is stored with a 640x480 full resolution, which is inconsistent with the intended outside-view monitor setup.

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
2. Inspect Log.txt immediately after the crash for RealSimGear and display-manager errors.
3. Correlate each physical monitor to its Windows display ID.
4. Correlate each physical G5 to its COM port and intended persona.
5. Determine whether one of the duplicate COM6 G5 entries should be removed or re-enumerated.
6. Verify whether X-Plane should expose separate monitor windows for G5s, or whether those are fully plugin-driven and should not appear in X-Plane monitor assignments.

## Exit criteria

This issue can move to resolved when:

- X-Plane starts without display-assignment errors
- instrument displays load in the intended roles
- G5 hardware role switching works without crashing
- the documented config in displays.md matches the live setup
