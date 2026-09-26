"""Edición de parámetros de Tor en tiempo de ejecución y carga de configuración."""

import wx

from ..errors import show_error, show_message
from ..formatting import yes_no
from ..widgets import readonly_text, set_text_if_changed


class SetConfDialog(wx.Dialog):
    def __init__(self, parent, option_names, find_option, initial_name=None):
        super().__init__(parent, title='Establecer un parámetro de Tor', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._find_option = find_option

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label='&Parámetro:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.name = wx.ComboBox(self, choices=option_names, value=initial_name or '', style=wx.CB_DROPDOWN)
        sizer.Add(self.name, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Información del parámetro:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.info = readonly_text(self)
        self.info.SetMinSize((520, 110))
        sizer.Add(self.info, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Valores nuevos, uno por línea:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.values = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.HSCROLL)
        self.values.SetMinSize((520, 110))
        sizer.Add(self.values, 1, wx.EXPAND | wx.ALL, 8)
        note = wx.StaticText(self, label='Si deja los valores vacíos, el parámetro quedará sin valor. Para volver '
                                         'al valor predeterminado use «Restablecer al predeterminado». Los cambios '
                                         'se aplican de inmediato; para conservarlos al reiniciar Tor, guarde la '
                                         'configuración en disco.')
        note.Wrap(520)
        sizer.Add(note, 0, wx.ALL, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()

        self.name.Bind(wx.EVT_COMBOBOX, lambda event: self._update_info(prefill=True))
        self.name.Bind(wx.EVT_TEXT, lambda event: self._update_info(prefill=False))
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._update_info(prefill=True)
        (self.values if initial_name else self.name).SetFocus()

    def _update_info(self, prefill):
        option = self._find_option(self.name.GetValue().strip())
        if option is None:
            set_text_if_changed(self.info, 'Parámetro desconocido o sin información disponible.')
            return
        lines = ['Tipo: %s' % (option.type or 'desconocido'),
                 'Modificado respecto al predeterminado: %s' % yes_no(option.modified)]
        lines.append('Valor actual: %s' % (' | '.join(option.values) if option.values else 'sin valor'))
        lines.append('Valor predeterminado: %s' % (' | '.join(option.defaults) if option.defaults else 'sin valor'))
        if option.description:
            lines.append('Descripción: %s' % option.description)
        set_text_if_changed(self.info, '\n'.join(lines))
        if prefill:
            self.values.SetValue('\n'.join(option.values or []))

    def _on_ok(self, event):
        if not self.name.GetValue().strip():
            show_message(self, 'Indique el nombre del parámetro.', 'Falta el parámetro', wx.ICON_ERROR)
            self.name.SetFocus()
            return
        event.Skip()

    def get_result(self):
        values = [line.strip() for line in self.values.GetValue().splitlines() if line.strip()]
        return self.name.GetValue().strip(), values


class LoadConfDialog(wx.Dialog):
    def __init__(self, parent, current_text):
        super().__init__(parent, title='Cargar configuración en Tor (LOADCONF)',
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        warning = wx.StaticText(self, label='Tor sustituirá su configuración por este texto, como si hubiera leído '
                                            'un torrc nuevo. Las opciones que no aparezcan volverán a su valor '
                                            'predeterminado, salvo las indicadas en la línea de órdenes al '
                                            'iniciarlo. Si se conectó a un Tor existente, no elimine su '
                                            'ControlPort o perderá la conexión.')
        warning.Wrap(620)
        sizer.Add(warning, 0, wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Configuración en formato torrc:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.text = wx.TextCtrl(self, value=current_text, style=wx.TE_MULTILINE | wx.HSCROLL)
        self.text.SetMinSize((620, 300))
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        open_file = wx.Button(self, label='&Abrir un fichero torrc…')
        sizer.Add(open_file, 0, wx.LEFT | wx.RIGHT, 8)
        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.FindWindowById(wx.ID_OK).SetLabel('&Cargar en Tor')
        self.CentreOnParent()
        open_file.Bind(wx.EVT_BUTTON, self._on_open)
        self.text.SetFocus()

    def _on_open(self, event):
        with wx.FileDialog(self, 'Abrir un fichero de configuración de Tor',
                           wildcard='Todos los archivos (*.*)|*.*', style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = dialog.GetPath()
        try:
            with open(path, encoding='utf-8', errors='replace') as handle:
                self.text.SetValue(handle.read())
        except OSError as exc:
            show_error(self, exc, 'No se pudo abrir el fichero')
            return
        self.text.SetFocus()

    def get_text(self):
        return self.text.GetValue()
