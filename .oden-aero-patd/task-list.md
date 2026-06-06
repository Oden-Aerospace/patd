# PATD Task List

## Active workstream

1. Reset monitor layout prefs and rebuild the display positions from scratch.
2. Confirm whether the upgrade dialog still appears after a clean monitor reset.
3. Resolve duplicate RealSimGear G5 COM6 mapping and popup target conflicts.
4. Determine why X-Plane still logs the monitor 2 custom-resolution restore warning.
5. Add pre/post snapshot diff reporting.
6. Investigate RealSimGear and G5 runtime commands or datarefs for live popup reassignment.
7. Document confirmed runtime control points in the PATD spec.
8. Decide whether live reset should be implemented with an in-sim plugin.

## Execution order

Current default order:

1. Clean monitor reset and manual recapture
2. Upgrade dialog investigation
3. G5 duplicate mapping cleanup
4. Snapshot diff support
5. Runtime API investigation
6. In-sim plugin decision

## Done

1. Create PATD display specification in `displays.md`.
2. Create issue tracker structure under `.oden-aero-patd`.
3. Capture current crash-log findings for issue 001.
4. Build initial Python harness and local `.venv` support.
5. Add stricter spec-driven monitor validation and safe config draft generation.
6. Add `apply-safe-config` to the harness.
7. Back up `Output/preferences/X-Plane Window Positions.prf` automatically before rewrite.
8. Rewrite only the known-bad outside-view full-resolution entry.
9. Re-run the harness and verify `outside_view_resolution_1` passes.
10. Harden startup prompt suppression in the harness by clearing `default_situation`, setting `_warn_update 0`, and stripping `UNSAFE` before launch.
11. Re-run a validation snapshot and confirm the PATD spec checks pass except for the known duplicate G5 port issue.
12. Confirm the stale situation-file startup popup is gone after removing `default_situation` from `Output/preferences/Miscellaneous.prf`.
13. Add guaranteed post-run cleanup so harness prompt suppression is restored even if run capture fails.
14. Add a monitor reset command and a default 30-second manual startup interaction window for live recapture.