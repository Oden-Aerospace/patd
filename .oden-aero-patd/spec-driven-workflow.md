# Spec-Driven Workflow

Yes. This PATD workspace can be run in a spec-driven way.

## Source of truth

Use these files as the primary specification set:

- `displays.md` for the human-readable PATD layout and intent
- `specs/patd_display_spec.json` for machine-checked expectations
- `issue-*.md` files for gaps between intended and observed behavior
- `task-list.md` for the ordered execution plan

## Working model

1. Update the human-readable spec when your intent changes.
2. Update the machine-readable spec when the harness should enforce a new rule.
3. Run the harness against the live configuration.
4. Compare observed state to the spec.
5. Make the smallest safe change.
6. Re-run the harness.
7. Commit each completed change.

## Good fit for this repo

Spec-driven work is a good fit here because the PATD problem is mostly configuration correctness:

- monitor assignment
- instrument role assignment
- persisted preference state
- plugin device mapping
- crash and log regression detection

## Limits

The current harness can validate persisted config and logs, but it does not yet prove final on-screen placement. For that, we will need one or more of:

1. runtime API hooks from X-Plane or plugins
2. screenshot-based assertions
3. an in-sim plugin for live introspection and control

## Immediate next spec-driven steps

1. Add an `apply-safe-config` command that writes a reviewed, backed-up monitor reset.
2. Add pre/post snapshot diff reporting to show exactly what changed.
3. Research X-Plane and RealSimGear runtime control points for instrument popups.