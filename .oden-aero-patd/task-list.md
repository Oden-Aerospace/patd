# PATD Task List

## Active workstream

1. Add `apply-safe-config` to the harness.
2. Back up `Output/preferences/X-Plane Window Positions.prf` before any rewrite.
3. Rewrite only the understood monitor-related settings for the outside-view monitors.
4. Re-run the harness after applying the safe config.
5. Add pre/post snapshot diff reporting.
6. Investigate RealSimGear and G5 runtime commands or datarefs for live popup reassignment.
7. Document confirmed runtime control points in the PATD spec.
8. Decide whether live reset should be implemented with an in-sim plugin.

## Execution order

Current default order:

1. Safe config apply path
2. Snapshot diff support
3. Runtime API investigation
4. In-sim plugin decision

## Done

1. Create PATD display specification in `displays.md`.
2. Create issue tracker structure under `.oden-aero-patd`.
3. Capture current crash-log findings for issue 001.
4. Build initial Python harness and local `.venv` support.
5. Add stricter spec-driven monitor validation and safe config draft generation.