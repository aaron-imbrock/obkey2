# Changelog

All notable changes to this project will be documented here.

## [0.0.13] - 2026-06-05

### Fixed
- `CellRendererCombo` with `has_entry=False` triggered `gtk_cell_area_activate_cell: GTK_IS_CELL_EDITABLE` assertion in GTK3, preventing the action-type dropdown from opening. Switched to `has_entry=True` and added an `edited` signal handler to validate typed action names.
- `PropertyTable.clear()` removed child widgets without destroying them, leaving orphaned GDK windows and producing `gdk_window_get_window_type: GDK_IS_WINDOW` assertions. Now calls `child.destroy()` after each removal.

## [0.0.12] - 2026-06-05

### Changed
- Replaced all deprecated GTK2-era APIs with proper GTK3 equivalents: `Gtk.ToolButton.new_from_stock`, `Gtk.ImageMenuItem`, `Gtk.Table`, `Gtk.AttachOptions`, `add_with_viewport`, and `Label.set_padding` are gone.
- Toolbar and context menu icons now use named freedesktop theme icons (`list-add`, `list-remove`, `go-up`, `go-down`, `edit-cut`, `edit-copy`, `edit-paste`, `edit-delete`, `format-indent-more`, `application-exit`) instead of deprecated GTK stock items.
- `PropertyTable` and `OCStartupNotify` sub-table rebuilt with `Gtk.Grid` (row/column spacing, margins) replacing the deprecated `Gtk.Table`.
- Main window now uses `Gtk.HeaderBar` with title, filename subtitle, and Save button (`document-save-symbolic`); Save removed from the keybind toolbar.
- Default window size increased to 800×560; right pane initialises at 280 px, vertical split at 50 % of height.
- Entry module renamed from `__main__.py` to `app.py`; `pyproject.toml` entry point updated to `obkey2.app:main`.

## [0.0.11] - 2026-06-04

### Fixed
- Replace `xml.dom.minidom._write_data` call with `xml.sax.saxutils.escape` to fix `TypeError` on Python 3.13 where the private API gained a required third argument.
- Add `"Primary": "C"` to `replace_table_gtk2openbox` so GTK3's `<Primary>` modifier alias for Control no longer raises `KeyError` during accelerator editing.

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
