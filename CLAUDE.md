# obkey2 — Claude Guidelines

## Bug fix workflow

Every bug fix must follow this sequence before being considered done:

1. **Branch off main** — create a branch named after the fix or version (e.g. `v0.X.Y` or `fix/short-description`). Never commit bug fixes directly to `main`.
2. **Increment the patch version** — bump the version in `pyproject.toml` (e.g. `0.0.10` → `0.0.11`). Use semantic patch increments for bug fixes.
3. **Update CHANGELOG.md** — add a new `## [x.x.x] - YYYY-MM-DD` entry at the top (below the header) with a `### Fixed` section describing what was broken and how it was corrected. Date is today's date.
4. **Commit on the branch** — stage and commit `src/obkey2/classes.py`, `pyproject.toml`, `CHANGELOG.md`, and any test files together in a single commit.

## Versioning scheme

The project uses `MAJOR.MINOR.PATCH` in `pyproject.toml`. Bug fixes increment `PATCH`. New features increment `MINOR`. The version in `pyproject.toml` is the single source of truth.

## Changelog format

Follow the existing pattern in `CHANGELOG.md`:

```
## [x.x.x] - YYYY-MM-DD

### Fixed
- One-line description of the bug and the fix.
```

Sections used: `Added`, `Changed`, `Fixed`, `Removed`.
