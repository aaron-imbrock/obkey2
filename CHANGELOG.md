# Changelog

All notable changes to this project will be documented here.

## [0.0.10] - 2026-06-04

### Fixed
- Escape special XML characters during save serialization so keyboard data containing `&`, `<`, `"`, and similar values writes valid Openbox XML.
- Apply `xml_quoteattr` to attribute values (`action name=`, `keybind key=`) so keys and action names with special characters round-trip correctly.

### Added
- `xml_escape()` and `xml_quoteattr()` helper functions wrapping `xml.sax.saxutils` for consistent XML encoding across all serialization paths.
- Test suite (`tests/test_xml_serialization.py`) covering XML escaping in `OCString.deparse` and `OBKeyboard` serialization round-trips.

## [0.0.8] - 2026-05-24

### Changed
- CLI command renamed from `obkey2` back to `obkey`. Package name remains `obkey2`.

## [0.0.7] - 2026-05-24

### Added
- Unsaved-changes dialog on close: closing the window or pressing Quit when
  there are unsaved edits prompts **Save / Discard / Cancel** before exiting.
  Dirty state is tracked across all edit paths — key edits, chroot toggles,
  action type changes, property widget changes, action reordering, and
  finalactions sub-lists.

### Changed
- Project renamed from `obkey` to `obkey2`; CLI command is now `obkey2`.
- Package directory renamed `src/obkey/` → `src/obkey2/`.
- Window title updated to `obkey2`.

## [0.0.6] - 2026-05-24

### Fixed
- Ctrl+C now terminates the application cleanly. GTK's GLib event loop
  previously blocked `SIGINT`; a `GLib.unix_signal_add` handler now delivers
  the signal inside the main loop and calls `Gtk.main_quit`.

## [0.0.5] - 2026-05-24

### Added
- `pyproject.toml` with hatchling build backend; installable via `uv pip install .` or `uv tool install .`
- Entry point `obkey` wired to `obkey.__main__:main`
- Icons bundled inside the Python package at `src/obkey/icons/`

### Changed
- Ported from Python 2 + PyGTK 2 to Python 3 + PyGObject (GTK 3)
- Replaced `import gtk` / `import gobject` with `gi.repository.Gtk` / `gi.repository.GObject`
- Replaced `from StringIO import StringIO` with `from io import StringIO`
- Replaced `file()` built-in with `open()`
- Fixed `dict.keys().sort()` → `sorted(dict.keys())` for Python 3 compatibility
- Replaced `distutils` / `setup.py` with `pyproject.toml`
- Dropped locale / gettext support (English only)
- Icons now found relative to package `__file__` instead of `/usr/share/obkey/icons`

### Removed
- `setup.py`, old `obkey` script, `obkey_classes.py`, `build/`, `locale/`, `po/`
