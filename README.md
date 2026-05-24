# obkey2 — Openbox Key Editor

A graphical editor for the keyboard shortcuts section of the Openbox window manager configuration (`rc.xml`).

## Dependencies

### System packages (install via your package manager)

**Debian/Ubuntu:**
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

**Fedora/RHEL:**
```bash
sudo dnf install python3-gobject gtk3
```

**Arch Linux:**
```bash
sudo pacman -S python-gobject gtk3
```

> You also need [Openbox](http://openbox.org) itself installed. obkey2 edits `~/.config/openbox/rc.xml`.

## Installation

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install directly from git
uv tool install git+https://github.com/aaron-imbrock/obkey2.git

# Or from a local clone
uv tool install /path/to/obkey2
```

For development (editable install):

```bash
uv pip install -e .
```

## Usage

```bash
# Edit the default Openbox config
obkey

# Edit a specific rc.xml file
obkey /path/to/rc.xml
```

## Interface

The main window has three panes:

- **Left — Key tree**: shows all keybindings in a hierarchy. Top-level keys and chained key sequences are shown as parent/child nodes.
- **Top-right — Action properties**: shows editable parameters for the selected action.
- **Bottom-right — Action list**: lists the actions bound to the selected key. Use the toolbar to add, remove, and reorder actions.

### Toolbar buttons (Key tree)

| Button | Action |
|--------|--------|
| Save   | Write changes back to `rc.xml` and reconfigure Openbox |
| +sibling | Insert a new keybind at the same level |
| +child | Insert a child keybind (for chained sequences) |
| Remove | Delete the selected keybind |
| Quit   | Prompt for unsaved changes, then exit |

### chainQuitKey

The bar at the bottom of the key tree shows the **chainQuitKey** — the key that cancels a chained key sequence. Edit it by clicking on it.

## Notes

- Changes are written to `rc.xml` on Save; Openbox is automatically reconfigured via `openbox --reconfigure`.
- Closing the window or pressing Quit with unsaved changes will prompt to Save, Discard, or Cancel.
- Chained keybindings (e.g. `W-F1 then W-F2`) are represented as parent/child nodes.
- A key node can have either **actions** or **child keys**, not both (unless it is a chroot node).

## Origin

Original source code taken from [https://code.google.com/archive/p/obkey](https://code.google.com/archive/p/obkey) and updated from Python 2 + PyGTK 2 to Python 3 + PyGObject (GTK 3), repackaged for installation via `uv`.

## License

MIT — original author: nsf &lt;no.smile.face@gmail.com&gt;
