"""Visor de texto de solo lectura y consultas GETINFO."""

import wx

from ..async_utils import run_in_thread
from ..errors import short_description, show_error
from ..widgets import copy_to_clipboard, readonly_text, save_text_to_file


class TextViewDialog(wx.Dialog):
    def __init__(self, parent, title, label, text, default_file='tor.txt'):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._text = text
        self._default_file = default_file

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.view = readonly_text(self, value=text)
        self.view.SetMinSize((640, 380))
        sizer.Add(self.view, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy = wx.Button(self, label='&Copiar')
        save = wx.Button(self, label='&Guardar en un fichero…')
        buttons.Add(copy, 0, wx.RIGHT, 6)
        buttons.Add(save, 0)
        sizer.Add(buttons, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetEscapeId(wx.ID_CLOSE)
        self.CentreOnParent()

        copy.Bind(wx.EVT_BUTTON, lambda event: copy_to_clipboard(self._text))
        save.Bind(wx.EVT_BUTTON, self._on_save)
        self.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
        self.view.SetFocus()

    def _on_save(self, event):
        try:
            save_text_to_file(self, self._text, 'Guardar', default_file=self._default_file)
        except OSError as exc:
            show_error(self, exc, 'No se pudo guardar el fichero')


class GetInfoDialog(wx.Dialog):
    def __init__(self, parent, backend):
        super().__init__(parent, title='Consultar información de Tor (GETINFO)',
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.backend = backend
        self._descriptions = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label='&Clave que se consultará (las terminadas en «*» necesitan un '
                                            'argumento en lugar del asterisco):'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.key = wx.ComboBox(self, style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)
        row.Add(self.key, 1, wx.RIGHT, 6)
        query = wx.Button(self, label='Con&sultar')
        row.Add(query, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Descripción de la clave:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.description = readonly_text(self, multiline=False, value='Cargando la lista de claves…')
        sizer.Add(self.description, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Resultado:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.result = readonly_text(self)
        self.result.SetMinSize((680, 320))
        sizer.Add(self.result, 1, wx.EXPAND | wx.ALL, 8)
        copy = wx.Button(self, label='Co&piar el resultado')
        sizer.Add(copy, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetEscapeId(wx.ID_CLOSE)
        self.CentreOnParent()

        query.Bind(wx.EVT_BUTTON, self._on_query)
        self.key.Bind(wx.EVT_TEXT_ENTER, self._on_query)
        self.key.Bind(wx.EVT_COMBOBOX, self._on_key_changed)
        self.key.Bind(wx.EVT_TEXT, self._on_key_changed)
        copy.Bind(wx.EVT_BUTTON, lambda event: copy_to_clipboard(self.result.GetValue()))
        self.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
        self.key.SetFocus()

        run_in_thread(backend.get_info_names, on_success=self._on_names,
                      on_error=lambda exc: self.description.SetValue(short_description(exc)), owner=self)

    def _on_names(self, names):
        self._descriptions = dict(names)
        current = self.key.GetValue()
        self.key.Set([key for key, _ in names])
        self.key.SetValue(current)
        self.description.SetValue('%d claves disponibles. Elija una o escríbala.' % len(names))

    def _on_key_changed(self, event):
        description = self._descriptions.get(self.key.GetValue().strip())
        if description is not None:
            self.description.SetValue(description)
        event.Skip()

    def _on_query(self, event):
        key = self.key.GetValue().strip()
        if not key:
            return
        self.result.SetValue('Consultando %s…' % key)
        run_in_thread(self.backend.get_info_raw, key, on_success=self._show,
                      on_error=lambda exc: self._show(short_description(exc)), owner=self)

    def _show(self, text):
        self.result.SetValue(text if text else '(respuesta vacía)')
        self.result.SetFocus()
