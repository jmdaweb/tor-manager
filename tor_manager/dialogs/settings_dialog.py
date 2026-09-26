import os

import wx

from .. import paths, torrc
from ..errors import confirm, show_error, show_message
from ..settings import LAUNCH_AUTH_COOKIE, LAUNCH_AUTH_NONE, LAUNCH_AUTH_PASSWORD, AppSettings

LAUNCH_AUTH_CHOICES = [
    (LAUNCH_AUTH_COOKIE, 'Cookie (recomendado)'),
    (LAUNCH_AUTH_PASSWORD, 'Contraseña'),
    (LAUNCH_AUTH_NONE, 'Sin autenticación (inseguro)'),
]


class SettingsDialog(wx.Dialog):
    def __init__(self, parent, settings):
        super().__init__(parent, title='Ajustes de Tor Manager', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._settings = settings
        self._forget_password = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        note = wx.StaticText(self, label='Los cambios de puertos, directorio de datos, autenticación y opciones '
                                         'de arranque se aplican la próxima vez que se inicie Tor.')
        note.Wrap(520)
        sizer.Add(note, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1)
        grid.Add(wx.StaticText(self, label='Puerto &SOCKS:'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.socks_port = wx.SpinCtrl(self, min=1, max=65535)
        grid.Add(self.socks_port, 0)
        grid.Add(wx.StaticText(self, label='Puerto de &control:'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.control_port = wx.SpinCtrl(self, min=1, max=65535)
        grid.Add(self.control_port, 0)
        grid.Add(wx.StaticText(self, label='&Directorio de datos:'), 0, wx.ALIGN_CENTER_VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.data_directory = wx.TextCtrl(self)
        row.Add(self.data_directory, 1, wx.RIGHT, 6)
        browse = wx.Button(self, label='E&xaminar…')
        row.Add(browse, 0)
        grid.Add(row, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, label='&Autenticación del Tor iniciado:'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.launch_auth = wx.Choice(self, choices=[text for _, text in LAUNCH_AUTH_CHOICES])
        grid.Add(self.launch_auth, 0)
        sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        sizer.Add(wx.StaticText(self, label='&Opciones adicionales de arranque, una por línea con el formato '
                                            '«Opción valor»:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.extra_options = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.HSCROLL, size=(-1, 110))
        sizer.Add(self.extra_options, 1, wx.EXPAND | wx.ALL, 10)

        self.minimize_to_tray = wx.CheckBox(self, label='&Minimizar a la bandeja del sistema al minimizar la ventana')
        sizer.Add(self.minimize_to_tray, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.close_to_tray = wx.CheckBox(self, label='Al cerrar la ventana, &ocultarla en la bandeja en lugar de salir')
        sizer.Add(self.close_to_tray, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.auto_start = wx.CheckBox(self, label='&Iniciar Tor automáticamente al abrir el programa')
        sizer.Add(self.auto_start, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.forget_button = wx.Button(self, label='Olvidar la contraseña &guardada')
        self.forget_button.Enable(bool(settings.saved_password))
        actions.Add(self.forget_button, 0, wx.RIGHT, 6)
        factory_torrc = wx.Button(self, label='Restablecer el &torrc de fábrica…')
        actions.Add(factory_torrc, 0, wx.RIGHT, 6)
        defaults = wx.Button(self, label='&Valores predeterminados')
        actions.Add(defaults, 0)
        sizer.Add(actions, 0, wx.LEFT | wx.RIGHT, 10)

        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(self.GetSize())
        self.CentreOnParent()

        browse.Bind(wx.EVT_BUTTON, self._on_browse)
        self.forget_button.Bind(wx.EVT_BUTTON, self._on_forget)
        factory_torrc.Bind(wx.EVT_BUTTON, self._on_factory_torrc)
        defaults.Bind(wx.EVT_BUTTON, lambda event: self._load(AppSettings()))
        self.launch_auth.Bind(wx.EVT_CHOICE, self._on_launch_auth)
        self._load(settings)
        self.socks_port.SetFocus()

    def _load(self, settings):
        self.socks_port.SetValue(settings.socks_port)
        self.control_port.SetValue(settings.control_port)
        self.data_directory.SetValue(settings.effective_data_directory())
        codes = [code for code, _ in LAUNCH_AUTH_CHOICES]
        self.launch_auth.SetSelection(codes.index(settings.launch_auth) if settings.launch_auth in codes else 0)
        self.extra_options.SetValue(settings.extra_options)
        self.minimize_to_tray.SetValue(settings.minimize_to_tray)
        self.close_to_tray.SetValue(settings.close_to_tray)
        self.auto_start.SetValue(settings.auto_start)

    def apply_to(self, settings):
        settings.socks_port = self.socks_port.GetValue()
        settings.control_port = self.control_port.GetValue()
        data_directory = self.data_directory.GetValue().strip()
        if not data_directory or os.path.normcase(os.path.abspath(data_directory)) == \
                os.path.normcase(paths.default_data_directory()):
            data_directory = ''
        settings.data_directory = data_directory
        previous_auth = settings.launch_auth
        settings.launch_auth = LAUNCH_AUTH_CHOICES[self.launch_auth.GetSelection()][0]
        if settings.launch_auth != previous_auth:
            settings.saved_password = ''
        settings.extra_options = self.extra_options.GetValue().strip()
        settings.minimize_to_tray = self.minimize_to_tray.IsChecked()
        settings.close_to_tray = self.close_to_tray.IsChecked()
        settings.auto_start = self.auto_start.IsChecked()
        if self._forget_password:
            settings.saved_password = ''

    def _on_browse(self, event):
        with wx.DirDialog(self, 'Elija el directorio de datos de Tor', self.data_directory.GetValue()) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.data_directory.SetValue(dialog.GetPath())

    def _on_forget(self, event):
        self._forget_password = True
        self.forget_button.Disable()
        self.launch_auth.SetFocus()
        show_message(self, 'La contraseña guardada se borrará al aceptar los ajustes.', 'Contraseña')

    def _on_launch_auth(self, event):
        if LAUNCH_AUTH_CHOICES[self.launch_auth.GetSelection()][0] == LAUNCH_AUTH_NONE:
            show_message(self, 'Sin autenticación, cualquier programa de este equipo podrá controlar Tor '
                               'a través del puerto de control.', 'Aviso de seguridad', wx.ICON_WARNING)

    def _on_factory_torrc(self, event):
        if not confirm(self, 'Se sobrescribirá el fichero torrc de Tor Manager con la configuración de fábrica '
                             'y se perderán los cambios guardados en él, incluidos los servicios onion '
                             'persistentes (sus claves no se borran).\n\n%s\n\n¿Desea continuar?'
                             % paths.torrc_file(), 'Restablecer el torrc'):
            return
        try:
            path = torrc.write_factory_torrc()
        except OSError as exc:
            show_error(self, exc, 'No se pudo escribir el torrc')
            return
        show_message(self, 'Se ha restablecido %s. Si Tor está en ejecución, reinícielo para aplicar '
                           'la configuración de fábrica.' % path, 'Torrc restablecido')
