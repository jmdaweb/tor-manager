"""Puente entre los eventos de Stem y la interfaz.

Stem ejecuta los listeners en su propio hilo lector. Aquí cada evento se
convierte en un modelo plano y se reenvía a la ventana principal como evento
wx con wx.CallAfter, de modo que ningún widget se toca fuera del hilo de wx.
"""

import logging
from datetime import datetime

import wx
import wx.lib.newevent
from stem.control import EventType, State

from .async_utils import call_after
from .models import BootstrapStatus
from .tor_backend import circuit_from_event, stream_from_event

log = logging.getLogger(__name__)

TorCircuitEvent, EVT_TOR_CIRCUIT = wx.lib.newevent.NewEvent()
TorStreamEvent, EVT_TOR_STREAM = wx.lib.newevent.NewEvent()
TorBandwidthEvent, EVT_TOR_BANDWIDTH = wx.lib.newevent.NewEvent()
TorLogEvent, EVT_TOR_LOG = wx.lib.newevent.NewEvent()
TorBootstrapEvent, EVT_TOR_BOOTSTRAP = wx.lib.newevent.NewEvent()
TorConfChangedEvent, EVT_TOR_CONF_CHANGED = wx.lib.newevent.NewEvent()
TorDisconnectedEvent, EVT_TOR_DISCONNECTED = wx.lib.newevent.NewEvent()

LOG_RUNLEVELS = ('ERR', 'WARN', 'NOTICE', 'INFO', 'DEBUG')

_CLIENT_STATUS_MESSAGES = {
    'CIRCUIT_ESTABLISHED': 'Tor puede establecer circuitos.',
    'CIRCUIT_NOT_ESTABLISHED': 'Tor no consigue establecer circuitos.',
    'ENOUGH_DIR_INFO': 'Tor tiene suficiente información del directorio.',
    'NOT_ENOUGH_DIR_INFO': 'Tor no tiene suficiente información del directorio.',
    'DANGEROUS_PORT': 'Una aplicación intentó conectar a un puerto considerado inseguro.',
    'DANGEROUS_SOCKS': 'Una aplicación usa un protocolo SOCKS que puede filtrar DNS.',
    'SOCKS_BAD_HOSTNAME': 'Una aplicación solicitó un nombre de máquina no válido.',
}


def log_events_for(level):
    """Tipos de evento de registro de Tor desde ERR hasta level."""
    index = LOG_RUNLEVELS.index(level) if level in LOG_RUNLEVELS else LOG_RUNLEVELS.index('NOTICE')
    return [getattr(EventType, name) for name in LOG_RUNLEVELS[:index + 1]]


class StemEventBridge:
    def __init__(self, backend, target):
        self._backend = backend
        self._target = target
        self._attached = False
        self._log_level = 'NOTICE'

    def attach(self, log_level='NOTICE'):
        """Se suscribe a los eventos de Tor. Llamar desde un hilo secundario."""
        self._attached = True
        subscriptions = (
            (self._on_circuit, EventType.CIRC),
            (self._on_stream, EventType.STREAM),
            (self._on_bandwidth, EventType.BW),
            (self._on_client_status, EventType.STATUS_CLIENT),
            (self._on_conf_changed, EventType.CONF_CHANGED),
            (self._on_signal, EventType.SIGNAL),
        )
        for listener, event_type in subscriptions:
            try:
                self._backend.add_event_listener(listener, event_type)
            except Exception as exc:
                log.warning('No se pudo suscribir al evento %s de Tor: %s', event_type, exc)
        self.set_log_level(log_level)
        self._backend.add_status_listener(self._on_controller_state)

    def set_log_level(self, level):
        """Cambia los niveles de registro recibidos. Llamar desde un hilo secundario."""
        self._log_level = level
        self._backend.remove_event_listener(self._on_log)
        self._backend.add_event_listener(self._on_log, *log_events_for(level))

    def detach(self):
        """Deja de entregar eventos. Solo se usa antes de cerrar la conexión, que
        ya elimina las suscripciones en Tor, así que no envía nada por la red."""
        if not self._attached:
            return
        self._attached = False
        try:
            self._backend.remove_status_listener(self._on_controller_state)
        except Exception:
            log.debug('Error al quitar el listener de estado', exc_info=True)

    # --- Entrega al hilo de wx -------------------------------------------------

    def _post(self, event):
        if self._attached:
            call_after(self._deliver, event)

    def _deliver(self, event):
        if self._attached and self._target:
            wx.PostEvent(self._target, event)

    def _post_log(self, runlevel, message):
        self._post(TorLogEvent(runlevel=runlevel, message=message, timestamp=datetime.now()))

    # --- Listeners (hilo lector de Stem) ------------------------------------------

    def _on_circuit(self, event):
        self._post(TorCircuitEvent(circuit=circuit_from_event(event)))

    def _on_stream(self, event):
        self._post(TorStreamEvent(stream=stream_from_event(event)))

    def _on_bandwidth(self, event):
        self._post(TorBandwidthEvent(read=event.read, written=event.written))

    def _on_log(self, event):
        self._post_log(str(event.runlevel), event.message)

    def _on_client_status(self, event):
        arguments = event.arguments or {}
        if event.action == 'BOOTSTRAP':
            self._post(TorBootstrapEvent(status=BootstrapStatus.from_arguments(arguments)))
            return
        message = _CLIENT_STATUS_MESSAGES.get(event.action, 'Estado del cliente: %s' % event.action)
        details = ' '.join('%s=%s' % item for item in arguments.items())
        self._post_log(str(event.runlevel), '%s %s' % (message, details) if details else message)

    def _on_conf_changed(self, event):
        changed = {key: list(values) for key, values in (event.changed or {}).items()}
        self._post(TorConfChangedEvent(changed=changed, unset=list(event.unset or [])))

    def _on_signal(self, event):
        self._post_log('NOTICE', 'Tor ha procesado la señal %s.' % event.signal)

    def _on_controller_state(self, controller, state, timestamp):
        if state == State.CLOSED:
            self._post(TorDisconnectedEvent())
