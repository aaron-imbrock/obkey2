# obkey2 — Claude Guidelines

## Development workflow

Every code change — bug fix, refactor, or new feature — must follow this sequence before being considered done:

1. **Branch off main** — create a branch named after the change type and description:
   - Bug fix: `fix/short-description` or `v0.X.Y`
   - Refactor / modernisation: `refactor/short-description`
   - New feature: `feat/short-description`
   Never commit directly to `main`.
2. **Increment the version** — bump the version in `pyproject.toml` according to the versioning scheme below.
3. **Update CHANGELOG.md** — add a new `## [x.x.x] - YYYY-MM-DD` entry at the top (below the header) with the appropriate section(s). Date is today's date.
4. **Commit on the branch** — stage and commit all changed source files, `pyproject.toml`, and `CHANGELOG.md` together in a single commit.

This workflow applies regardless of whether the change was requested as a "fix", "rebuild", "rename", or any other framing.

## Versioning scheme

The project uses `MAJOR.MINOR.PATCH` in `pyproject.toml`. The version in `pyproject.toml` is the single source of truth.

| Change type | Version increment | Example |
|---|---|---|
| Bug fix | PATCH | `0.0.11` → `0.0.12` |
| Refactor / internal modernisation | PATCH | `0.0.11` → `0.0.12` |
| New user-facing feature | MINOR | `0.0.11` → `0.1.0` |
| Breaking change | MAJOR | `0.0.11` → `1.0.0` |

## Changelog format

Follow the existing pattern in `CHANGELOG.md`:

```
## [x.x.x] - YYYY-MM-DD

### Fixed
- One-line description of the bug and the fix.
```

Sections used: `Added`, `Changed`, `Fixed`, `Removed`.
