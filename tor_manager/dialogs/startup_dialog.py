"""Diálogo para iniciar Tor (incorporado o personalizado) o conectar con uno existente."""

import logging
import os
import re

import wx

from .. import paths, torrc
from ..async_utils import call_after, call_in_gui_and_wait, run_in_thread
from ..constants import AUTH_METHOD_LABELS
from ..errors import short_description, show_error, show_message
from ..exceptions import IncorrectPasswordError, LaunchCancelledError, PasswordRequiredError
from ..settings import (
    AUTH_AUTO,
    AUTH_COOKIE,
    AUTH_NONE,
    AUTH_PASSWORD,
    AUTH_SAFECOOKIE,
    LAUNCH_AUTH_PASSWORD,
    MODE_ATTACH,
    MODE_BUNDLED,
    MODE_CUSTOM,
)
from ..tor_backend import CONNECT_RETRY_SECONDS, hash_control_password
from ..widgets import readonly_text
from .auth_dialog import ask_password
from .settings_dialog import SettingsDialog

log = logging.getLogger(__name__)

AUTH_CHOICES = [
    (AUTH_AUTO, 'Automático: el mejor método que ofrezca Tor (recomendado)'),
    (AUTH_NONE, 'Sin autenticación'),
    (AUTH_PASSWORD, 'Contraseña'),
    (AUTH_COOKIE, 'Cookie'),
    (AUTH_SAFECOOKIE, 'SafeCookie (cookie con desafío)'),
]

_BOOTSTRAP_LINE = re.compile(r'Bootstrapped (\d+)%')

PHASE_IDLE = 'idle'
PHASE_BUSY = 'busy'
PHASE_BOOTSTRAPPING = 'bootstrapping'
PHASE_DONE = 'done'


class StartupDialog(wx.Dialog):
    def __init__(self, parent, backend, settings):
        super().__init__(parent, title='Iniciar Tor - Tor Manager',
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.backend = backend
        self.settings = settings
        self.bootstrap_status = None
        self._phase = PHASE_IDLE
        self._cancelled = False
        self._remember_password = False
        self._poll_in_flight = False
        self._last_bootstrap = None
        self._mode = settings.tor_mode

        self._build()
        self._load_from_settings()
        self._set_phase(PHASE_IDLE)

        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._poll_bootstrap, self._timer)
        self.Bind(wx.EVT_BUTTON, self._on_start, self.start_button)
        self.Bind(wx.EVT_BUTTON, lambda event: self._finish(wx.ID_OK), self.continue_button)
        self.Bind(wx.EVT_BUTTON, self._on_cancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self._on_cancel)
        self.Bind(wx.EVT_RADIOBUTTON, self._on_mode_changed)
        self.browse_button.Bind(wx.EVT_BUTTON, self._on_browse)
        self.settings_button.Bind(wx.EVT_BUTTON, self._on_settings)

        if settings.auto_start:
            wx.CallAfter(self._start)

    # --- Construcción --------------------------------------------------------

    def _build(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label='Elija cómo quiere usar Tor:'), 0, wx.ALL, 8)

        self.rb_bundled = wx.RadioButton(self, label='Iniciar el Tor inc&orporado en el programa', style=wx.RB_GROUP)
        sizer.Add(self.rb_bundled, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label='Ejecutable incorporado:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.bundled_info = readonly_text(self, multiline=False)
        sizer.Add(self.bundled_info, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.rb_custom = wx.RadioButton(self, label='Iniciar un ejecutable de Tor &personalizado')
        sizer.Add(self.rb_custom, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Ruta del e&jecutable:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.custom_path = wx.TextCtrl(self)
        row.Add(self.custom_path, 1, wx.RIGHT, 6)
        self.browse_button = wx.Button(self, label='&Examinar…')
        row.Add(self.browse_button, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)

        self.rb_attach = wx.RadioButton(self, label='Co&nectar a un Tor que ya está en ejecución')
        sizer.Add(self.rb_attach, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=6)
        grid.Add(wx.StaticText(self, label='&Dirección IP del puerto de control:'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.attach_address = wx.TextCtrl(self)
        grid.Add(self.attach_address, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self, label='Puer&to de control:'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.attach_port = wx.SpinCtrl(self, min=1, max=65535)
        grid.Add(self.attach_port, 0)
        sizer.Add(grid, 0, wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Método de a&utenticación:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.auth_choice = wx.Choice(self, choices=[text for _, text in AUTH_CHOICES])
        row.Add(self.auth_choice, 1, wx.RIGHT, 6)
        self.settings_button = wx.Button(self, label='Aju&stes avanzados…')
        row.Add(self.settings_button, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)

        sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label='Progreso del arranque de Tor:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.gauge = wx.Gauge(self, range=100)
        sizer.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='Estado:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.status = readonly_text(self, multiline=False, value='Preparado.')
        sizer.Add(self.status, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Mensajes de Tor:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.messages = readonly_text(self)
        self.messages.SetMinSize((560, 160))
        sizer.Add(self.messages, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.start_button = wx.Button(self, label='&Iniciar')
        self.start_button.SetDefault()
        buttons.Add(self.start_button, 0, wx.RIGHT, 6)
        self.continue_button = wx.Button(self, label='Continuar sin espe&rar')
        buttons.Add(self.continue_button, 0, wx.RIGHT, 6)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, '&Cancelar')
        buttons.Add(self.cancel_button, 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizerAndFit(sizer)
        self.SetMinSize(self.GetSize())
        self.CentreOnScreen()

    def _load_from_settings(self):
        bundled = paths.default_bundled_tor_path()
        if os.path.isfile(bundled):
            self.bundled_info.SetValue(bundled)
        else:
            self.bundled_info.SetValue('No encontrado. Copie el Tor Expert Bundle en %s (consulte LEEME.txt).'
                                       % os.path.dirname(bundled))
        self.custom_path.SetValue(self.settings.custom_tor_path)
        self.attach_address.SetValue(self.settings.attach_address)
        self.attach_port.SetValue(self.settings.attach_port)
        codes = [code for code, _ in AUTH_CHOICES]
        method = self.settings.auth_method
        self.auth_choice.SetSelection(codes.index(method) if method in codes else 0)
        {MODE_BUNDLED: self.rb_bundled, MODE_CUSTOM: self.rb_custom,
         MODE_ATTACH: self.rb_attach}.get(self._mode, self.rb_bundled).SetValue(True)

    def _selected_mode(self):
        if self.rb_custom.GetValue():
            return MODE_CUSTOM
        if self.rb_attach.GetValue():
            return MODE_ATTACH
        return MODE_BUNDLED

    def _set_phase(self, phase):
        self._phase = phase
        idle = phase == PHASE_IDLE
        mode = self._selected_mode()
        for control in (self.rb_bundled, self.rb_custom, self.rb_attach, self.auth_choice, self.settings_button):
            control.Enable(idle)
        self.custom_path.Enable(idle and mode == MODE_CUSTOM)
        self.browse_button.Enable(idle and mode == MODE_CUSTOM)
        self.attach_address.Enable(idle and mode == MODE_ATTACH)
        self.attach_port.Enable(idle and mode == MODE_ATTACH)
        self.start_button.Enable(idle)
        self.continue_button.Enable(phase == PHASE_BOOTSTRAPPING)
        self.cancel_button.Enable(phase != PHASE_DONE and not self._cancelled)

    # --- Utilidades de hilo ----------------------------------------------------

    def _gui(self, function, *args):
        """Programa function en el hilo de wx si el diálogo sigue existiendo."""
        call_after(lambda: function(*args) if self else None)

    def _append_message(self, text):
        self.messages.AppendText(text + '\n')

    def _set_status(self, text):
        self.status.SetValue(text)

    def _on_tor_output(self, line):
        self._gui(self._handle_tor_line, line)

    def _handle_tor_line(self, line):
        self._append_message(line)
        match = _BOOTSTRAP_LINE.search(line)
        if match:
            self.gauge.SetValue(min(100, int(match.group(1))))

    # --- Eventos de la interfaz --------------------------------------------------

    def _on_mode_changed(self, event):
        self._set_phase(self._phase)

    def _on_browse(self, event):
        wildcard = ('Ejecutable de Tor (tor.exe)|tor.exe|Programas (*.exe)|*.exe|Todos los archivos (*.*)|*.*'
                    if os.name == 'nt' else 'Todos los archivos (*)|*')
        current = self.custom_path.GetValue().strip()
        with wx.FileDialog(self, 'Seleccione el ejecutable de Tor', defaultDir=os.path.dirname(current),
                           wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.custom_path.SetValue(dialog.GetPath())
                self.custom_path.SetFocus()

    def _on_settings(self, event):
        with SettingsDialog(self, self.settings) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                dialog.apply_to(self.settings)
                self._save_settings()

    def _save_settings(self):
        try:
            self.settings.save()
        except OSError as exc:
            log.warning('No se pudieron guardar los ajustes: %s', exc)

    def _on_start(self, event):
        self._start()

    # --- Arranque ------------------------------------------------------------

    def _start(self):
        if self._phase != PHASE_IDLE:
            return
        mode = self._selected_mode()
        tor_executable = address = None
        port = None

        if mode == MODE_BUNDLED:
            tor_executable = paths.default_bundled_tor_path()
            if not os.path.isfile(tor_executable):
                show_message(self, 'No se encontró el Tor incorporado en:\n%s\n\nCopie allí el contenido del '
                                   'Tor Expert Bundle o elija un ejecutable personalizado.' % tor_executable,
                             'Tor no encontrado', wx.ICON_ERROR)
                return
        elif mode == MODE_CUSTOM:
            tor_executable = self.custom_path.GetValue().strip()
            if not tor_executable:
                show_message(self, 'Indique la ruta del ejecutable de Tor.', 'Falta el ejecutable', wx.ICON_ERROR)
                self.custom_path.SetFocus()
                return
            if os.path.dirname(tor_executable) and not os.path.isfile(tor_executable):
                show_message(self, 'No existe el fichero:\n%s' % tor_executable, 'Tor no encontrado', wx.ICON_ERROR)
                self.custom_path.SetFocus()
                return
        else:
            address = self.attach_address.GetValue().strip() or '127.0.0.1'
            if address.lower() == 'localhost':
                address = '127.0.0.1'
            port = self.attach_port.GetValue()

        auth_method = AUTH_CHOICES[self.auth_choice.GetSelection()][0]
        self.settings.tor_mode = mode
        self.settings.custom_tor_path = self.custom_path.GetValue().strip()
        self.settings.attach_address = self.attach_address.GetValue().strip() or '127.0.0.1'
        self.settings.attach_port = self.attach_port.GetValue()
        self.settings.auth_method = auth_method
        self._save_settings()

        password = self.settings.saved_password or None
        password_hash = None
        self._remember_password = False
        if mode != MODE_ATTACH and self.settings.launch_auth == LAUNCH_AUTH_PASSWORD:
            if not password:
                result = ask_password(self, 'Escriba la contraseña que protegerá el puerto de control del Tor '
                                            'que se va a iniciar.', require_value=True)
                if result is None:
                    return
                password, self._remember_password = result
            password_hash = hash_control_password(password)

        self._cancelled = False
        self._last_bootstrap = None
        self.bootstrap_status = None
        self.gauge.SetValue(0)
        self.messages.Clear()
        self.backend.reset_abort()
        self._set_phase(PHASE_BUSY)
        self._set_status('Iniciando Tor…' if mode != MODE_ATTACH else 'Conectando con Tor…')
        self.messages.SetFocus()
        run_in_thread(self._worker, mode, tor_executable, address, port, auth_method, password, password_hash,
                      on_success=self._on_worker_done, on_error=self._on_worker_failed, owner=self)

    def _worker(self, mode, tor_executable, address, port, auth_method, password, password_hash):
        """Se ejecuta en un hilo secundario."""
        backend = self.backend
        if mode != MODE_ATTACH:
            torrc_path = torrc.ensure_torrc()
            args = torrc.build_launch_args(self.settings, tor_executable, torrc_path, password_hash)
            self._gui(self._append_message, 'Iniciando %s' % tor_executable)
            self._gui(self._append_message, 'Fichero de configuración: %s' % torrc_path)
            backend.set_output_callback(self._on_tor_output)
            pid = backend.launch(tor_executable, torrc_path, args, init_msg_handler=self._on_tor_output)
            self._gui(self._set_status, 'Tor se está ejecutando (PID %s). Conectando con el puerto de control…' % pid)
            backend.connect('127.0.0.1', self.settings.control_port, retry_seconds=CONNECT_RETRY_SECONDS)
        else:
            self._gui(self._append_message, 'Conectando con %s:%s…' % (address, port))
            backend.connect(address, port)

        self._gui(self._set_status, 'Conectado. Autenticando…')
        info = backend.get_auth_info()
        methods = ', '.join(AUTH_METHOD_LABELS.get(method, method) for method in info.methods) or 'ninguno'
        self._gui(self._append_message, 'Tor %s ofrece estos métodos de autenticación: %s.'
                  % (info.tor_version or '', methods))

        while True:
            try:
                backend.authenticate(auth_method, password)
                break
            except (PasswordRequiredError, IncorrectPasswordError) as exc:
                answer = call_in_gui_and_wait(self._ask_password, isinstance(exc, IncorrectPasswordError))
                if answer is None:
                    raise LaunchCancelledError('Se canceló la autenticación.')
                password, self._remember_password = answer

        self._gui(self._append_message, 'Autenticación correcta.')
        return password

    def _ask_password(self, incorrect):
        if not self or self._cancelled:
            return None
        error = 'La contraseña no es correcta. Inténtelo de nuevo.' if incorrect else None
        return ask_password(self, 'Tor exige una contraseña para acceder a su puerto de control.', error=error)

    def _on_worker_done(self, password):
        if self._cancelled:
            return
        if self._remember_password and password:
            self.settings.saved_password = password
            self._save_settings()
        self._set_phase(PHASE_BOOTSTRAPPING)
        self._set_status('Conectado. Esperando a que Tor complete el arranque…')
        self.continue_button.SetFocus()
        self._poll_bootstrap()
        self._timer.Start(1000)

    def _on_worker_failed(self, exc):
        if self._cancelled:
            return
        if isinstance(exc, LaunchCancelledError):
            self._append_message(exc.message)
            self._set_status('Operación cancelada.')
        else:
            self._append_message('Error: %s' % short_description(exc))
            self._set_status('No se pudo iniciar o conectar Tor.')
            show_error(self, exc)
        self._stop_backend()

    def _stop_backend(self):
        self._timer.Stop()
        self._set_phase(PHASE_BUSY)
        self.cancel_button.Disable()
        run_in_thread(self.backend.shutdown, on_success=self._on_backend_stopped,
                      on_error=self._on_backend_stopped, owner=self)

    def _on_backend_stopped(self, _result):
        self._set_phase(PHASE_IDLE)
        self.start_button.SetFocus()

    # --- Progreso del arranque --------------------------------------------------

    def _poll_bootstrap(self, event=None):
        if self._poll_in_flight or self._phase != PHASE_BOOTSTRAPPING:
            return
        self._poll_in_flight = True
        run_in_thread(self.backend.get_bootstrap_status, on_success=self._on_bootstrap_status,
                      on_error=self._on_bootstrap_error, owner=self)

    def _on_bootstrap_status(self, status):
        self._poll_in_flight = False
        if self._phase != PHASE_BOOTSTRAPPING:
            return
        self.bootstrap_status = status
        self.gauge.SetValue(min(100, status.progress))
        text = 'Arranque de Tor: %d %% (%s)' % (status.progress, status.summary or status.tag)
        if status.warning:
            text += '. Advertencia: %s' % status.warning
        self._set_status(text)
        key = (status.progress, status.summary, status.warning)
        if key != self._last_bootstrap:
            self._last_bootstrap = key
            if not self.backend.owns_process:
                self._append_message(text)
        if status.progress >= 100:
            self._finish(wx.ID_OK)

    def _on_bootstrap_error(self, exc):
        self._poll_in_flight = False
        if self._phase == PHASE_BOOTSTRAPPING and not self._cancelled:
            self._on_worker_failed(exc)

    # --- Cierre --------------------------------------------------------------

    def _on_cancel(self, event):
        if self._phase == PHASE_IDLE:
            self._finish(wx.ID_CANCEL)
            return
        if self._phase == PHASE_DONE or self._cancelled or not self.cancel_button.IsEnabled():
            if isinstance(event, wx.CloseEvent) and event.CanVeto():
                event.Veto()
            return
        self._cancelled = True
        self._timer.Stop()
        self._set_phase(PHASE_BUSY)
        self._set_status('Cancelando…')
        self.backend.abort_launch()
        run_in_thread(self.backend.shutdown, on_success=lambda _: self._finish(wx.ID_CANCEL),
                      on_error=lambda _: self._finish(wx.ID_CANCEL), owner=self)

    def _finish(self, code):
        if self._phase == PHASE_DONE:
            return
        self._timer.Stop()
        self.backend.set_output_callback(None)
        self._set_phase(PHASE_DONE)
        if self.IsModal():
            self.EndModal(code)
