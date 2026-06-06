# PATD Task List

## Active workstream

1. Add pre/post snapshot diff reporting.
2. Investigate RealSimGear and G5 runtime commands or datarefs for live popup reassignment.
3. Document confirmed runtime control points in the PATD spec.
4. Decide whether live reset should be implemented with an in-sim plugin.

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
6. Add `apply-safe-config` to the harness.
7. Back up `Output/preferences/X-Plane Window Positions.prf` automatically before rewrite.
8. Rewrite only the known-bad outside-view full-resolution entry.
9. Re-run the harness and verify `outside_view_resolution_1` passes.