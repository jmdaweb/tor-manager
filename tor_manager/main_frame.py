"""Ventana principal: menús, pestañas, barra de estado y ciclo de vida de Tor."""

import logging

import wx

from . import APP_NAME, __version__
from . import constants as C
from .async_utils import run_in_thread
from .dialogs.circuit_dialogs import AttachStreamDialog, CircuitDialog
from .dialogs.config_dialogs import LoadConfDialog, SetConfDialog
from .dialogs.info_dialogs import GetInfoDialog, TextViewDialog
from .dialogs.onion_dialogs import OnionServiceCreateDialog, OnionServiceResultDialog
from .dialogs.relay_dialogs import RelayLookupDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.startup_dialog import StartupDialog
from .errors import confirm, short_description, show_error, show_message
from .exceptions import TorNotConnectedError
from .formatting import format_rate
from .icons import make_icon_bundle
from .models import ONION_EPHEMERAL, ONION_PERSISTENT
from .panels.circuits_panel import CircuitsPanel
from .panels.config_panel import ConfigPanel
from .panels.log_panel import LogPanel
from .panels.onion_services_panel import OnionServicesPanel
from .panels.streams_panel import StreamsPanel
from .taskbar import TorTaskBarIcon
from .tor_backend import STEM_VERSION
from .widgets import copy_to_clipboard
from .tor_events import (
    EVT_TOR_BANDWIDTH,
    EVT_TOR_BOOTSTRAP,
    EVT_TOR_CIRCUIT,
    EVT_TOR_CONF_CHANGED,
    EVT_TOR_DISCONNECTED,
    EVT_TOR_LOG,
    EVT_TOR_STREAM,
    StemEventBridge,
)

log = logging.getLogger(__name__)

# posiciones de los menús que requieren conexión con Tor
_TOR_MENUS = range(1, 6)


class MainFrame(wx.Frame):
    def __init__(self, backend, settings):
        super().__init__(None, title=APP_NAME, size=(1040, 740))
        self.backend = backend
        self.settings = settings
        self.bridge = None
        self._connected = False
        self._exit_requested = False
        self._exiting = False
        self._tray_notice_shown = False
        self._last_focus = None
        self._bootstrap_progress = None
        self._config_refresh = None

        self.SetIcons(make_icon_bundle(False))
        self._build_menu()
        self._build_body()
        self.CreateStatusBar(3)
        self.SetStatusWidths([-3, -2, -2])
        self.taskbar = TorTaskBarIcon(self)
        self._bind_events()
        self._set_connected(False)
        self.Centre()

    # --- Construcción --------------------------------------------------------

    def _build_menu(self):
        menubar = wx.MenuBar()

        def add_menu(title, entries):
            menu = wx.Menu()
            for entry in entries:
                if entry is None:
                    menu.AppendSeparator()
                elif entry[0] == 'check':
                    menu.AppendCheckItem(entry[1], entry[2])
                else:
                    menu.Append(entry[0], entry[1])
            menubar.Append(menu, title)

        add_menu('&Archivo', [
            (C.ID_CONNECT, '&Iniciar o conectar Tor…'),
            (C.ID_RESTART_TOR, '&Reiniciar Tor'),
            (C.ID_DISCONNECT, '&Detener Tor o desconectar'),
            None,
            (C.ID_SETTINGS, '&Ajustes…'),
            (C.ID_HIDE_TO_TRAY, '&Ocultar en la bandeja del sistema\tCtrl+H'),
            None,
            (wx.ID_EXIT, '&Salir\tCtrl+Q'),
        ])
        add_menu('&Circuitos', [
            (C.ID_NEW_CIRCUIT, '&Nuevo circuito…\tCtrl+N'),
            (C.ID_EXTEND_CIRCUIT, '&Extender circuito…'),
            (C.ID_REPURPOSE_CIRCUIT, 'Cambiar &propósito…'),
            None,
            (C.ID_CLOSE_CIRCUIT, '&Cerrar circuito'),
            (C.ID_CLOSE_CIRCUIT_IF_UNUSED, 'Cerrar si &no se usa'),
            None,
            (C.ID_REFRESH_CIRCUITS, '&Actualizar lista'),
        ])
        add_menu('S&treams', [
            (C.ID_ATTACH_STREAM, '&Asociar a un circuito…'),
            (C.ID_CLOSE_STREAM, '&Cerrar stream…'),
            None,
            ('check', C.ID_MANUAL_ATTACH, 'Asociar streams &manualmente'),
            None,
            (C.ID_REFRESH_STREAMS, 'Ac&tualizar lista'),
        ])
        add_menu('Servicios &onion', [
            (C.ID_ADD_EPHEMERAL, 'Añadir servicio &efímero…'),
            (C.ID_ADD_PERSISTENT, 'Añadir servicio &persistente…'),
            (C.ID_REMOVE_SERVICE, 'E&liminar servicio'),
            None,
            (C.ID_COPY_ADDRESS, '&Copiar dirección\tCtrl+Shift+C'),
            (C.ID_REFRESH_SERVICES, '&Actualizar lista'),
        ])
        add_menu('Co&nfiguración', [
            (C.ID_EDIT_OPTION, '&Establecer parámetro…\tCtrl+E'),
            (C.ID_RESET_OPTION, '&Restablecer parámetro al predeterminado'),
            None,
            (C.ID_SAVE_CONFIG, '&Guardar configuración en disco\tCtrl+S'),
            (C.ID_FACTORY_RESET, 'Restablecer valores de &fábrica…'),
            (C.ID_LOAD_TORRC, '&Cargar configuración (LOADCONF)…'),
            (C.ID_VIEW_CONFIG_TEXT, '&Ver configuración actual…'),
            None,
            (C.ID_REFRESH_CONFIG, 'Ac&tualizar lista'),
        ])
        add_menu('Co&ntrol', [
            (C.ID_NEW_IDENTITY, 'Nueva &identidad\tCtrl+I'),
            (C.ID_RELOAD, '&Recargar configuración (RELOAD)'),
            (C.ID_CLEAR_DNS, '&Vaciar la caché DNS'),
            None,
            (C.ID_DORMANT, 'Pasar a modo &latente (DORMANT)'),
            (C.ID_ACTIVE, 'Pasar a modo &activo (ACTIVE)'),
            (C.ID_HEARTBEAT, 'Registrar un &heartbeat'),
            (C.ID_DROP_GUARDS, '&Descartar los nodos guardia…'),
            None,
            (C.ID_GETINFO, 'Consultar in&formación (GETINFO)…\tCtrl+G'),
            (C.ID_RELAY_LOOKUP, 'Consultar un r&elé…\tCtrl+R'),
            (C.ID_REFRESH_INFO, 'Actualizar información &general'),
        ])
        add_menu('&Ver', [
            (C.ID_VIEW_CIRCUITS, '&Circuitos\tCtrl+1'),
            (C.ID_VIEW_STREAMS, '&Streams\tCtrl+2'),
            (C.ID_VIEW_SERVICES, 'Servicios &onion\tCtrl+3'),
            (C.ID_VIEW_CONFIG, 'Con&figuración\tCtrl+4'),
            (C.ID_VIEW_LOG, '&Información y registro\tCtrl+5'),
            None,
            (C.ID_REFRESH_CURRENT, '&Actualizar la pestaña actual\tF5'),
        ])
        add_menu('Ay&uda', [
            (wx.ID_ABOUT, '&Acerca de Tor Manager…'),
        ])
        self.SetMenuBar(menubar)

    def _build_body(self):
        root = wx.Panel(self)
        self.notebook = wx.Notebook(root)
        self.circuits_panel = CircuitsPanel(self.notebook)
        self.streams_panel = StreamsPanel(self.notebook)
        self.services_panel = OnionServicesPanel(self.notebook)
        self.config_panel = ConfigPanel(self.notebook)
        self.log_panel = LogPanel(self.notebook, self.settings.log_level)
        self._pages = [
            (self.circuits_panel, 'Circuitos'),
            (self.streams_panel, 'Streams'),
            (self.services_panel, 'Servicios onion'),
            (self.config_panel, 'Configuración'),
            (self.log_panel, 'Información y registro'),
        ]
        for panel, title in self._pages:
            self.notebook.AddPage(panel, title)

        self.circuits_panel.streams_provider = self.streams_panel.streams_for_circuit
        self.streams_panel.circuit_provider = self.circuits_panel.get_item
        self.log_panel.on_level_changed = self._on_log_level_changed

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        root.SetSizer(sizer)

    def _bind_events(self):
        handlers = {
            C.ID_CONNECT: lambda event: self._on_connect(),
            C.ID_RESTART_TOR: lambda event: self._on_restart(),
            C.ID_DISCONNECT: lambda event: self._on_disconnect(),
            C.ID_SETTINGS: self._on_settings,
            C.ID_HIDE_TO_TRAY: lambda event: self.hide_to_tray(),
            wx.ID_EXIT: lambda event: self.request_exit(),
            C.ID_NEW_CIRCUIT: self._on_new_circuit,
            C.ID_EXTEND_CIRCUIT: self._on_extend_circuit,
            C.ID_REPURPOSE_CIRCUIT: self._on_repurpose_circuit,
            C.ID_CLOSE_CIRCUIT: lambda event: self._close_circuit(False),
            C.ID_CLOSE_CIRCUIT_IF_UNUSED: lambda event: self._close_circuit(True),
            C.ID_REFRESH_CIRCUITS: lambda event: self.refresh_circuits(),
            C.ID_ATTACH_STREAM: self._on_attach_stream,
            C.ID_CLOSE_STREAM: self._on_close_stream,
            C.ID_MANUAL_ATTACH: self._on_manual_attach,
            C.ID_REFRESH_STREAMS: lambda event: self.refresh_streams(),
            C.ID_ADD_EPHEMERAL: lambda event: self._add_service(ONION_EPHEMERAL),
            C.ID_ADD_PERSISTENT: lambda event: self._add_service(ONION_PERSISTENT),
            C.ID_REMOVE_SERVICE: self._on_remove_service,
            C.ID_COPY_ADDRESS: self._on_copy_address,
            C.ID_REFRESH_SERVICES: lambda event: self.refresh_services(),
            C.ID_EDIT_OPTION: self._on_edit_option,
            C.ID_RESET_OPTION: self._on_reset_option,
            C.ID_SAVE_CONFIG: lambda event: self._save_config(False),
            C.ID_FACTORY_RESET: self._on_factory_reset,
            C.ID_LOAD_TORRC: self._on_load_torrc,
            C.ID_VIEW_CONFIG_TEXT: self._on_view_config_text,
            C.ID_REFRESH_CONFIG: lambda event: self.refresh_config(),
            C.ID_NEW_IDENTITY: lambda event: self.request_new_identity(),
            C.ID_RELOAD: lambda event: self._send_signal('RELOAD', 'Tor ha recargado su configuración.'),
            C.ID_CLEAR_DNS: lambda event: self._send_signal('CLEARDNSCACHE', 'Se ha vaciado la caché DNS de Tor.'),
            C.ID_DORMANT: lambda event: self._send_signal('DORMANT', 'Tor ha pasado a modo latente.'),
            C.ID_ACTIVE: lambda event: self._send_signal('ACTIVE', 'Tor ha pasado a modo activo.'),
            C.ID_HEARTBEAT: lambda event: self._send_signal(
                'HEARTBEAT', 'Tor ha escrito un heartbeat en su registro.'),
            C.ID_DROP_GUARDS: self._on_drop_guards,
            C.ID_GETINFO: lambda event: self._show_modal(GetInfoDialog(self, self.backend)),
            C.ID_RELAY_LOOKUP: lambda event: self._show_modal(RelayLookupDialog(self, self.backend)),
            C.ID_REFRESH_INFO: lambda event: self.refresh_info(),
            C.ID_VIEW_CIRCUITS: lambda event: self._select_page(self.circuits_panel),
            C.ID_VIEW_STREAMS: lambda event: self._select_page(self.streams_panel),
            C.ID_VIEW_SERVICES: lambda event: self._select_page(self.services_panel),
            C.ID_VIEW_CONFIG: lambda event: self._select_page(self.config_panel),
            C.ID_VIEW_LOG: lambda event: self._select_page(self.log_panel),
            C.ID_REFRESH_CURRENT: self._on_refresh_current,
            wx.ID_ABOUT: self._on_about,
        }
        for command_id, handler in handlers.items():
            self.Bind(wx.EVT_MENU, handler, id=command_id)
            self.Bind(wx.EVT_BUTTON, handler, id=command_id)

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ICONIZE, self._on_iconize)
        self.Bind(EVT_TOR_CIRCUIT, self._on_tor_circuit)
        self.Bind(EVT_TOR_STREAM, self._on_tor_stream)
        self.Bind(EVT_TOR_BANDWIDTH, self._on_tor_bandwidth)
        self.Bind(EVT_TOR_LOG, self._on_tor_log)
        self.Bind(EVT_TOR_BOOTSTRAP, self._on_tor_bootstrap)
        self.Bind(EVT_TOR_CONF_CHANGED, self._on_tor_conf_changed)
        self.Bind(EVT_TOR_DISCONNECTED, self._on_tor_disconnected)

    # --- Utilidades ------------------------------------------------------------

    def set_status(self, text):
        self.SetStatusText(text, 0)

    def app_log(self, message, level='NOTICE'):
        self.log_panel.append('Programa', level, message)

    def _show_modal(self, dialog):
        with dialog:
            dialog.ShowModal()

    def _select_page(self, panel):
        for index, (page, _title) in enumerate(self._pages):
            if page is panel:
                self.notebook.SetSelection(index)
                break

    def _require_selection(self, panel, message):
        item = panel.selected_item()
        if item is None:
            show_message(self, message, 'No hay nada seleccionado')
            self._select_page(panel)
            panel.list.SetFocus()
        return item

    def _run(self, function, *args, busy=None, done=None, on_success=None, quiet=False, error_title=None):
        """Ejecuta una llamada a Tor en segundo plano e informa en la barra de estado."""
        if busy:
            self.set_status(busy)

        def success(result):
            if done is not None:
                message = done(result) if callable(done) else done
                self.set_status(message)
                self.app_log(message)
            if on_success is not None:
                on_success(result)

        def failure(exc):
            if quiet:
                if self._connected and not isinstance(exc, TorNotConnectedError):
                    self.app_log(short_description(exc), 'WARN')
                return
            self.set_status(short_description(exc))
            show_error(self, exc, error_title)

        run_in_thread(function, *args, on_success=success, on_error=failure, owner=self)

    # --- Conexión con Tor --------------------------------------------------------

    def run_startup(self):
        """Muestra el diálogo de arranque. Devuelve True si hay conexión con Tor."""
        parent = self if self.IsShown() else None
        with StartupDialog(parent, self.backend, self.settings) as dialog:
            result = dialog.ShowModal()
            bootstrap = dialog.bootstrap_status
        if result != wx.ID_OK:
            return False
        self._on_connected(bootstrap)
        return True

    def _on_connected(self, bootstrap):
        self.bridge = StemEventBridge(self.backend, self)
        self._set_connected(True)
        self.set_status('Conectado a Tor.')
        self.app_log('Conectado a Tor.')
        if bootstrap is not None:
            self._show_bootstrap(bootstrap)
        run_in_thread(self.bridge.attach, self.settings.log_level,
                      on_success=lambda _: self.refresh_all(), on_error=self._on_attach_failed, owner=self)

    def _on_attach_failed(self, exc):
        self.app_log('No se pudo suscribir a los eventos de Tor: %s' % short_description(exc), 'WARN')
        self.refresh_all()

    def refresh_all(self):
        self.refresh_circuits()
        self.refresh_streams()
        self.refresh_services()
        self.refresh_config()
        self.refresh_info()
        self._run(self.backend.get_manual_stream_attachment, quiet=True,
                  on_success=lambda enabled: self.GetMenuBar().Check(C.ID_MANUAL_ATTACH, enabled))
        self._run(self.backend.get_bootstrap_status, quiet=True, on_success=self._show_bootstrap)

    def _set_connected(self, connected):
        self._connected = connected
        menubar = self.GetMenuBar()
        for position in _TOR_MENUS:
            menubar.EnableTop(position, connected)
        menubar.Enable(C.ID_CONNECT, not connected)
        menubar.Enable(C.ID_RESTART_TOR, connected)
        menubar.Enable(C.ID_DISCONNECT, connected)
        for panel in (self.circuits_panel, self.streams_panel, self.services_panel, self.config_panel):
            panel.Enable(connected)
        refresh_info = self.FindWindowById(C.ID_REFRESH_INFO, self.log_panel)
        if refresh_info is not None:
            refresh_info.Enable(connected)
        self.SetIcons(make_icon_bundle(connected))
        self._update_tray()

    def _update_tray(self):
        if not self._connected:
            status = 'sin conexión'
        elif self._bootstrap_progress is None:
            status = 'conectado'
        else:
            status = 'conectado, arranque al %d %%' % self._bootstrap_progress
        self.taskbar.update(self._connected, status)

    def _teardown_connection(self):
        if self.bridge is not None:
            self.bridge.detach()
            self.bridge = None
        self._bootstrap_progress = None
        self._set_connected(False)
        for panel in (self.circuits_panel, self.streams_panel, self.services_panel, self.config_panel):
            panel.clear()
        self.log_panel.set_info_text('Sin conexión con Tor.')
        self.SetStatusText('', 1)
        self.SetStatusText('', 2)

    def _stop_tor(self, then=None):
        self._teardown_connection()
        self.set_status('Deteniendo Tor…')

        def done(_result):
            self.set_status('Sin conexión con Tor.')
            self.app_log('Conexión con Tor cerrada.')
            if then is not None:
                then()

        run_in_thread(self.backend.shutdown, on_success=done, on_error=done, owner=self)

    def _on_connect(self):
        if not self._connected:
            self.run_startup()

    def _on_restart(self):
        question = ('¿Reiniciar Tor? Se cerrarán todos los circuitos y los servicios onion efímeros.'
                    if self.backend.owns_process else
                    '¿Cerrar la conexión con Tor y volver a conectar?')
        if confirm(self, question, 'Reiniciar Tor'):
            self._stop_tor(then=self.run_startup)

    def _on_disconnect(self):
        question = ('¿Detener Tor? Se cerrarán todas las conexiones que usan Tor.'
                    if self.backend.owns_process else
                    '¿Cerrar la conexión con Tor? El proceso de Tor seguirá en ejecución.')
        if confirm(self, question, 'Detener Tor'):
            self._stop_tor()

    def _on_tor_disconnected(self, event):
        if self._exiting or not self._connected:
            return
        self._teardown_connection()
        self.set_status('Se ha perdido la conexión con Tor.')
        self.app_log('Se ha perdido la conexión con Tor.', 'WARN')
        if not self.IsShown():
            self.taskbar.notify(APP_NAME, 'Se ha perdido la conexión con Tor.')

        def after_cleanup(_result):
            if self.IsShown() and confirm(self, 'Se ha perdido la conexión con Tor. ¿Desea iniciarlo o '
                                                'conectarse de nuevo?', 'Conexión perdida', default_no=False):
                self.run_startup()

        run_in_thread(self.backend.shutdown, 1.0, on_success=after_cleanup, on_error=after_cleanup, owner=self)

    # --- Bandeja del sistema y cierre -----------------------------------------------

    def hide_to_tray(self):
        focus = wx.Window.FindFocus()
        if focus is not None and focus.GetTopLevelParent() is self:
            self._last_focus = focus
        self.Hide()
        if not self._tray_notice_shown:
            self._tray_notice_shown = True
            self.taskbar.notify(APP_NAME, 'Tor Manager sigue en ejecución en la bandeja del sistema. '
                                          'Haga clic en su icono para mostrarlo.')

    def restore_from_tray(self):
        if self._exiting:
            return
        if self.IsIconized():
            self.Iconize(False)
        if not self.IsShown():
            self.Show()
        self.Raise()
        focus = self._last_focus
        if focus:
            focus.SetFocus()

    def _on_iconize(self, event):
        if event.IsIconized() and self.settings.minimize_to_tray and not self._exiting:
            wx.CallAfter(self.hide_to_tray)
        event.Skip()

    def request_exit(self):
        self._exit_requested = True
        self.Close()

    def exit_without_connection(self):
        """Cierra la aplicación cuando se cancela el arranque inicial."""
        self._exiting = True
        self.taskbar.RemoveIcon()
        self.taskbar.Destroy()
        self.Destroy()

    def _on_close(self, event):
        if event.CanVeto() and not self._exit_requested and self.settings.close_to_tray and not self._exiting:
            event.Veto()
            self.hide_to_tray()
            return
        if self._exiting:
            if event.CanVeto():
                event.Veto()
            return

        self._exiting = True
        self._teardown_connection()
        self.taskbar.RemoveIcon()
        self.taskbar.Destroy()

        if not event.CanVeto():
            # el sistema está cerrando la sesión: no se puede esperar a un hilo
            self.backend.shutdown(wait_timeout=2.0)
            self.Destroy()
            return

        event.Veto()
        self.Hide()
        finished = []

        def finish(_result=None):
            if finished:
                return
            finished.append(True)
            if self:
                self.Destroy()

        wx.CallLater(9000, finish)
        run_in_thread(self.backend.shutdown, on_success=finish, on_error=finish)

    # --- Eventos de Tor -------------------------------------------------------

    def _on_tor_circuit(self, event):
        self.circuits_panel.apply_event(event.circuit)
        self.streams_panel.refresh_detail()

    def _on_tor_stream(self, event):
        self.streams_panel.apply_event(event.stream)
        self.circuits_panel.refresh_detail()

    def _on_tor_bandwidth(self, event):
        self.SetStatusText('Descarga: %s, subida: %s' % (format_rate(event.read), format_rate(event.written)), 2)

    def _on_tor_log(self, event):
        self.log_panel.append('Tor', event.runlevel, event.message, event.timestamp)

    def _on_tor_bootstrap(self, event):
        previous = self._bootstrap_progress
        self._show_bootstrap(event.status)
        if event.status.progress >= 100 and (previous is None or previous < 100):
            self.app_log('Tor ha completado el arranque y está listo para usarse.')
            if not self.IsShown():
                self.taskbar.notify(APP_NAME, 'Tor está listo para usarse.')

    def _show_bootstrap(self, status):
        self._bootstrap_progress = status.progress
        text = 'Arranque: %d %% (%s)' % (status.progress, status.summary or status.tag)
        if status.warning:
            text += ', advertencia: %s' % status.warning
        self.SetStatusText(text, 1)
        self._update_tray()

    def _on_tor_conf_changed(self, event):
        changes = ['%s=%s' % (key, ', '.join(values)) for key, values in event.changed.items()]
        changes += ['%s sin valor' % key for key in event.unset]
        if changes:
            self.app_log('Configuración de Tor modificada: %s' % '; '.join(changes), 'INFO')
        self._schedule_config_refresh()

    def _schedule_config_refresh(self):
        if self._config_refresh is not None and self._config_refresh.IsRunning():
            self._config_refresh.Restart(1000)
        else:
            self._config_refresh = wx.CallLater(1000, self.refresh_config)

    def _on_log_level_changed(self, level):
        self.settings.log_level = level
        self._save_settings()
        if self.bridge is not None:
            self._run(self.bridge.set_log_level, level, quiet=True,
                      done='Nivel de detalle del registro de Tor cambiado.')

    # --- Actualizaciones ------------------------------------------------------

    def refresh_circuits(self):
        self._run(self.backend.get_circuits, quiet=True, on_success=self.circuits_panel.set_circuits)

    def refresh_streams(self):
        self._run(self.backend.get_streams, quiet=True, on_success=self.streams_panel.set_streams)

    def refresh_services(self):
        self._run(self.backend.list_onion_services, quiet=True, on_success=self.services_panel.set_services)

    def refresh_config(self):
        self._run(self.backend.get_config_options, quiet=True, on_success=self.config_panel.set_options)

    def refresh_info(self):
        self._run(self.backend.get_general_info, quiet=True, on_success=self.log_panel.set_info)

    def _on_refresh_current(self, event):
        page = self._pages[self.notebook.GetSelection()][0]
        if not self._connected:
            return
        {
            self.circuits_panel: self.refresh_circuits,
            self.streams_panel: self.refresh_streams,
            self.services_panel: self.refresh_services,
            self.config_panel: self.refresh_config,
            self.log_panel: self.refresh_info,
        }[page]()
        self.set_status('Lista actualizada.')

    # --- Circuitos -------------------------------------------------------------

    def _on_new_circuit(self, event):
        with CircuitDialog(self, self.backend) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path, purpose, wait = dialog.get_result()
        self._run(self.backend.new_circuit, path, purpose, wait,
                  busy='Construyendo el circuito…' if wait else 'Solicitando un circuito nuevo…',
                  done=lambda circuit_id: 'Circuito %s %s.' % (circuit_id, 'construido' if wait else 'solicitado'))

    def _on_extend_circuit(self, event):
        circuit = self._require_selection(self.circuits_panel, 'Seleccione en la lista el circuito que desea extender.')
        if circuit is None:
            return
        with CircuitDialog(self, self.backend, circuit) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path, _purpose, wait = dialog.get_result()
        self._run(self.backend.extend_circuit, circuit.id, path, wait,
                  busy='Extendiendo el circuito %s…' % circuit.id,
                  done=lambda circuit_id: 'Circuito %s extendido.' % circuit_id)

    def _on_repurpose_circuit(self, event):
        circuit = self._require_selection(self.circuits_panel, 'Seleccione en la lista un circuito.')
        if circuit is None:
            return
        choices = [text for _, text in C.CIRCUIT_PURPOSE_CHOICES]
        with wx.SingleChoiceDialog(self, 'Nuevo propósito para el circuito %s:' % circuit.id,
                                   'Cambiar el propósito del circuito', choices) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            purpose = C.CIRCUIT_PURPOSE_CHOICES[dialog.GetSelection()][0]
        self._run(self.backend.repurpose_circuit, circuit.id, purpose,
                  done='Propósito del circuito %s cambiado.' % circuit.id)

    def _close_circuit(self, if_unused):
        circuit = self._require_selection(self.circuits_panel, 'Seleccione en la lista el circuito que desea cerrar.')
        if circuit is None:
            return
        question = ('¿Cerrar el circuito %s cuando deje de usarse?' if if_unused else
                    '¿Cerrar el circuito %s? Se interrumpirán los streams que lo usan.') % circuit.id
        if not confirm(self, question, 'Cerrar circuito'):
            return
        self._run(self.backend.close_circuit, circuit.id, if_unused,
                  done='Se ha pedido el cierre del circuito %s.' % circuit.id)

    # --- Streams ---------------------------------------------------------------

    def _on_attach_stream(self, event):
        stream = self._require_selection(self.streams_panel, 'Seleccione en la lista el stream que desea asociar.')
        if stream is None:
            return
        circuits = self.circuits_panel.built_circuits()
        if not circuits:
            show_message(self, 'No hay circuitos construidos. Cree uno en la pestaña Circuitos.', 'Sin circuitos')
            return
        with AttachStreamDialog(self, stream, circuits) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            circuit_id, hop = dialog.get_result()
        self._run(self.backend.attach_stream, stream.id, circuit_id, hop,
                  done='Stream %s asociado al circuito %s.' % (stream.id, circuit_id))

    def _on_close_stream(self, event):
        stream = self._require_selection(self.streams_panel, 'Seleccione en la lista el stream que desea cerrar.')
        if stream is None:
            return
        with wx.SingleChoiceDialog(self, 'Motivo que se comunicará al cerrar el stream %s hacia %s:'
                                   % (stream.id, stream.target), 'Cerrar stream',
                                   [text for _, text in C.RELAY_END_REASONS]) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            reason = C.RELAY_END_REASONS[dialog.GetSelection()][0]
        self._run(self.backend.close_stream, stream.id, reason, done='Stream %s cerrado.' % stream.id)

    def _on_manual_attach(self, event):
        enabled = event.IsChecked()
        menubar = self.GetMenuBar()
        if enabled and not confirm(self, 'Con esta opción Tor deja de asociar automáticamente las conexiones '
                                         'nuevas: cada stream esperará a que usted lo asocie a un circuito en '
                                         'la pestaña Streams y, si no lo hace, fallará por tiempo agotado.\n\n'
                                         '¿Desea activarla?', 'Asociar streams manualmente'):
            menubar.Check(C.ID_MANUAL_ATTACH, False)
            return
        self._run(self.backend.set_manual_stream_attachment, enabled,
                  done='Asociación manual de streams %s.' % ('activada' if enabled else 'desactivada'))

    # --- Servicios onion -------------------------------------------------------

    def _add_service(self, kind):
        with OnionServiceCreateDialog(self, kind) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            spec = dialog.get_spec()
        if kind == ONION_EPHEMERAL:
            function = self.backend.create_ephemeral_service
            busy = ('Creando el servicio onion y esperando a que se publique…' if spec['await_publication']
                    else 'Creando el servicio onion…')
        else:
            function = self.backend.create_persistent_service
            busy = 'Creando el servicio onion persistente…'

        def created(result):
            self.refresh_services()
            with OnionServiceResultDialog(self, result) as result_dialog:
                result_dialog.ShowModal()

        self._run(lambda: function(**spec), busy=busy,
                  done=lambda result: 'Servicio onion creado: %s' % (result.address or 'dirección pendiente'),
                  on_success=created, error_title='No se pudo crear el servicio onion')

    def _on_remove_service(self, event):
        service = self._require_selection(self.services_panel, 'Seleccione en la lista el servicio que desea eliminar.')
        if service is None:
            return
        name = service.address or service.directory
        if service.kind == ONION_EPHEMERAL:
            if not confirm(self, '¿Eliminar el servicio onion efímero %s?' % name, 'Eliminar servicio'):
                return
            self._run(self.backend.remove_ephemeral_service, service.service_id,
                      done='Servicio %s eliminado.' % name, on_success=lambda _: self.refresh_services())
            return

        message = ('¿Eliminar el servicio onion persistente %s?\n\nSus claves permanecerán en %s por si desea '
                   'recuperarlo más adelante.\n\nPuede eliminarlo y guardar el cambio en el torrc, o eliminarlo '
                   'solo mientras Tor siga en ejecución.' % (name, service.directory))
        with wx.MessageDialog(self, message, 'Eliminar servicio', wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION) as dialog:
            dialog.SetYesNoCancelLabels('Eliminar y &guardar', 'Eliminar &solo ahora', '&Cancelar')
            answer = dialog.ShowModal()
        if answer == wx.ID_CANCEL:
            return
        self._run(self.backend.remove_persistent_service, service.directory, answer == wx.ID_YES,
                  done='Servicio %s eliminado.' % name, on_success=lambda _: self.refresh_services())

    def _on_copy_address(self, event):
        service = self._require_selection(self.services_panel, 'Seleccione en la lista un servicio onion.')
        if service is None:
            return
        if not service.address:
            show_message(self, 'La dirección de este servicio todavía no está disponible.', 'Copiar dirección')
            return
        if copy_to_clipboard(service.address):
            self.set_status('Dirección copiada: %s' % service.address)

    # --- Configuración ---------------------------------------------------------

    def _on_edit_option(self, event):
        selected = self.config_panel.selected_item()
        with SetConfDialog(self, self.config_panel.option_names(), self.config_panel.find_option,
                           selected.name if selected else None) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            name, values = dialog.get_result()
        self._run(self.backend.set_option, name, values, done='Parámetro %s establecido.' % name,
                  on_success=lambda _: self._schedule_config_refresh(),
                  error_title='No se pudo establecer %s' % name)

    def _on_reset_option(self, event):
        option = self._require_selection(self.config_panel, 'Seleccione en la lista el parámetro que desea restablecer.')
        if option is None:
            return
        if not confirm(self, '¿Restablecer %s a su valor predeterminado?' % option.name, 'Restablecer parámetro'):
            return
        self._run(self.backend.reset_option, option.name, done='Parámetro %s restablecido.' % option.name,
                  on_success=lambda _: self._schedule_config_refresh())

    def _save_config(self, force):
        def failed(exc):
            detail = getattr(exc, 'detail', '') or ''
            if not force and '%include' in detail and confirm(
                    self, 'El torrc usa %include y Tor no lo sobrescribe sin forzarlo. ¿Guardar de todos modos?',
                    'Guardar configuración'):
                self._save_config(True)
            else:
                self.set_status(short_description(exc))
                show_error(self, exc, 'No se pudo guardar la configuración')

        self.set_status('Guardando la configuración…')
        run_in_thread(self.backend.save_config, force, owner=self, on_error=failed,
                      on_success=lambda _: self._report('Configuración guardada en el torrc.'))

    def _report(self, message):
        self.set_status(message)
        self.app_log(message)

    def _on_factory_reset(self, event):
        if not confirm(self, 'Se restablecerán a su valor predeterminado todos los parámetros modificados, '
                             'excepto los que mantienen la conexión con Tor (puertos, directorio de datos, '
                             'autenticación y registro), y el resultado se guardará en el torrc.\n\nTambién se '
                             'eliminarán los servicios onion persistentes de la configuración (sus claves no se '
                             'borran).\n\n¿Desea continuar?', 'Restablecer valores de fábrica'):
            return

        def done(result):
            lines = ['Parámetros restablecidos: %d.' % len(result.reset)]
            if result.reset:
                lines.append(', '.join(result.reset))
            if result.failed:
                lines.append('')
                lines.append('No se pudieron restablecer:')
                lines.extend('  %s: %s' % item for item in result.failed)
            lines.append('')
            lines.append('Configuración guardada en el torrc.' if result.saved else
                         'No se pudo guardar en el torrc: %s' % result.save_error)
            self._schedule_config_refresh()
            self.refresh_services()
            show_message(self, '\n'.join(lines), 'Valores de fábrica restablecidos')

        self._run(self.backend.factory_reset, busy='Restableciendo la configuración…',
                  done='Configuración restablecida a los valores de fábrica.', on_success=done)

    def _on_load_torrc(self, event):
        def loaded_text(text):
            with LoadConfDialog(self, text) as dialog:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                new_text = dialog.get_text()
            self._run(self.backend.load_config_text, new_text, busy='Cargando la configuración…',
                      done='Configuración cargada en Tor.', on_success=lambda _: self._schedule_config_refresh(),
                      error_title='Tor no ha aceptado la configuración')

        self._run(self.backend.get_config_text, on_success=loaded_text)

    def _on_view_config_text(self, event):
        def show(text):
            self._show_modal(TextViewDialog(self, 'Configuración actual de Tor',
                                            '&Opciones distintas de las predeterminadas (config-text):',
                                            text or '(Tor usa la configuración predeterminada)',
                                            default_file='torrc-actual.txt'))

        self._run(self.backend.get_config_text, on_success=show)

    # --- Control ---------------------------------------------------------------

    def request_new_identity(self):
        if not self._connected:
            return

        def done(wait):
            if wait:
                message = 'Tor solo permite pedir una identidad nueva cada pocos segundos. Espere %.0f s.' % wait
                self.set_status(message)
                show_message(self, message, 'Nueva identidad')
            else:
                self._report('Nueva identidad solicitada: las conexiones nuevas usarán circuitos nuevos.')
                if not self.IsShown():
                    self.taskbar.notify(APP_NAME, 'Nueva identidad solicitada.')

        self._run(self.backend.new_identity, on_success=done)

    def _send_signal(self, name, message):
        self._run(self.backend.send_signal, name, done=message)

    def _on_drop_guards(self, event):
        if confirm(self, 'Tor olvidará sus nodos guardia y elegirá otros. Hacerlo sin motivo reduce el anonimato. '
                         '¿Desea continuar?', 'Descartar nodos guardia'):
            self._run(self.backend.drop_guards, done='Nodos guardia descartados.')

    # --- Otros -----------------------------------------------------------------

    def _on_settings(self, event):
        with SettingsDialog(self, self.settings) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            dialog.apply_to(self.settings)
        self._save_settings()
        self.set_status('Ajustes guardados.')

    def _save_settings(self):
        try:
            self.settings.save()
        except OSError as exc:
            show_error(self, exc, 'No se pudieron guardar los ajustes')

    def _on_about(self, event):
        show_message(self, '%s %s\n\nGestor accesible de Tor basado en Stem %s y wxPython %s.\n\n'
                           'Permite iniciar Tor o conectarse a uno existente, gestionar circuitos, streams y '
                           'servicios onion, y modificar la configuración en tiempo de ejecución.'
                     % (APP_NAME, __version__, STEM_VERSION, wx.version()), 'Acerca de %s' % APP_NAME)
