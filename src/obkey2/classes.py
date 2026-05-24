import gi
gi.require_version('Gtk', '3.0')
import xml.dom.minidom
from io import StringIO
from gi.repository import GObject, Gtk
import copy
import sys
import os
import gettext

#------------------------------------------------------------------------------
# Config
#------------------------------------------------------------------------------

_pkg_dir = os.path.dirname(os.path.abspath(__file__))
config_icons = os.path.join(_pkg_dir, 'icons')
config_locale_dir = os.path.join(_pkg_dir, 'locale')

_ = lambda x: x
config_title = 'obkey2'

#------------------------------------------------------------------------------
# Key utils
#------------------------------------------------------------------------------

replace_table_openbox2gtk = {
    "mod1":    "<Mod1>",
    "mod2":    "<Mod2>",
    "mod3":    "<Mod3>",
    "mod4":    "<Mod4>",
    "mod5":    "<Mod5>",
    "control": "<Ctrl>",
    "c":       "<Ctrl>",
    "alt":     "<Alt>",
    "a":       "<Alt>",
    "meta":    "<Meta>",
    "m":       "<Meta>",
    "super":   "<Super>",
    "w":       "<Super>",
    "shift":   "<Shift>",
    "s":       "<Shift>",
    "hyper":   "<Hyper>",
    "h":       "<Hyper>",
}

replace_table_gtk2openbox = {
    "Mod1":    "Mod1",
    "Mod2":    "Mod2",
    "Mod3":    "Mod3",
    "Mod4":    "Mod4",
    "Mod5":    "Mod5",
    "Control": "C",
    "Alt":     "A",
    "Meta":    "M",
    "Super":   "W",
    "Shift":   "S",
    "Hyper":   "H",
}


def _accelerator_parse(accel_str):
    result = Gtk.accelerator_parse(accel_str)
    # PyGObject >= 3.42 returns (success, key, mods); older returns (key, mods)
    if len(result) == 3:
        return result[1], result[2]
    return result


def key_openbox2gtk(obstr):
    toks = obstr.split("-")
    try:
        toksgdk = [replace_table_openbox2gtk[mod.lower()] for mod in toks[:-1]]
    except Exception:
        return (0, 0)
    toksgdk.append(toks[-1])
    return _accelerator_parse("".join(toksgdk))


def key_gtk2openbox(key, mods):
    result = ""
    if mods:
        s = Gtk.accelerator_name(0, mods)
        svec = [replace_table_gtk2openbox[i] for i in s[1:-1].split('><')]
        result = '-'.join(svec)
    if key:
        k = Gtk.accelerator_name(key, 0)
        if result:
            result += '-'
        result += k
    return result

#------------------------------------------------------------------------------
# Sensitivity switchers / conditions
#------------------------------------------------------------------------------

class SensCondition:
    def __init__(self, initial_state):
        self.switchers = []
        self.state = initial_state

    def register_switcher(self, sw):
        self.switchers.append(sw)

    def set_state(self, state):
        if self.state == state:
            return
        self.state = state
        for sw in self.switchers:
            sw.notify()


class SensSwitcher:
    def __init__(self, conditions):
        self.conditions = conditions
        self.widgets = []
        for c in conditions:
            c.register_switcher(self)

    def append(self, widget):
        self.widgets.append(widget)

    def set_sensitive(self, state):
        for w in self.widgets:
            w.set_sensitive(state)

    def notify(self):
        for c in self.conditions:
            if not c.state:
                self.set_sensitive(False)
                return
        self.set_sensitive(True)

#------------------------------------------------------------------------------
# KeyTable
#------------------------------------------------------------------------------

class KeyTable:
    def __init__(self, actionlist, ob, quit_cb=None):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.ob = ob
        self.quit_cb = quit_cb or Gtk.main_quit
        self.actionlist = actionlist
        actionlist.set_callback(self.actions_cb)

        self.icons = self.load_icons()

        self.model, self.cqk_model = self.create_models()
        self.view, self.cqk_view = self.create_views(self.model, self.cqk_model)

        self.copied = None

        self.cond_insert_child      = SensCondition(False)
        self.cond_paste_buffer      = SensCondition(False)
        self.cond_selection_available = SensCondition(False)

        self.sw_insert_child_and_paste = SensSwitcher([self.cond_insert_child, self.cond_paste_buffer])
        self.sw_insert_child           = SensSwitcher([self.cond_insert_child])
        self.sw_paste_buffer           = SensSwitcher([self.cond_paste_buffer])
        self.sw_selection_available    = SensSwitcher([self.cond_selection_available])

        self.context_menu = self.create_context_menu()

        for kb in self.ob.keyboard.keybinds:
            self.apply_keybind(kb)

        self.apply_cqk_initial_value()

        self.widget.pack_start(self.create_toolbar(), False, False, 0)
        self.widget.pack_start(self.create_scroll(self.view), True, True, 0)
        self.widget.pack_start(self.create_cqk_hbox(self.cqk_view), False, False, 0)

        if len(self.model):
            self.view.get_selection().select_iter(self.model.get_iter_first())

        self.sw_insert_child_and_paste.notify()
        self.sw_insert_child.notify()
        self.sw_paste_buffer.notify()
        self.sw_selection_available.notify()

    def create_cqk_hbox(self, cqk_view):
        cqk_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        cqk_label = Gtk.Label(label=_("chainQuitKey:"))
        cqk_label.set_padding(5, 5)

        cqk_frame = Gtk.Frame()
        cqk_frame.add(cqk_view)

        cqk_hbox.pack_start(cqk_label, False, False, 0)
        cqk_hbox.pack_start(cqk_frame, True, True, 0)
        return cqk_hbox

    def create_context_menu(self):
        context_menu = Gtk.Menu()

        item = Gtk.ImageMenuItem.new_from_stock("gtk-cut", None)
        item.connect('activate', lambda menu: self.cut_selected())
        item.get_child().set_label(_("Cu_t"))
        context_menu.append(item)
        self.sw_selection_available.append(item)

        item = Gtk.ImageMenuItem.new_from_stock("gtk-copy", None)
        item.connect('activate', lambda menu: self.copy_selected())
        item.get_child().set_label(_("_Copy"))
        context_menu.append(item)
        self.sw_selection_available.append(item)

        item = Gtk.ImageMenuItem.new_from_stock("gtk-paste", None)
        item.connect('activate', lambda menu: self.insert_sibling(self.copied))
        item.get_child().set_label(_("_Paste"))
        context_menu.append(item)
        self.sw_paste_buffer.append(item)

        item = Gtk.ImageMenuItem.new_from_stock("gtk-paste", None)
        item.get_child().set_label(_("P_aste as child"))
        item.connect('activate', lambda menu: self.insert_child(self.copied))
        context_menu.append(item)
        self.sw_insert_child_and_paste.append(item)

        item = Gtk.ImageMenuItem.new_from_stock("gtk-remove", None)
        item.connect('activate', lambda menu: self.del_selected())
        item.get_child().set_label(_("_Remove"))
        context_menu.append(item)
        self.sw_selection_available.append(item)

        context_menu.show_all()
        return context_menu

    def create_models(self):
        model = Gtk.TreeStore(
            GObject.TYPE_UINT,    # accel key
            GObject.TYPE_INT,     # accel mods
            GObject.TYPE_STRING,  # accel string (openbox)
            GObject.TYPE_BOOLEAN, # chroot
            GObject.TYPE_BOOLEAN, # show chroot
            GObject.TYPE_PYOBJECT # OBKeyBind
        )
        cqk_model = Gtk.ListStore(
            GObject.TYPE_UINT,   # accel key
            GObject.TYPE_INT,    # accel mods
            GObject.TYPE_STRING  # accel string (openbox)
        )
        return (model, cqk_model)

    def create_scroll(self, view):
        scroll = Gtk.ScrolledWindow()
        scroll.add(view)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        return scroll

    def create_views(self, model, cqk_model):
        r0 = Gtk.CellRendererAccel()
        r0.props.editable = True
        r0.connect('accel-edited', self.accel_edited)

        r1 = Gtk.CellRendererText()
        r1.props.editable = True
        r1.connect('edited', self.key_edited)

        r2 = Gtk.CellRendererToggle()
        r2.connect('toggled', self.chroot_toggled)

        c0 = Gtk.TreeViewColumn(_("Key"), r0, accel_key=0, accel_mods=1)
        c1 = Gtk.TreeViewColumn(_("Key (text)"), r1, text=2)
        c2 = Gtk.TreeViewColumn(_("Chroot"), r2, active=3, visible=4)

        c0.set_expand(True)

        view = Gtk.TreeView(model=model)
        view.append_column(c0)
        view.append_column(c1)
        view.append_column(c2)
        view.get_selection().connect('changed', self.view_cursor_changed)
        view.connect('button-press-event', self.view_button_clicked)

        # chainQuitKey table
        r0 = Gtk.CellRendererAccel()
        r0.props.editable = True
        r0.connect('accel-edited', self.cqk_accel_edited)

        r1 = Gtk.CellRendererText()
        r1.props.editable = True
        r1.connect('edited', self.cqk_key_edited)

        c0 = Gtk.TreeViewColumn("Key", r0, accel_key=0, accel_mods=1)
        c1 = Gtk.TreeViewColumn("Key (text)", r1, text=2)
        c0.set_expand(True)

        def cqk_view_focus_lost(view, event):
            view.get_selection().unselect_all()

        cqk_view = Gtk.TreeView(model=cqk_model)
        cqk_view.set_headers_visible(False)
        cqk_view.append_column(c0)
        cqk_view.append_column(c1)
        cqk_view.connect('focus-out-event', cqk_view_focus_lost)
        return (view, cqk_view)

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.set_show_arrow(False)

        but = Gtk.ToolButton.new_from_stock("gtk-save")
        but.set_tooltip_text(_("Save ") + self.ob.path + _(" file"))
        but.connect('clicked', lambda but: self.ob.save())
        toolbar.insert(but, -1)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        but = Gtk.ToolButton(icon_widget=self.icons['add_sibling'])
        but.set_tooltip_text(_("Insert sibling keybind"))
        but.connect('clicked', lambda but: self.insert_sibling(OBKeyBind()))
        toolbar.insert(but, -1)

        but = Gtk.ToolButton(icon_widget=self.icons['add_child'])
        but.set_tooltip_text(_("Insert child keybind"))
        but.connect('clicked', lambda but: self.insert_child(OBKeyBind()))
        toolbar.insert(but, -1)
        self.sw_insert_child.append(but)

        but = Gtk.ToolButton.new_from_stock("gtk-remove")
        but.set_tooltip_text(_("Remove keybind"))
        but.connect('clicked', lambda but: self.del_selected())
        toolbar.insert(but, -1)
        self.sw_selection_available.append(but)

        sep = Gtk.SeparatorToolItem()
        sep.set_draw(False)
        sep.set_expand(True)
        toolbar.insert(sep, -1)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        but = Gtk.ToolButton.new_from_stock("gtk-quit")
        but.set_tooltip_text(_("Quit application"))
        but.connect('clicked', lambda but: self.quit_cb())
        toolbar.insert(but, -1)
        return toolbar

    def apply_cqk_initial_value(self):
        cqk_accel_key, cqk_accel_mods = key_openbox2gtk(self.ob.keyboard.chainQuitKey)
        if cqk_accel_mods == 0:
            self.ob.keyboard.chainQuitKey = ""
        self.cqk_model.append((cqk_accel_key, int(cqk_accel_mods), self.ob.keyboard.chainQuitKey))

    def apply_keybind(self, kb, parent=None):
        accel_key, accel_mods = key_openbox2gtk(kb.key)
        chroot = kb.chroot
        show_chroot = len(kb.children) > 0 or not len(kb.actions)
        n = self.model.append(parent,
                (accel_key, int(accel_mods), kb.key, chroot, show_chroot, kb))
        for c in kb.children:
            self.apply_keybind(c, n)

    def load_icons(self):
        icons = {}
        icons['add_sibling'] = Gtk.Image.new_from_file(os.path.join(config_icons, "add_sibling.png"))
        icons['add_child']   = Gtk.Image.new_from_file(os.path.join(config_icons, "add_child.png"))
        return icons

    # callbacks

    def view_button_clicked(self, view, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pathinfo = view.get_path_at_pos(x, y)
            if pathinfo:
                path, col, cellx, celly = pathinfo
                view.grab_focus()
                view.set_cursor(path, col, 0)
                self.context_menu.popup(None, None, None, None, event.button, time)
            else:
                view.grab_focus()
                view.get_selection().unselect_all()
                self.context_menu.popup(None, None, None, None, event.button, time)
            return 1

    def actions_cb(self):
        (model, it) = self.view.get_selection().get_selected()
        kb = model.get_value(it, 5)
        if len(kb.actions) == 0:
            model.set_value(it, 4, True)
            self.cond_insert_child.set_state(True)
        else:
            model.set_value(it, 4, False)
            self.cond_insert_child.set_state(False)

    def view_cursor_changed(self, selection):
        (model, it) = selection.get_selected()
        actions = None
        if it:
            kb = model.get_value(it, 5)
            if len(kb.children) == 0 and not kb.chroot:
                actions = kb.actions
            self.cond_selection_available.set_state(True)
            self.cond_insert_child.set_state(len(kb.actions) == 0)
        else:
            self.cond_insert_child.set_state(False)
            self.cond_selection_available.set_state(False)
        self.actionlist.set_actions(actions)

    def cqk_accel_edited(self, cell, path, accel_key, accel_mods, keycode):
        self.cqk_model[path][0] = accel_key
        self.cqk_model[path][1] = int(accel_mods)
        kstr = key_gtk2openbox(accel_key, accel_mods)
        self.cqk_model[path][2] = kstr
        self.ob.keyboard.chainQuitKey = kstr
        self.ob.mark_dirty()
        self.view.grab_focus()

    def cqk_key_edited(self, cell, path, text):
        key, mods = key_openbox2gtk(text)
        self.cqk_model[path][0] = key
        self.cqk_model[path][1] = int(mods)
        self.cqk_model[path][2] = text
        self.ob.keyboard.chainQuitKey = text
        self.ob.mark_dirty()
        self.view.grab_focus()

    def accel_edited(self, cell, path, accel_key, accel_mods, keycode):
        self.model[path][0] = accel_key
        self.model[path][1] = int(accel_mods)
        kstr = key_gtk2openbox(accel_key, accel_mods)
        self.model[path][2] = kstr
        self.model[path][5].key = kstr
        self.ob.mark_dirty()

    def key_edited(self, cell, path, text):
        key, mods = key_openbox2gtk(text)
        self.model[path][0] = key
        self.model[path][1] = int(mods)
        self.model[path][2] = text
        self.model[path][5].key = text
        self.ob.mark_dirty()

    def chroot_toggled(self, cell, path):
        self.model[path][3] = not self.model[path][3]
        kb = self.model[path][5]
        kb.chroot = self.model[path][3]
        if kb.chroot:
            self.actionlist.set_actions(None)
        elif not kb.children:
            self.actionlist.set_actions(kb.actions)
        self.ob.mark_dirty()

    def cut_selected(self):
        self.copy_selected()
        self.del_selected()

    def copy_selected(self):
        (model, it) = self.view.get_selection().get_selected()
        if it:
            sel = model.get_value(it, 5)
            self.copied = copy.deepcopy(sel)
            self.cond_paste_buffer.set_state(True)

    def _insert_keybind(self, keybind, parent=None, after=None):
        keybind.parent = parent
        kbs = parent.children if parent else self.ob.keyboard.keybinds
        if after:
            kbs.insert(kbs.index(after) + 1, keybind)
        else:
            kbs.append(keybind)

    def insert_sibling(self, keybind):
        (model, it) = self.view.get_selection().get_selected()

        accel_key, accel_mods = key_openbox2gtk(keybind.key)
        show_chroot = len(keybind.children) > 0 or not len(keybind.actions)

        if it:
            parent_it = model.iter_parent(it)
            parent = None
            if parent_it:
                parent = model.get_value(parent_it, 5)
            after = model.get_value(it, 5)
            self._insert_keybind(keybind, parent, after)
            newit = self.model.insert_after(parent_it, it,
                    (accel_key, int(accel_mods), keybind.key, keybind.chroot, show_chroot, keybind))
        else:
            self._insert_keybind(keybind)
            newit = self.model.append(None,
                    (accel_key, int(accel_mods), keybind.key, keybind.chroot, show_chroot, keybind))

        if newit:
            for c in keybind.children:
                self.apply_keybind(c, newit)
            self.view.get_selection().select_iter(newit)
        self.ob.mark_dirty()

    def insert_child(self, keybind):
        (model, it) = self.view.get_selection().get_selected()
        parent = model.get_value(it, 5)
        self._insert_keybind(keybind, parent)

        accel_key, accel_mods = key_openbox2gtk(keybind.key)
        show_chroot = len(keybind.children) > 0 or not len(keybind.actions)

        newit = self.model.append(it,
                (accel_key, int(accel_mods), keybind.key, keybind.chroot, show_chroot, keybind))

        if len(parent.children) == 1:
            self.actionlist.set_actions(None)
        self.ob.mark_dirty()

    def del_selected(self):
        (model, it) = self.view.get_selection().get_selected()
        if it:
            kb = model.get_value(it, 5)
            kbs = self.ob.keyboard.keybinds
            if kb.parent:
                kbs = kb.parent.children
            kbs.remove(kb)
            isok = self.model.remove(it)
            if isok:
                self.view.get_selection().select_iter(it)
            self.ob.mark_dirty()

#------------------------------------------------------------------------------
# PropertyTable
#------------------------------------------------------------------------------

class PropertyTable:
    def __init__(self, mark_dirty=None):
        self._mark_dirty = mark_dirty
        self.widget = Gtk.ScrolledWindow()
        self.table = Gtk.Table(1, 2)
        self.table.set_row_spacings(5)
        self.widget.add_with_viewport(self.table)
        self.widget.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    def add_row(self, label_text, table):
        label = Gtk.Label(label=_(label_text))
        label.set_xalign(0)
        label.set_yalign(0)
        row = self.table.props.n_rows
        self.table.attach(label, 0, 1, row, row + 1,
                          Gtk.AttachOptions.EXPAND | Gtk.AttachOptions.FILL, 0, 5, 0)
        self.table.attach(table, 1, 2, row, row + 1, Gtk.AttachOptions.FILL, 0, 5, 0)

    def clear(self):
        cs = self.table.get_children()
        cs.reverse()
        for c in cs:
            self.table.remove(c)
        self.table.resize(1, 2)

    def set_action(self, action):
        self.clear()
        if not action:
            return
        for a in action.option_defs:
            self.add_row(a.name + ":", a.generate_widget(action, self._mark_dirty))
        self.table.queue_resize()
        self.table.show_all()

#------------------------------------------------------------------------------
# ActionList
#------------------------------------------------------------------------------

class ActionList:
    def __init__(self, proptable=None, on_change=None):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.actions = None
        self.proptable = proptable
        self.actions_cb = None
        self._on_change = on_change
        self.copied = None

        self.cond_paste_buffer         = SensCondition(False)
        self.cond_selection_available  = SensCondition(False)
        self.cond_action_list_nonempty = SensCondition(False)
        self.cond_can_move_up          = SensCondition(False)
        self.cond_can_move_down        = SensCondition(False)

        self.sw_paste_buffer         = SensSwitcher([self.cond_paste_buffer])
        self.sw_selection_available  = SensSwitcher([self.cond_selection_available])
        self.sw_action_list_nonempty = SensSwitcher([self.cond_action_list_nonempty])
        self.sw_can_move_up          = SensSwitcher([self.cond_can_move_up])
        self.sw_can_move_down        = SensSwitcher([self.cond_can_move_down])

        self.model = self.create_model()
        self.view = self.create_view(self.model)

        self.context_menu = self.create_context_menu()

        self.widget.pack_start(self.create_scroll(self.view), True, True, 0)
        self.widget.pack_start(self.create_toolbar(), False, False, 0)

        self.sw_paste_buffer.notify()
        self.sw_selection_available.notify()
        self.sw_action_list_nonempty.notify()
        self.sw_can_move_up.notify()
        self.sw_can_move_down.notify()

    def create_model(self):
        return Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)

    def create_choices(self):
        choices = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        action_list = {}
        for a in actions:
            action_list[_(a)] = a
        for a in sorted(action_list.keys()):
            choices.append((a, action_list[a]))
        return choices

    def create_scroll(self, view):
        scroll = Gtk.ScrolledWindow()
        scroll.add(view)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        return scroll

    def create_view(self, model):
        renderer = Gtk.CellRendererCombo()

        def editingstarted(cell, widget, path):
            widget.set_wrap_width(4)

        renderer.props.model = self.create_choices()
        renderer.props.text_column = 0
        renderer.props.editable = True
        renderer.props.has_entry = False
        renderer.connect('changed', self.action_class_changed)
        renderer.connect('editing-started', editingstarted)

        column = Gtk.TreeViewColumn(_("Actions"), renderer, text=0)

        view = Gtk.TreeView(model=model)
        view.append_column(column)
        view.get_selection().connect('changed', self.view_cursor_changed)
        view.connect('button-press-event', self.view_button_clicked)
        return view

    def create_context_menu(self):
        context_menu = Gtk.Menu()

        item = Gtk.ImageMenuItem.new_from_stock("gtk-cut", None)
        item.connect('activate', lambda menu: self.cut_selected())
        item.get_child().set_label(_("Cu_t"))
        context_menu.append(item)
        self.sw_selection_available.append(item)

        item = Gtk.ImageMenuItem.new_from_stock("gtk-copy", None)
        item.connect('activate', lambda menu: self.copy_selected())
        item.get_child().set_label(_("_Copy"))
        context_menu.append(item)
        self.sw_selection_available.append(item)

        item = Gtk.ImageMenuItem.new_from_stock("gtk-paste", None)
        item.connect('activate', lambda menu: self.insert_action(self.copied))
        item.get_child().set_label(_("_Paste"))
        context_menu.append(item)
        self.sw_paste_buffer.append(item)

        item = Gtk.ImageMenuItem.new_from_stock("gtk-remove", None)
        item.connect('activate', lambda menu: self.del_selected())
        item.get_child().set_label(_("_Remove"))
        context_menu.append(item)
        self.sw_selection_available.append(item)

        context_menu.show_all()
        return context_menu

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)
        toolbar.set_show_arrow(False)

        but = Gtk.ToolButton.new_from_stock("gtk-add")
        but.set_tooltip_text(_("Insert action"))
        but.connect('clicked', lambda but: self.insert_action(OBAction("Focus")))
        toolbar.insert(but, -1)

        but = Gtk.ToolButton.new_from_stock("gtk-remove")
        but.set_tooltip_text(_("Remove action"))
        but.connect('clicked', lambda but: self.del_selected())
        toolbar.insert(but, -1)
        self.sw_selection_available.append(but)

        but = Gtk.ToolButton.new_from_stock("gtk-go-up")
        but.set_tooltip_text(_("Move action up"))
        but.connect('clicked', lambda but: self.move_selected_up())
        toolbar.insert(but, -1)
        self.sw_can_move_up.append(but)

        but = Gtk.ToolButton.new_from_stock("gtk-go-down")
        but.set_tooltip_text(_("Move action down"))
        but.connect('clicked', lambda but: self.move_selected_down())
        toolbar.insert(but, -1)
        self.sw_can_move_down.append(but)

        sep = Gtk.SeparatorToolItem()
        sep.set_draw(False)
        sep.set_expand(True)
        toolbar.insert(sep, -1)

        but = Gtk.ToolButton.new_from_stock("gtk-delete")
        but.set_tooltip_text(_("Remove all actions"))
        but.connect('clicked', lambda but: self.clear())
        toolbar.insert(but, -1)
        self.sw_action_list_nonempty.append(but)
        return toolbar

    # callbacks

    def view_button_clicked(self, view, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pathinfo = view.get_path_at_pos(x, y)
            if pathinfo:
                path, col, cellx, celly = pathinfo
                view.grab_focus()
                view.set_cursor(path, col, 0)
                self.context_menu.popup(None, None, None, None, event.button, time)
            else:
                view.grab_focus()
                view.get_selection().unselect_all()
                self.context_menu.popup(None, None, None, None, event.button, time)
            return 1

    def action_class_changed(self, combo, path, it):
        m = combo.props.model
        ntype = m.get_value(it, 1)
        self.model[path][0] = m.get_value(it, 0)
        self.model[path][1].mutate(ntype)
        if self.proptable:
            self.proptable.set_action(self.model[path][1])
        if self._on_change:
            self._on_change()

    def view_cursor_changed(self, selection):
        (model, it) = selection.get_selected()
        act = None
        if it:
            act = model.get_value(it, 1)
        if self.proptable:
            self.proptable.set_action(act)
        if act:
            l = len(self.actions)
            i = self.actions.index(act)
            self.cond_can_move_up.set_state(i != 0)
            self.cond_can_move_down.set_state(l > 1 and i + 1 < l)
            self.cond_selection_available.set_state(True)
        else:
            self.cond_can_move_up.set_state(False)
            self.cond_can_move_down.set_state(False)
            self.cond_selection_available.set_state(False)

    def cut_selected(self):
        self.copy_selected()
        self.del_selected()

    def copy_selected(self):
        if self.actions is None:
            return
        (model, it) = self.view.get_selection().get_selected()
        if it:
            a = model.get_value(it, 1)
            self.copied = copy.deepcopy(a)
            self.cond_paste_buffer.set_state(True)

    def clear(self):
        if self.actions is None or not len(self.actions):
            return
        del self.actions[:]
        self.model.clear()
        self.cond_action_list_nonempty.set_state(False)
        if self.actions_cb:
            self.actions_cb()
        if self._on_change:
            self._on_change()

    def move_selected_up(self):
        if self.actions is None:
            return
        (model, it) = self.view.get_selection().get_selected()
        if not it:
            return
        i, = self.model.get_path(it)
        l = len(self.model)
        self.cond_can_move_up.set_state(i - 1 != 0)
        self.cond_can_move_down.set_state(l > 1 and i < l)
        if i == 0:
            return
        itprev = self.model.get_iter(i - 1)
        self.model.swap(it, itprev)
        action = self.model.get_value(it, 1)
        i = self.actions.index(action)
        self.actions[i - 1], self.actions[i] = action, self.actions[i - 1]
        if self._on_change:
            self._on_change()

    def move_selected_down(self):
        if self.actions is None:
            return
        (model, it) = self.view.get_selection().get_selected()
        if not it:
            return
        i, = self.model.get_path(it)
        l = len(self.model)
        self.cond_can_move_up.set_state(i + 1 != 0)
        self.cond_can_move_down.set_state(l > 1 and i + 2 < l)
        if i + 1 >= l:
            return
        itnext = self.model.iter_next(it)
        self.model.swap(it, itnext)
        action = self.model.get_value(it, 1)
        i = self.actions.index(action)
        self.actions[i + 1], self.actions[i] = action, self.actions[i + 1]
        if self._on_change:
            self._on_change()

    def insert_action(self, action):
        if self.actions is None:
            return
        (model, it) = self.view.get_selection().get_selected()
        if it:
            self._insert_action(action, model.get_value(it, 1))
            newit = self.model.insert_after(it, (_(action.name), action))
        else:
            self._insert_action(action)
            newit = self.model.append((_(action.name), action))
        if newit:
            self.view.get_selection().select_iter(newit)
        self.cond_action_list_nonempty.set_state(len(self.model))
        if self.actions_cb:
            self.actions_cb()
        if self._on_change:
            self._on_change()

    def del_selected(self):
        if self.actions is None:
            return
        (model, it) = self.view.get_selection().get_selected()
        if it:
            self.actions.remove(model.get_value(it, 1))
            isok = self.model.remove(it)
            if isok:
                self.view.get_selection().select_iter(it)
        self.cond_action_list_nonempty.set_state(len(self.model))
        if self.actions_cb:
            self.actions_cb()
        if self._on_change:
            self._on_change()

    def set_actions(self, actionlist):
        self.actions = actionlist
        self.model.clear()
        self.widget.set_sensitive(self.actions is not None)
        if not self.actions:
            return
        for a in self.actions:
            self.model.append((_(a.name), a))
        if len(self.model):
            self.view.get_selection().select_iter(self.model.get_iter_first())
        self.cond_action_list_nonempty.set_state(len(self.model))

    def _insert_action(self, action, after=None):
        if after:
            self.actions.insert(self.actions.index(after) + 1, action)
        else:
            self.actions.append(action)

    def set_callback(self, cb):
        self.actions_cb = cb

#------------------------------------------------------------------------------
# MiniActionList
#------------------------------------------------------------------------------

class MiniActionList(ActionList):
    def __init__(self, proptable=None, on_change=None):
        ActionList.__init__(self, proptable, on_change)
        self.widget.set_size_request(-1, 120)
        self.view.set_headers_visible(False)

    def create_choices(self):
        choices = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        action_list = {}
        for a in actions:
            action_list[_(a)] = a
        for a in sorted(action_list.keys()):
            if len(actions[action_list[a]]) == 0:
                choices.append((a, action_list[a]))
        return choices

#------------------------------------------------------------------------------
# XML utilities
#------------------------------------------------------------------------------

def xml_parse_attr(elt, name):
    return elt.getAttribute(name)

def xml_parse_attr_bool(elt, name):
    attr = elt.getAttribute(name).lower()
    return attr in ("true", "yes", "on")

def xml_parse_string(elt):
    if elt.hasChildNodes():
        return elt.firstChild.nodeValue
    return ""

def xml_parse_bool(elt):
    val = elt.firstChild.nodeValue.lower()
    return val in ("true", "yes", "on")

def xml_find_nodes(elt, name):
    return [n for n in elt.childNodes if n.nodeName == name]

def xml_find_node(elt, name):
    nodes = xml_find_nodes(elt, name)
    return nodes[0] if len(nodes) == 1 else None


def fixed_writexml(self, writer, indent="", addindent="", newl=""):
    writer.write(indent + "<" + self.tagName)
    attrs = self._get_attributes()
    for a_name in sorted(attrs.keys()):
        writer.write(" %s=\"" % a_name)
        xml.dom.minidom._write_data(writer, attrs[a_name].value)
        writer.write("\"")
    if self.childNodes:
        if (len(self.childNodes) == 1
                and self.childNodes[0].nodeType == xml.dom.minidom.Node.TEXT_NODE):
            writer.write(">")
            self.childNodes[0].writexml(writer, "", "", "")
            writer.write("</%s>%s" % (self.tagName, newl))
            return
        writer.write(">%s" % newl)
        for node in self.childNodes:
            fixed_writexml(node, writer, indent + addindent, addindent, newl)
        writer.write("%s</%s>%s" % (indent, self.tagName, newl))
    else:
        writer.write("/>%s" % newl)


def fixed_toprettyxml(self, indent="", addindent="\t", newl="\n"):
    writer = StringIO()
    fixed_writexml(self, writer, indent, addindent, newl)
    return writer.getvalue()

#------------------------------------------------------------------------------
# Option Classes
#------------------------------------------------------------------------------

class OCString(object):
    __slots__ = ('name', 'default', 'alts')

    def __init__(self, name, default, alts=[]):
        self.name = name
        self.default = default
        self.alts = alts

    def apply_default(self, action):
        action.options[self.name] = self.default

    def parse(self, action, dom):
        node = xml_find_node(dom, self.name)
        if not node:
            for a in self.alts:
                node = xml_find_node(dom, a)
                if node:
                    break
        if node:
            action.options[self.name] = xml_parse_string(node)
        else:
            action.options[self.name] = self.default

    def deparse(self, action):
        val = action.options[self.name]
        if val == self.default:
            return None
        return xml.dom.minidom.parseString(
            "<" + str(self.name) + ">" + str(val) + "</" + str(self.name) + ">"
        ).documentElement

    def generate_widget(self, action, mark_dirty=None):
        def changed(entry, action):
            action.options[self.name] = entry.get_text()
            if mark_dirty:
                mark_dirty()
        entry = Gtk.Entry()
        entry.set_text(action.options[self.name])
        entry.connect('changed', changed, action)
        return entry


class OCCombo(object):
    __slots__ = ('name', 'default', 'choices')

    def __init__(self, name, default, choices):
        self.name = name
        self.default = default
        self.choices = choices

    def apply_default(self, action):
        action.options[self.name] = self.default

    def parse(self, action, dom):
        node = xml_find_node(dom, self.name)
        action.options[self.name] = xml_parse_string(node) if node else self.default

    def deparse(self, action):
        val = action.options[self.name]
        if val == self.default:
            return None
        return xml.dom.minidom.parseString(
            "<" + str(self.name) + ">" + str(val) + "</" + str(self.name) + ">"
        ).documentElement

    def generate_widget(self, action, mark_dirty=None):
        def changed(combo, action):
            action.options[self.name] = self.choices[combo.get_active()]
            if mark_dirty:
                mark_dirty()

        model = Gtk.ListStore(GObject.TYPE_STRING)
        for c in self.choices:
            model.append((_(c),))

        combo = Gtk.ComboBox()
        combo.set_active(self.choices.index(action.options[self.name]))
        combo.set_model(model)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        combo.connect('changed', changed, action)
        return combo


class OCNumber(object):
    __slots__ = ('name', 'default', 'min', 'max')

    def __init__(self, name, default, mmin, mmax):
        self.name = name
        self.default = default
        self.min = mmin
        self.max = mmax

    def apply_default(self, action):
        action.options[self.name] = self.default

    def parse(self, action, dom):
        node = xml_find_node(dom, self.name)
        action.options[self.name] = int(float(xml_parse_string(node))) if node else self.default

    def deparse(self, action):
        val = action.options[self.name]
        if val == self.default:
            return None
        return xml.dom.minidom.parseString(
            "<" + str(self.name) + ">" + str(val) + "</" + str(self.name) + ">"
        ).documentElement

    def generate_widget(self, action, mark_dirty=None):
        def changed(num, action):
            action.options[self.name] = num.get_value_as_int()
            if mark_dirty:
                mark_dirty()
        num = Gtk.SpinButton()
        num.set_increments(1, 5)
        num.set_range(self.min, self.max)
        num.set_value(action.options[self.name])
        num.connect('value-changed', changed, action)
        return num


class OCBoolean(object):
    __slots__ = ('name', 'default')

    def __init__(self, name, default):
        self.name = name
        self.default = default

    def apply_default(self, action):
        action.options[self.name] = self.default

    def parse(self, action, dom):
        node = xml_find_node(dom, self.name)
        action.options[self.name] = xml_parse_bool(node) if node else self.default

    def deparse(self, action):
        if action.options[self.name] == self.default:
            return None
        val = "yes" if action.options[self.name] else "no"
        return xml.dom.minidom.parseString(
            "<" + str(self.name) + ">" + val + "</" + str(self.name) + ">"
        ).documentElement

    def generate_widget(self, action, mark_dirty=None):
        def changed(checkbox, action):
            action.options[self.name] = checkbox.get_active()
            if mark_dirty:
                mark_dirty()
        check = Gtk.CheckButton()
        check.set_active(action.options[self.name])
        check.connect('toggled', changed, action)
        return check


class OCStartupNotify(object):
    def __init__(self):
        self.name = "startupnotify"

    def apply_default(self, action):
        action.options['startupnotify_enabled'] = False
        action.options['startupnotify_wmclass'] = ""
        action.options['startupnotify_name'] = ""
        action.options['startupnotify_icon'] = ""

    def parse(self, action, dom):
        self.apply_default(action)
        startupnotify = xml_find_node(dom, "startupnotify")
        if not startupnotify:
            return
        enabled = xml_find_node(startupnotify, "enabled")
        if enabled:
            action.options['startupnotify_enabled'] = xml_parse_bool(enabled)
        wmclass = xml_find_node(startupnotify, "wmclass")
        if wmclass:
            action.options['startupnotify_wmclass'] = xml_parse_string(wmclass)
        name = xml_find_node(startupnotify, "name")
        if name:
            action.options['startupnotify_name'] = xml_parse_string(name)
        icon = xml_find_node(startupnotify, "icon")
        if icon:
            action.options['startupnotify_icon'] = xml_parse_string(icon)

    def deparse(self, action):
        if not action.options['startupnotify_enabled']:
            return None
        root = xml.dom.minidom.parseString(
            "<startupnotify><enabled>yes</enabled></startupnotify>"
        ).documentElement
        for key, tag in [('startupnotify_wmclass', 'wmclass'),
                         ('startupnotify_name', 'name'),
                         ('startupnotify_icon', 'icon')]:
            if action.options[key]:
                root.appendChild(xml.dom.minidom.parseString(
                    "<" + tag + ">" + action.options[key] + "</" + tag + ">"
                ).documentElement)
        return root

    def generate_widget(self, action, mark_dirty=None):
        sens_list = []

        def enabled_toggled(checkbox, action, sens_list):
            active = checkbox.get_active()
            action.options['startupnotify_enabled'] = active
            for w in sens_list:
                w.set_sensitive(active)
            if mark_dirty:
                mark_dirty()

        def text_changed(textbox, action, var):
            action.options[var] = textbox.get_text()
            if mark_dirty:
                mark_dirty()

        wmclass = Gtk.Entry()
        wmclass.set_size_request(100, -1)
        wmclass.set_text(action.options['startupnotify_wmclass'])
        wmclass.connect('changed', text_changed, action, 'startupnotify_wmclass')

        name = Gtk.Entry()
        name.set_size_request(100, -1)
        name.set_text(action.options['startupnotify_name'])
        name.connect('changed', text_changed, action, 'startupnotify_name')

        icon = Gtk.Entry()
        icon.set_size_request(100, -1)
        icon.set_text(action.options['startupnotify_icon'])
        icon.connect('changed', text_changed, action, 'startupnotify_icon')

        sens_list = [wmclass, name, icon]

        enabled = Gtk.CheckButton()
        enabled.set_active(action.options['startupnotify_enabled'])
        enabled.connect('toggled', enabled_toggled, action, sens_list)

        def put_table(table, label_text, widget, row, addtosens=True):
            label = Gtk.Label(label=_(label_text))
            label.set_padding(5, 5)
            label.set_xalign(0)
            label.set_yalign(0)
            if addtosens:
                sens_list.append(label)
            table.attach(label, 0, 1, row, row + 1,
                         Gtk.AttachOptions.EXPAND | Gtk.AttachOptions.FILL, 0, 0, 0)
            table.attach(widget, 1, 2, row, row + 1, Gtk.AttachOptions.FILL, 0, 0, 0)

        table = Gtk.Table(1, 2)
        put_table(table, "enabled:", enabled, 0, False)
        put_table(table, "wmclass:", wmclass, 1)
        put_table(table, "name:", name, 2)
        put_table(table, "icon:", icon, 3)

        sens = enabled.get_active()
        for w in sens_list:
            w.set_sensitive(sens)

        frame = Gtk.Frame()
        frame.add(table)
        return frame


class OCFinalActions(object):
    __slots__ = ('name',)

    def __init__(self):
        self.name = "finalactions"

    def apply_default(self, action):
        a1, a2, a3 = OBAction(), OBAction(), OBAction()
        a1.mutate("Focus"); a2.mutate("Raise"); a3.mutate("Unshade")
        action.options[self.name] = [a1, a2, a3]

    def parse(self, action, dom):
        node = xml_find_node(dom, self.name)
        action.options[self.name] = []
        if node:
            for a in xml_find_nodes(node, "action"):
                act = OBAction()
                act.parse(a)
                action.options[self.name].append(act)
        else:
            self.apply_default(action)

    def deparse(self, action):
        a = action.options[self.name]
        if len(a) == 3:
            if a[0].name == "Focus" and a[1].name == "Raise" and a[2].name == "Unshade":
                return None
        if not a:
            return None
        root = xml.dom.minidom.parseString("<finalactions/>").documentElement
        for act in a:
            root.appendChild(act.deparse())
        return root

    def generate_widget(self, action, mark_dirty=None):
        w = MiniActionList(on_change=mark_dirty)
        w.set_actions(action.options[self.name])
        frame = Gtk.Frame()
        frame.add(w.widget)
        return frame

#------------------------------------------------------------------------------
# Action definitions
#------------------------------------------------------------------------------

actions = {
    "Execute": [
        OCString("command", "", ['execute']),
        OCString("prompt", ""),
        OCStartupNotify()
    ],
    "ShowMenu": [OCString("menu", "")],
    "NextWindow": [
        OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False),
        OCBoolean("allDesktops", False), OCBoolean("panels", False),
        OCBoolean("desktop", False), OCBoolean("linear", False), OCFinalActions()
    ],
    "PreviousWindow": [
        OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False),
        OCBoolean("allDesktops", False), OCBoolean("panels", False),
        OCBoolean("desktop", False), OCBoolean("linear", False), OCFinalActions()
    ],
    "DirectionalFocusNorth":     [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalFocusSouth":     [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalFocusEast":      [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalFocusWest":      [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalFocusNorthEast": [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalFocusNorthWest": [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalFocusSouthEast": [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalFocusSouthWest": [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetNorth":    [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetSouth":    [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetEast":     [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetWest":     [OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetNorthEast":[OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetNorthWest":[OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetSouthEast":[OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "DirectionalTargetSouthWest":[OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions()],
    "Desktop":             [OCNumber("desktop", 1, 1, 9999)],
    "DesktopNext":         [OCBoolean("wrap", True)],
    "DesktopPrevious":     [OCBoolean("wrap", True)],
    "DesktopLeft":         [OCBoolean("wrap", True)],
    "DesktopRight":        [OCBoolean("wrap", True)],
    "DesktopUp":           [OCBoolean("wrap", True)],
    "DesktopDown":         [OCBoolean("wrap", True)],
    "DesktopLast":         [],
    "AddDesktopLast":      [],
    "RemoveDesktopLast":   [],
    "AddDesktopCurrent":   [],
    "RemoveDesktopCurrent":[],
    "ToggleShowDesktop":   [],
    "ToggleDockAutohide":  [],
    "Reconfigure":         [],
    "Restart":             [OCString("command", "", ["execute"])],
    "Exit":                [OCBoolean("prompt", True)],
    "SessionLogout":       [OCBoolean("prompt", True)],
    "Debug":               [OCString("string", "")],
    "Focus":               [],
    "Raise":               [],
    "Lower":               [],
    "RaiseLower":          [],
    "Unfocus":             [],
    "FocusToBottom":       [],
    "Iconify":             [],
    "Close":               [],
    "ToggleShade":         [],
    "Shade":               [],
    "Unshade":             [],
    "ToggleOmnipresent":   [],
    "ToggleMaximizeFull":  [],
    "MaximizeFull":        [],
    "UnmaximizeFull":      [],
    "ToggleMaximizeVert":  [],
    "MaximizeVert":        [],
    "UnmaximizeVert":      [],
    "ToggleMaximizeHorz":  [],
    "MaximizeHorz":        [],
    "UnmaximizeHorz":      [],
    "ToggleFullscreen":    [],
    "ToggleDecorations":   [],
    "Decorate":            [],
    "Undecorate":          [],
    "SendToDesktop":       [OCNumber("desktop", 1, 1, 9999), OCBoolean("follow", True)],
    "SendToDesktopNext":   [OCBoolean("wrap", True), OCBoolean("follow", True)],
    "SendToDesktopPrevious":[OCBoolean("wrap", True), OCBoolean("follow", True)],
    "SendToDesktopLeft":   [OCBoolean("wrap", True), OCBoolean("follow", True)],
    "SendToDesktopRight":  [OCBoolean("wrap", True), OCBoolean("follow", True)],
    "SendToDesktopUp":     [OCBoolean("wrap", True), OCBoolean("follow", True)],
    "SendToDesktopDown":   [OCBoolean("wrap", True), OCBoolean("follow", True)],
    "Move":                [],
    "Resize":              [OCCombo("edge", "none", ['none', "top", "left", "right", "bottom",
                                                     "topleft", "topright", "bottomleft", "bottomright"])],
    "MoveToCenter":        [],
    "MoveResizeTo":        [OCString("x", "current"), OCString("y", "current"),
                            OCString("width", "current"), OCString("height", "current"),
                            OCString("monitor", "current")],
    "MoveRelative":        [OCNumber("x", 0, -9999, 9999), OCNumber("y", 0, -9999, 9999)],
    "ResizeRelative":      [OCNumber("left", 0, -9999, 9999), OCNumber("right", 0, -9999, 9999),
                            OCNumber("top", 0, -9999, 9999), OCNumber("bottom", 0, -9999, 9999)],
    "MoveToEdgeNorth":     [],
    "MoveToEdgeSouth":     [],
    "MoveToEdgeWest":      [],
    "MoveToEdgeEast":      [],
    "GrowToEdgeNorth":     [],
    "GrowToEdgeSouth":     [],
    "GrowToEdgeWest":      [],
    "GrowToEdgeEast":      [],
    "ShadeLower":          [],
    "UnshadeRaise":        [],
    "ToggleAlwaysOnTop":   [],
    "ToggleAlwaysOnBottom":[],
    "SendToTopLayer":      [],
    "SendToBottomLayer":   [],
    "SendToNormalLayer":   [],
    "BreakChroot":         [],
}

#------------------------------------------------------------------------------
# Config parsing
#------------------------------------------------------------------------------

class OBAction:
    def __init__(self, name=None):
        self.options = {}
        self.option_defs = []
        self.name = name
        if name:
            self.mutate(name)

    def parse(self, dom):
        if dom.hasChildNodes():
            for child in dom.childNodes:
                self.parseChild(child)
        self.name = xml_parse_attr(dom, "name")
        try:
            self.option_defs = actions[self.name]
        except KeyError:
            pass
        for od in self.option_defs:
            od.parse(self, dom)

    def parseChild(self, dom):
        try:
            if dom.hasChildNodes():
                for child in dom.childNodes:
                    try:
                        child.nodeValue = child.nodeValue.strip()
                    except AttributeError:
                        pass
                    self.parseChild(child)
        except AttributeError:
            pass
        else:
            try:
                dom.nodeValue = dom.nodeValue.strip()
            except AttributeError:
                pass

    def deparse(self):
        root = xml.dom.minidom.parseString(
            '<action name="' + str(self.name) + '"/>'
        ).documentElement
        for od in self.option_defs:
            od_node = od.deparse(self)
            if od_node:
                root.appendChild(od_node)
        return root

    def mutate(self, newtype):
        if hasattr(self, "option_defs") and actions[newtype] == self.option_defs:
            self.options = {}
            self.name = newtype
            return
        self.options = {}
        self.name = newtype
        self.option_defs = actions[self.name]
        for od in self.option_defs:
            od.apply_default(self)

    def __deepcopy__(self, memo):
        result = self.__class__()
        result.option_defs = self.option_defs
        result.options = copy.deepcopy(self.options, memo)
        result.name = copy.deepcopy(self.name, memo)
        return result


class OBKeyBind:
    def __init__(self, parent=None):
        self.children = []
        self.actions = []
        self.key = "a"
        self.chroot = False
        self.parent = parent

    def parse(self, dom):
        self.key = xml_parse_attr(dom, "key")
        self.chroot = xml_parse_attr_bool(dom, "chroot")
        kbinds = xml_find_nodes(dom, "keybind")
        if kbinds:
            for k in kbinds:
                kb = OBKeyBind(self)
                kb.parse(k)
                self.children.append(kb)
        else:
            for a in xml_find_nodes(dom, "action"):
                newa = OBAction()
                newa.parse(a)
                self.actions.append(newa)

    def deparse(self):
        if self.chroot:
            root = xml.dom.minidom.parseString(
                '<keybind key="' + str(self.key) + '" chroot="yes"/>'
            ).documentElement
        else:
            root = xml.dom.minidom.parseString(
                '<keybind key="' + str(self.key) + '"/>'
            ).documentElement
        if self.children:
            for k in self.children:
                root.appendChild(k.deparse())
        else:
            for a in self.actions:
                root.appendChild(a.deparse())
        return root

    def insert_empty_action(self, after=None):
        newact = OBAction()
        newact.mutate("Execute")
        if after:
            self.actions.insert(self.actions.index(after) + 1, newact)
        else:
            self.actions.append(newact)
        return newact

    def move_up(self, action):
        i = self.actions.index(action)
        self.actions[i - 1], self.actions[i] = action, self.actions[i - 1]

    def move_down(self, action):
        i = self.actions.index(action)
        self.actions[i + 1], self.actions[i] = action, self.actions[i + 1]


class OBKeyboard:
    def __init__(self, dom):
        self.chainQuitKey = None
        self.keybinds = []
        cqk = xml_find_node(dom, "chainQuitKey")
        if cqk:
            self.chainQuitKey = xml_parse_string(cqk)
        for keybind_node in xml_find_nodes(dom, "keybind"):
            kb = OBKeyBind()
            kb.parse(keybind_node)
            self.keybinds.append(kb)

    def deparse(self):
        root = xml.dom.minidom.parseString('<keyboard/>').documentElement
        chainQuitKey_node = xml.dom.minidom.parseString(
            '<chainQuitKey>' + str(self.chainQuitKey) + '</chainQuitKey>'
        ).documentElement
        root.appendChild(chainQuitKey_node)
        for k in self.keybinds:
            root.appendChild(k.deparse())
        return root


class OpenboxConfig:
    def __init__(self):
        self.dom = None
        self.keyboard = None
        self.path = None
        self.dirty = False

    def mark_dirty(self):
        self.dirty = True

    def load(self, path):
        self.path = path
        self.dom = xml.dom.minidom.parse(path)
        keyboard = xml_find_node(self.dom.documentElement, "keyboard")
        if keyboard:
            self.keyboard = OBKeyboard(keyboard)

    def save(self):
        if self.path is None:
            return
        keyboard = xml_find_node(self.dom.documentElement, "keyboard")
        newdom = xml_find_node(
            xml.dom.minidom.parseString(
                fixed_toprettyxml(self.keyboard.deparse(), "  ", "  ")
            ),
            "keyboard"
        )
        self.dom.documentElement.replaceChild(newdom, keyboard)
        with open(self.path, "wb") as f:
            f.write(self.dom.documentElement.toxml("utf-8"))
        self.dirty = False
        self.reconfigure_openbox()

    def reconfigure_openbox(self):
        os.system("openbox --reconfigure")
