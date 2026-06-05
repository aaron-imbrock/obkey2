import gi
gi.require_version('Gtk', '3.0')
import signal
import sys
import os
from gi.repository import GLib, Gtk
from obkey2 import classes as obkey_classes


def _unsaved_dialog(win):
    """Return Gtk.ResponseType: YES=save, NO=discard, CANCEL=go back."""
    dialog = Gtk.MessageDialog(
        transient_for=win,
        modal=True,
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.NONE,
        text="You have unsaved changes.",
    )
    dialog.format_secondary_text("Save changes before closing?")
    dialog.add_buttons(
        "_Discard", Gtk.ResponseType.NO,
        "_Cancel",  Gtk.ResponseType.CANCEL,
        "_Save",    Gtk.ResponseType.YES,
    )
    dialog.set_default_response(Gtk.ResponseType.YES)
    response = dialog.run()
    dialog.destroy()
    return response


def main():
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)

    path = os.path.expanduser("~/.config/openbox/rc.xml")
    if len(sys.argv) == 2:
        path = sys.argv[1]

    ob = obkey_classes.OpenboxConfig()
    ob.load(path)

    win = Gtk.Window()
    win.set_default_size(800, 560)

    header = Gtk.HeaderBar()
    header.set_show_close_button(True)
    header.set_title(obkey_classes.config_title)
    header.set_subtitle(os.path.basename(path))

    save_btn = Gtk.Button()
    save_btn.set_image(Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.BUTTON))
    save_btn.set_tooltip_text("Save " + path)
    save_btn.connect("clicked", lambda b: ob.save())
    header.pack_start(save_btn)

    win.set_titlebar(header)

    def request_quit():
        if ob.dirty:
            response = _unsaved_dialog(win)
            if response == Gtk.ResponseType.YES:
                ob.save()
            elif response == Gtk.ResponseType.CANCEL:
                return
        Gtk.main_quit()

    def on_delete_event(widget, event):
        request_quit()
        return True

    win.connect("delete-event", on_delete_event)

    tbl  = obkey_classes.PropertyTable(mark_dirty=ob.mark_dirty)
    al   = obkey_classes.ActionList(tbl, on_change=ob.mark_dirty)
    ktbl = obkey_classes.KeyTable(al, ob, quit_cb=request_quit)

    vbox = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
    vbox.pack1(tbl.widget, True, False)
    vbox.pack2(al.widget, True, False)

    hbox = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
    hbox.pack1(ktbl.widget, True, False)
    hbox.pack2(vbox, False, False)

    win.add(hbox)
    win.show_all()
    w, h = win.get_size()
    hbox.set_position(w - 280)
    vbox.set_position(h // 2)
    ktbl.view.grab_focus()
    Gtk.main()
    win.destroy()


if __name__ == "__main__":
    main()
