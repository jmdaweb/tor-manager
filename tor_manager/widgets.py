"""Controles y utilidades de interfaz compartidos.

Para los lectores de pantalla en Windows, cada control se crea justo después
de su etiqueta (wx.StaticText): así el control toma la etiqueta como nombre
accesible.
"""

import wx

READONLY_MULTILINE = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2


def readonly_text(parent, multiline=True, value=''):
    style = READONLY_MULTILINE if multiline else wx.TE_READONLY
    return wx.TextCtrl(parent, value=value, style=style)


def add_labeled(parent, sizer, label, control_factory, proportion=0, flag=wx.EXPAND):
    """Crea una etiqueta y, a continuación, el control que describe."""
    sizer.Add(wx.StaticText(parent, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
    control = control_factory()
    sizer.Add(control, proportion, flag | wx.ALL, 6)
    return control


def add_labeled_row(parent, grid, label, control_factory):
    grid.Add(wx.StaticText(parent, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
    control = control_factory()
    grid.Add(control, 1, wx.EXPAND)
    return control


def copy_to_clipboard(text):
    if not wx.TheClipboard.Open():
        return False
    try:
        wx.TheClipboard.SetData(wx.TextDataObject(text))
        wx.TheClipboard.Flush()
    finally:
        wx.TheClipboard.Close()
    return True


def save_text_to_file(parent, text, title, default_file='', wildcard='Archivos de texto (*.txt)|*.txt|Todos los archivos (*.*)|*.*'):
    with wx.FileDialog(parent, title, defaultFile=default_file, wildcard=wildcard,
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        path = dialog.GetPath()
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return path


def set_text_if_changed(control, text):
    """Evita mover el cursor del lector de pantalla si el texto no cambia."""
    if control.GetValue() != text:
        control.SetValue(text)


class ListDetailPanel(wx.Panel):
    """Lista en modo informe con botones de acción y un cuadro de detalle de
    solo lectura que muestra la información completa del elemento elegido."""

    def __init__(self, parent, list_label, columns, detail_label, actions=(), activate_id=None,
                 delete_id=None, context_menu=()):
        super().__init__(parent)
        self._keys = []
        self._items = {}
        self._activate_id = activate_id
        self._delete_id = delete_id
        self._context_menu = context_menu

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.add_header_controls(self.sizer)

        self.sizer.Add(wx.StaticText(self, label=list_label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for index, (title, width) in enumerate(columns):
            self.list.InsertColumn(index, title, width=width)
        self.sizer.Add(self.list, 3, wx.EXPAND | wx.ALL, 6)

        if actions:
            buttons = wx.BoxSizer(wx.HORIZONTAL)
            for command_id, label in actions:
                buttons.Add(wx.Button(self, command_id, label), 0, wx.RIGHT, 6)
            self.sizer.Add(buttons, 0, wx.LEFT | wx.RIGHT, 6)

        self.sizer.Add(wx.StaticText(self, label=detail_label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        self.detail = readonly_text(self)
        self.sizer.Add(self.detail, 2, wx.EXPAND | wx.ALL, 6)
        self.SetSizer(self.sizer)

        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activated)
        self.list.Bind(wx.EVT_LIST_KEY_DOWN, self._on_key_down)
        self.list.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)

    # --- Para subclases ------------------------------------------------------

    def add_header_controls(self, sizer):
        pass

    def columns_for(self, item):
        raise NotImplementedError

    def format_detail(self, item):
        raise NotImplementedError

    # --- Contenido -----------------------------------------------------------

    def set_items(self, items):
        """items: lista de (clave, objeto). Conserva la selección si es posible."""
        selected = self.selected_key()
        self.list.Freeze()
        try:
            self.list.DeleteAllItems()
            self._keys = []
            self._items = {}
            for key, item in items:
                self._append_row(key, item)
        finally:
            self.list.Thaw()
        if selected in self._items:
            self.select(selected)
        self.refresh_detail()

    def upsert(self, key, item):
        if key in self._items:
            index = self._keys.index(key)
            self._items[key] = item
            for column, text in enumerate(self.columns_for(item)):
                if self.list.GetItemText(index, column) != text:
                    self.list.SetItem(index, column, text)
            if key == self.selected_key():
                self.refresh_detail()
        else:
            self._append_row(key, item)

    def remove(self, key):
        if key not in self._items:
            return
        index = self._keys.index(key)
        was_selected = key == self.selected_key()
        self.list.DeleteItem(index)
        del self._keys[index]
        del self._items[key]
        if was_selected and self._keys:
            self.select(self._keys[min(index, len(self._keys) - 1)])
        self.refresh_detail()

    def clear(self):
        self.set_items([])

    def _append_row(self, key, item):
        columns = self.columns_for(item)
        index = self.list.InsertItem(self.list.GetItemCount(), columns[0])
        for column, text in enumerate(columns[1:], start=1):
            self.list.SetItem(index, column, text)
        self._keys.append(key)
        self._items[key] = item

    def get_item(self, key):
        return self._items.get(key)

    def items(self):
        return [self._items[key] for key in self._keys]

    def selected_key(self):
        index = self.list.GetFirstSelected()
        if 0 <= index < len(self._keys):
            return self._keys[index]
        return None

    def selected_item(self):
        key = self.selected_key()
        return self._items.get(key) if key is not None else None

    def select(self, key):
        if key not in self._items:
            return
        index = self._keys.index(key)
        self.list.Select(index)
        self.list.Focus(index)
        self.list.EnsureVisible(index)

    def refresh_detail(self):
        item = self.selected_item()
        set_text_if_changed(self.detail, self.format_detail(item) if item is not None else self.empty_detail())

    def empty_detail(self):
        return 'No hay ningún elemento seleccionado.'

    # --- Eventos -------------------------------------------------------------

    def _on_selection_changed(self, event):
        self.refresh_detail()
        event.Skip()

    def _send_command(self, command_id):
        event = wx.CommandEvent(wx.wxEVT_MENU, command_id)
        event.SetEventObject(self)
        wx.PostEvent(self, event)

    def _on_activated(self, event):
        if self._activate_id is not None:
            self._send_command(self._activate_id)

    def _on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE and self._delete_id is not None:
            self._send_command(self._delete_id)
        else:
            event.Skip()

    def _on_context_menu(self, event):
        if not self._context_menu:
            return
        menu = wx.Menu()
        for entry in self._context_menu:
            if entry is None:
                menu.AppendSeparator()
            else:
                menu.Append(*entry)
        self.PopupMenu(menu)
        menu.Destroy()
