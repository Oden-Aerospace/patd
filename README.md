# X-Plane 12 Config Sync

Personal Aviation Training Device (PATD) configuration snapshot for X-Plane 12.

This repository is intentionally restricted to small, text-based configuration files.

## What is tracked

- `Custom Scenery/scenery_packs.ini`
- All files in `Output/preferences/`
- Selected plugin mapping/config files in `Resources/plugins/`

## What is NOT tracked

- Aircraft, scenery, meshes, nav databases, installers, binaries, logs, and media assets.

## Daily workflow

1. Make your sim/config changes.
2. Run `git status`.
3. Commit only the allowed config file diffs.
4. Push to `origin`.

## Add more config files later

Update `.gitignore` with additional allowlist entries (using `!path/to/file`) for any new text-based settings you want to sync.
