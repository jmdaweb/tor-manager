"""Acceso a Tor mediante Stem.

Junto con tor_events es el único módulo que importa stem, y no depende de wx.
Todos los métodos públicos son síncronos (la interfaz los ejecuta en hilos
secundarios) y traducen las excepciones de Stem a las de exceptions.py.
"""

import atexit
import functools
import hashlib
import logging
import os
import queue
import subprocess
import threading
import time

import stem
import stem.connection
import stem.control
import stem.process
import stem.response
import stem.util.system
from stem.control import EventType, Listener

from .exceptions import (
    AuthenticationError,
    AuthMethodUnavailableError,
    CircuitExtensionError,
    CookieAuthError,
    IncorrectPasswordError,
    LaunchCancelledError,
    PasswordRequiredError,
    TorConnectionError,
    TorLaunchError,
    TorManagerError,
    TorNotConnectedError,
    TorRequestError,
    TorTimeoutError,
    UnsupportedFeatureError,
)
from .formatting import format_bytes, format_duration, format_rate, yes_no
from .models import (
    ONION_EPHEMERAL,
    ONION_PERSISTENT,
    AuthInfo,
    BootstrapStatus,
    CircuitInfo,
    ConfigOption,
    FactoryResetResult,
    OnionServiceCreated,
    OnionServiceInfo,
    RelayDetails,
    RelayInfo,
    StreamInfo,
)

log = logging.getLogger(__name__)
tor_output_log = logging.getLogger('tor_manager.tor_output')

STEM_VERSION = stem.__version__
CONNECT_RETRY_SECONDS = 20.0
CIRCUIT_BUILD_TIMEOUT = 60.0
PUBLICATION_TIMEOUT = 120.0

_AUTH_METHODS = {
    'none': stem.connection.AuthMethod.NONE,
    'password': stem.connection.AuthMethod.PASSWORD,
    'cookie': stem.connection.AuthMethod.COOKIE,
    'safecookie': stem.connection.AuthMethod.SAFECOOKIE,
}
_AUTH_METHOD_IDS = {value: key for key, value in _AUTH_METHODS.items()}

# opciones que mantienen la conexión con Tor; no se tocan al restablecer
PROTECTED_OPTIONS = frozenset(name.lower() for name in (
    'ControlPort', 'ControlSocket', 'SocksPort', 'DataDirectory', 'CookieAuthentication',
    'CookieAuthFile', 'CookieAuthFileGroupReadable', 'HashedControlPassword', 'Log',
    'GeoIPFile', 'GeoIPv6File',
))
_SKIPPED_CONFIG_TYPES = frozenset(('Virtual', 'Dependent', 'Obsolete'))


# --- Integración con el lanzador de Stem -----------------------------------

_launch_state = threading.local()


class _StemSubprocess:
    """Sustituye al módulo subprocess dentro de Stem.

    En Windows evita que tor.exe abra una ventana de consola (robaría el foco
    al lector de pantalla) y permite conocer el proceso mientras arranca para
    poder cancelarlo.
    """

    def __getattr__(self, name):
        return getattr(subprocess, name)

    @staticmethod
    def Popen(*args, **kwargs):
        if os.name == 'nt':
            kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
        process = subprocess.Popen(*args, **kwargs)
        callback = getattr(_launch_state, 'on_popen', None)
        if callback is not None:
            callback(process)
        return process


stem.process.subprocess = _StemSubprocess()
stem.util.system.subprocess = _StemSubprocess()

# Stem consulta platform.system(), que en Windows usa WMI (COM) la primera vez;
# se precalcula aquí, en el hilo principal, y no en un hilo secundario
stem.util.system.is_windows()


def hash_control_password(password):
    """Equivale a «tor --hash-password» (S2K iterado y con sal de RFC 2440)."""
    salt = os.urandom(8)
    indicator = 0x60
    count = (16 + (indicator & 15)) << ((indicator >> 4) + 6)
    data = salt + password.encode('utf-8')
    repeated = (data * (count // len(data) + 1))[:count]
    digest = hashlib.sha1(repeated).digest()
    return '16:' + (salt + bytes([indicator]) + digest).hex().upper()


def _escape_conf_value(value):
    # Stem envía los valores entre comillas sin escaparlos y Tor interpreta
    # las barras invertidas (por ejemplo, en rutas de Windows)
    return value.replace('\\', '\\\\').replace('"', '\\"')


# --- Conversión de objetos de Stem a modelos planos --------------------------

def _text(value):
    return None if value is None else str(value)


def circuit_from_event(event):
    return CircuitInfo(
        id=str(event.id),
        status=str(event.status or ''),
        purpose=str(event.purpose or ''),
        path=[(fingerprint or '', nickname or '') for fingerprint, nickname in (event.path or ())],
        build_flags=[str(flag) for flag in (event.build_flags or ())],
        created=event.created,
        reason=_text(event.reason),
        remote_reason=_text(event.remote_reason),
        hs_state=_text(event.hs_state),
        rend_query=_text(event.rend_query),
        socks_username=_text(getattr(event, 'socks_username', None)),
    )


def stream_from_event(event):
    circ_id = _text(event.circ_id)
    return StreamInfo(
        id=str(event.id),
        status=str(event.status or ''),
        circ_id=None if circ_id in (None, '0') else circ_id,
        target=str(event.target or ''),
        target_address=_text(event.target_address),
        target_port=event.target_port,
        purpose=_text(event.purpose),
        source_addr=_text(event.source_addr),
        reason=_text(event.reason),
        remote_reason=_text(event.remote_reason),
    )


def relay_from_entry(entry):
    version = getattr(entry, 'version', None)
    return RelayInfo(
        fingerprint=entry.fingerprint,
        nickname=entry.nickname,
        address=entry.address,
        or_port=entry.or_port,
        flags=sorted(str(flag) for flag in (entry.flags or ())),
        bandwidth=getattr(entry, 'bandwidth', None),
        version=str(version) if version else None,
        published=getattr(entry, 'published', None),
    )


# --- Traducción de excepciones ------------------------------------------------

def _translate_errors(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except TorManagerError:
            raise
        except stem.connection.MissingPassword as exc:
            raise PasswordRequiredError('Tor exige una contraseña para el puerto de control.', str(exc)) from exc
        except (stem.connection.IncorrectPassword, stem.connection.PasswordAuthRejected) as exc:
            raise IncorrectPasswordError('Tor ha rechazado la contraseña.', str(exc)) from exc
        except stem.connection.CookieAuthFailed as exc:
            raise CookieAuthError('No se pudo autenticar con el fichero de cookie de Tor.', str(exc),
                                  getattr(exc, 'cookie_path', None)) from exc
        except stem.connection.AuthenticationFailure as exc:
            raise AuthenticationError('La autenticación con Tor ha fallado.', str(exc)) from exc
        except stem.Timeout as exc:
            raise TorTimeoutError('Se agotó el tiempo de espera de la respuesta de Tor.', str(exc)) from exc
        except stem.CircuitExtensionFailed as exc:
            raise CircuitExtensionError('No se pudo construir o extender el circuito.', str(exc)) from exc
        except stem.DescriptorUnavailable as exc:
            raise TorRequestError('Tor no dispone de la información solicitada.', str(exc)) from exc
        except stem.UnsatisfiableRequest as exc:
            raise UnsupportedFeatureError('Tor no puede atender esta petición.', str(exc)) from exc
        except stem.SocketError as exc:
            raise TorConnectionError('Se ha perdido la conexión con el puerto de control de Tor.', str(exc)) from exc
        except stem.ControllerError as exc:
            raise TorRequestError('Tor ha rechazado la petición.', str(exc)) from exc
    return wrapper


def _translate_public_methods(cls):
    for name, value in list(vars(cls).items()):
        if not name.startswith('_') and callable(value):
            setattr(cls, name, _translate_errors(value))
    return cls


@_translate_public_methods
class TorBackend:
    def __init__(self):
        self._lock = threading.Lock()
        self._process = None
        self._controller = None
        self._owns_process = False
        self._launching_process = None
        self._abort_requested = False
        self._output_callback = None
        self._protocolinfo = None
        self._leave_streams_unattached = False
        self._ephemeral_registry = {}
        atexit.register(self._atexit_cleanup)

    # --- Estado ------------------------------------------------------------

    @property
    def is_connected(self):
        controller = self._controller
        return controller is not None and controller.is_alive() and controller.is_authenticated()

    @property
    def owns_process(self):
        return self._owns_process

    def _require_controller(self):
        controller = self._controller
        if controller is None or not controller.is_alive():
            raise TorNotConnectedError('No hay conexión con Tor.')
        return controller

    def set_output_callback(self, callback):
        """Recibe cada línea de la salida estándar de Tor (hilo secundario)."""
        self._output_callback = callback

    # --- Arranque, conexión y autenticación ----------------------------------

    def launch(self, tor_executable, torrc_path, args, init_msg_handler=None):
        """Inicia Tor con stem.process.launch_tor y devuelve su PID.

        Retorna en cuanto Tor informa del primer paso de arranque; el resto del
        progreso se sigue a través del puerto de control. No se pasa timeout
        porque Stem no lo admite en Windows.
        """
        _launch_state.on_popen = self._on_launch_popen
        try:
            process = stem.process.launch_tor(
                tor_cmd=tor_executable,
                args=args,
                torrc_path=torrc_path,
                completion_percent=0,
                init_msg_handler=init_msg_handler,
                take_ownership=True,
                close_output=False,
            )
        except OSError as exc:
            if self._abort_requested:
                raise LaunchCancelledError('Se canceló el arranque de Tor.') from exc
            raise TorLaunchError('No se pudo iniciar Tor.', str(exc)) from exc
        finally:
            _launch_state.on_popen = None
            self._launching_process = None

        with self._lock:
            aborted = self._abort_requested
            if not aborted:
                self._process = process
                self._owns_process = True
        if aborted:
            process.kill()
            process.wait()
            raise LaunchCancelledError('Se canceló el arranque de Tor.')
        self._start_output_readers(process)
        return process.pid

    def _on_launch_popen(self, process):
        with self._lock:
            self._launching_process = process
            aborted = self._abort_requested
        if aborted:
            process.kill()

    def reset_abort(self):
        """Prepara un nuevo intento de arranque o conexión."""
        with self._lock:
            self._abort_requested = False

    def abort_launch(self):
        with self._lock:
            self._abort_requested = True
            process = self._launching_process
        if process is not None and process.poll() is None:
            process.kill()

    def _start_output_readers(self, process):
        # mantener vaciadas las tuberías evita que Tor se bloquee al escribir
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                threading.Thread(target=self._read_output, args=(stream,),
                                 name='tor-output-reader', daemon=True).start()

    def _read_output(self, stream):
        try:
            for raw in iter(stream.readline, b''):
                line = raw.decode('utf-8', 'replace').rstrip()
                if not line:
                    continue
                tor_output_log.debug('%s', line)
                callback = self._output_callback
                if callback is not None:
                    try:
                        callback(line)
                    except Exception:
                        log.exception('Error al procesar la salida de Tor')
        except (OSError, ValueError):
            pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    def connect(self, address='127.0.0.1', port=9051, retry_seconds=0.0):
        deadline = time.monotonic() + retry_seconds
        while True:
            try:
                controller = stem.control.Controller.from_port(address=address, port=int(port))
                break
            except ValueError as exc:
                raise TorConnectionError('La dirección o el puerto de control no son válidos.', str(exc)) from exc
            except stem.SocketError as exc:
                if self._abort_requested:
                    raise LaunchCancelledError('Se canceló la conexión con Tor.') from exc
                process = self._process
                if process is not None and process.poll() is not None:
                    raise TorLaunchError('El proceso de Tor terminó de forma inesperada.', str(exc)) from exc
                if time.monotonic() >= deadline:
                    raise TorConnectionError(
                        'No se pudo conectar con el puerto de control %s:%s.' % (address, port), str(exc)) from exc
                time.sleep(0.5)

        with self._lock:
            previous, self._controller = self._controller, controller
            self._protocolinfo = None
        if previous is not None:
            previous.close()

    def get_auth_info(self):
        controller = self._require_controller()
        info = stem.connection.get_protocolinfo(controller)
        self._protocolinfo = info
        return AuthInfo(
            methods=[_AUTH_METHOD_IDS.get(method, 'unknown') for method in info.auth_methods],
            cookie_path=info.cookie_path,
            tor_version=str(info.tor_version) if info.tor_version else None,
        )

    def authenticate(self, method='auto', password=None):
        controller = self._require_controller()
        info = self._protocolinfo or stem.connection.get_protocolinfo(controller)

        if method == 'auto':
            stem.connection.authenticate(controller, password=password, protocolinfo_response=info)
            return

        required = _AUTH_METHODS[method]
        if required not in info.auth_methods:
            offered = ', '.join(str(item) for item in info.auth_methods) or 'ninguno'
            raise AuthMethodUnavailableError(
                'Tor no ofrece el método de autenticación elegido.', 'Métodos ofrecidos: %s' % offered)

        if method == 'none':
            stem.connection.authenticate_none(controller)
        elif method == 'password':
            if password is None:
                raise PasswordRequiredError('Tor exige una contraseña para el puerto de control.')
            stem.connection.authenticate_password(controller, password)
        elif method == 'cookie':
            stem.connection.authenticate_cookie(controller, info.cookie_path)
        elif method == 'safecookie':
            stem.connection.authenticate_safecookie(controller, info.cookie_path)

        # stem.connection.authenticate() hace esto por sí mismo, pero las funciones de
        # cada método no: sin ello Stem no activa los eventos ni envía TAKEOWNERSHIP
        controller._post_authentication()

    def shutdown(self, wait_timeout=5.0):
        """Cierra la conexión y, si Tor lo inició este programa, detiene Tor."""
        with self._lock:
            controller, self._controller = self._controller, None
            process, self._process = self._process, None
            owns, self._owns_process = self._owns_process, False
            leave_unattached, self._leave_streams_unattached = self._leave_streams_unattached, False
            self._protocolinfo = None
            self._ephemeral_registry.clear()
        self._output_callback = None

        deadline = time.monotonic() + wait_timeout
        signal_sent = False
        if controller is not None:
            try:
                if controller.is_alive() and controller.is_authenticated():
                    if owns and process is not None and process.poll() is None:
                        controller.signal(stem.Signal.SHUTDOWN)
                        signal_sent = True
                    elif not owns and leave_unattached:
                        controller.reset_conf('__LeaveStreamsUnattached')
            except (stem.ControllerError, OSError) as exc:
                log.debug('Error al pedir a Tor que se detenga: %s', exc)
            finally:
                try:
                    controller.close()
                except Exception:
                    log.debug('Error al cerrar el controlador', exc_info=True)

        if process is not None and process.poll() is None:
            if not signal_sent:
                process.terminate()
            self._wait_for_exit(process, deadline)

    @staticmethod
    def _wait_for_exit(process, deadline):
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
            return
        except subprocess.TimeoutExpired:
            log.warning('Tor no terminó a tiempo; se fuerza su cierre.')
        process.terminate()
        try:
            process.wait(timeout=2)
            return
        except subprocess.TimeoutExpired:
            pass
        process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            log.error('No se pudo detener el proceso de Tor (PID %s).', process.pid)

    def _atexit_cleanup(self):
        process = self._process
        if self._owns_process and process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    # --- Eventos -----------------------------------------------------------

    def add_event_listener(self, listener, *events):
        self._require_controller().add_event_listener(listener, *events)

    def remove_event_listener(self, listener):
        controller = self._controller
        if controller is not None:
            controller.remove_event_listener(listener)

    def add_status_listener(self, listener):
        self._require_controller().add_status_listener(listener)

    def remove_status_listener(self, listener):
        controller = self._controller
        if controller is not None:
            controller.remove_status_listener(listener)

    # --- Información general -------------------------------------------------

    def get_bootstrap_status(self):
        return BootstrapStatus.parse(self._require_controller().get_info('status/bootstrap-phase'))

    def get_version(self):
        return str(self._require_controller().get_version())

    def get_general_info(self):
        controller = self._require_controller()
        items = []

        def add(label, getter):
            try:
                value = getter()
            except (stem.ControllerError, ValueError, OSError) as exc:
                value = 'no disponible (%s)' % exc
            items.append((label, '' if value is None else str(value)))

        def uptime():
            seconds = controller.get_info('uptime', None)
            return format_duration(int(seconds)) if seconds else None

        def listeners(kind):
            found = controller.get_listeners(kind, [])
            return ', '.join('%s:%s' % (address, port) for address, port in found) or 'ninguna'

        def bootstrap():
            status = BootstrapStatus.parse(controller.get_info('status/bootstrap-phase'))
            return '%d %% (%s)' % (status.progress, status.summary or status.tag)

        def traffic(key):
            return format_bytes(int(controller.get_info(key)))

        def newnym():
            if controller.is_newnym_available():
                return 'disponible'
            return 'disponible dentro de %.0f s' % controller.get_newnym_wait()

        def accounting():
            if controller.get_info('accounting/enabled', '0') != '1':
                return 'desactivada'
            stats = controller.get_accounting_stats()
            return '%s; leído %s de %s; escrito %s de %s' % (
                stats.status, format_bytes(stats.read_bytes), format_bytes(stats.read_limit),
                format_bytes(stats.written_bytes), format_bytes(stats.write_limit))

        def auth_methods():
            info = self._protocolinfo
            if info is None:
                return None
            return ', '.join(_AUTH_METHOD_IDS.get(method, 'unknown') for method in info.auth_methods)

        def effective_rate():
            rate = controller.get_effective_rate(None)
            return format_rate(rate) if rate is not None else None

        add('Versión de Tor', lambda: controller.get_version())
        add('Proceso iniciado por Tor Manager', lambda: yes_no(self._owns_process))
        add('PID del proceso de Tor', lambda: controller.get_pid(None))
        add('Tiempo en funcionamiento', uptime)
        add('Estado del arranque', bootstrap)
        add('Circuito establecido', lambda: yes_no(controller.get_info('status/circuit-established', '0') == '1'))
        add('Estado de la red', lambda: controller.get_info('network-liveness', None))
        add('Modo latente', lambda: yes_no(controller.get_info('dormant', '0') == '1'))
        add('Nueva identidad', newnym)
        add('Dirección IP externa', lambda: controller.get_info('address', None) or 'desconocida')
        add('Huella digital (solo relés)', lambda: controller.get_info('fingerprint', None) or 'no es un relé')
        add('Escuchas SOCKS', lambda: listeners(Listener.SOCKS))
        add('Escuchas de control', lambda: listeners(Listener.CONTROL))
        add('Tráfico leído', lambda: traffic('traffic/read'))
        add('Tráfico escrito', lambda: traffic('traffic/written'))
        add('Tasa efectiva de ancho de banda', effective_rate)
        add('Contabilidad de tráfico', accounting)
        add('Base de datos GeoIP', lambda: 'no disponible' if controller.is_geoip_unavailable() else 'disponible')
        add('Métodos de autenticación ofrecidos', auth_methods)
        add('Fichero torrc', lambda: controller.get_info('config-file', None))
        add('Directorio de datos', lambda: controller.get_conf('DataDirectory', None))
        return items

    def get_info_names(self):
        text = self._require_controller().get_info('info/names')
        names = []
        for line in text.splitlines():
            key, _, description = line.partition(' -- ')
            if key.strip():
                names.append((key.strip(), description.strip()))
        return names

    def get_info_raw(self, key):
        return self._require_controller().get_info(key.strip())

    # --- Circuitos ---------------------------------------------------------

    def get_circuits(self):
        return [circuit_from_event(event) for event in self._require_controller().get_circuits()]

    def new_circuit(self, path=None, purpose='general', await_build=False):
        controller = self._require_controller()
        return controller.new_circuit(path or None, purpose, await_build,
                                      CIRCUIT_BUILD_TIMEOUT if await_build else None)

    def extend_circuit(self, circuit_id, path, await_build=False):
        controller = self._require_controller()
        return controller.extend_circuit(circuit_id, path, 'general', await_build,
                                         CIRCUIT_BUILD_TIMEOUT if await_build else None)

    def repurpose_circuit(self, circuit_id, purpose):
        self._require_controller().repurpose_circuit(circuit_id, purpose)

    def close_circuit(self, circuit_id, if_unused=False):
        self._require_controller().close_circuit(circuit_id, 'IfUnused' if if_unused else '')

    # --- Streams -----------------------------------------------------------

    def get_streams(self):
        return [stream_from_event(event) for event in self._require_controller().get_streams()]

    def attach_stream(self, stream_id, circuit_id, exiting_hop=None):
        self._require_controller().attach_stream(stream_id, circuit_id, exiting_hop)

    def close_stream(self, stream_id, reason='MISC'):
        self._require_controller().close_stream(stream_id, reason)

    def get_manual_stream_attachment(self):
        return self._require_controller().get_conf('__LeaveStreamsUnattached', '0') == '1'

    def set_manual_stream_attachment(self, enabled):
        self._require_controller().set_conf('__LeaveStreamsUnattached', '1' if enabled else '0')
        self._leave_streams_unattached = enabled

    # --- Relés -------------------------------------------------------------

    def get_relays(self):
        return [relay_from_entry(entry) for entry in self._require_controller().get_network_statuses()]

    def describe_relay(self, query):
        controller = self._require_controller()
        query = query.strip().lstrip('$')
        entry = controller.get_network_status(query, None)
        if entry is None:
            raise TorRequestError('No se encontró ningún relé que coincida con «%s».' % query)
        micro = controller.get_microdescriptor(entry.fingerprint, None)
        exit_policy = None
        if micro is not None and getattr(micro, 'exit_policy', None) is not None:
            exit_policy = str(micro.exit_policy)
        return RelayDetails(
            relay=relay_from_entry(entry),
            network_status_text=str(entry).strip(),
            microdescriptor_text=str(micro).strip() if micro is not None else None,
            exit_policy=exit_policy,
        )

    # --- Señales y otras órdenes ---------------------------------------------

    def send_signal(self, name):
        self._require_controller().signal(getattr(stem.Signal, name))

    def new_identity(self):
        """Devuelve 0 si se envió NEWNYM, o los segundos que faltan para poder hacerlo."""
        controller = self._require_controller()
        if not controller.is_newnym_available():
            return max(0.0, controller.get_newnym_wait())
        controller.signal(stem.Signal.NEWNYM)
        return 0.0

    def drop_guards(self):
        self._require_controller().drop_guards()

    # --- Configuración -------------------------------------------------------

    def get_config_options(self):
        controller = self._require_controller()
        names, types, descriptions = [], {}, {}
        for line in controller.get_info('config/names').splitlines():
            parts = line.strip().split(' ', 2)
            if not parts or not parts[0]:
                continue
            name = parts[0]
            option_type = parts[1] if len(parts) > 1 else ''
            if option_type in _SKIPPED_CONFIG_TYPES or name.startswith('__'):
                continue
            names.append(name)
            types[name] = option_type
            descriptions[name] = parts[2].strip() if len(parts) > 2 else ''

        defaults = {}
        for line in controller.get_info('config/defaults', '').splitlines():
            key, _, value = line.partition(' ')
            if key:
                defaults.setdefault(key.lower(), []).append(value)

        custom = self._custom_option_names(controller)
        values = self._get_conf_values(controller, names)
        return [
            ConfigOption(
                name=name,
                type=types[name],
                values=values.get(name),
                defaults=defaults.get(name.lower(), []),
                modified=name.lower() in custom,
                description=descriptions[name],
            )
            for name in names
        ]

    @staticmethod
    def _custom_option_names(controller):
        names = set()
        for line in controller.get_info('config-text', '').splitlines():
            key = line.strip().partition(' ')[0]
            if key and not key.startswith('#'):
                names.add(key.lower())
        return names

    @staticmethod
    def _get_conf_values(controller, names):
        try:
            return {key: list(value) for key, value in controller.get_conf_map(names, multiple=True).items()}
        except stem.ControllerError:
            log.debug('GETCONF conjunto fallido; se consultan las opciones por separado', exc_info=True)
        values = {}
        for name in names:
            try:
                values[name] = list(controller.get_conf(name, multiple=True))
            except stem.ControllerError:
                values[name] = None
        return values

    def get_option_values(self, name):
        return list(self._require_controller().get_conf(name, multiple=True))

    def set_option(self, name, values):
        """values vacío anula la opción (SETCONF sin valor)."""
        escaped = [_escape_conf_value(value) for value in values] if values else None
        self._require_controller().set_options([(name, escaped)])

    def reset_option(self, name):
        self._require_controller().reset_conf(name)

    def get_config_text(self):
        return self._require_controller().get_info('config-text', '')

    def load_config_text(self, text):
        self._require_controller().load_conf(text)

    def save_config(self, force=False):
        self._require_controller().save_conf(force)

    def factory_reset(self):
        """Restablece a su valor predeterminado cada opción cambiada, salvo las
        que mantienen la conexión, y guarda el resultado en el torrc."""
        controller = self._require_controller()
        names = []
        for line in controller.get_info('config-text', '').splitlines():
            key = line.strip().partition(' ')[0]
            if key and not key.startswith('#') and not key.startswith('__') \
                    and key.lower() not in PROTECTED_OPTIONS and key not in names:
                names.append(key)

        failed = []
        if names:
            try:
                controller.set_options([(name, None) for name in names], reset=True)
            except stem.ControllerError:
                for name in names:
                    try:
                        controller.reset_conf(name)
                    except stem.ControllerError as exc:
                        failed.append((name, str(exc)))
        controller.clear_cache()

        try:
            controller.save_conf()
        except stem.ControllerError as exc:
            return FactoryResetResult(names, failed, False, str(exc))
        return FactoryResetResult(names, failed, True)

    # --- Servicios onion -----------------------------------------------------

    def list_onion_services(self):
        controller = self._require_controller()
        services = []
        own = controller.list_ephemeral_hidden_services(our_services=True, detached=False)
        detached = controller.list_ephemeral_hidden_services(our_services=False, detached=True)
        seen = set()
        for service_id, is_detached in [(item, False) for item in own] + [(item, True) for item in detached]:
            if service_id in seen:
                continue
            seen.add(service_id)
            meta = self._ephemeral_registry.get(service_id, {})
            services.append(OnionServiceInfo(
                kind=ONION_EPHEMERAL,
                address=service_id + '.onion',
                service_id=service_id,
                ports=list(meta.get('ports', [])),
                detached=is_detached,
                created_here=bool(meta),
                key_type=meta.get('key_type'),
            ))

        for directory, conf in self._hidden_service_conf(controller).items():
            hostname = self._read_hostname(controller, directory)
            services.append(OnionServiceInfo(
                kind=ONION_PERSISTENT,
                address=hostname,
                service_id=hostname[:-len('.onion')] if hostname and hostname.endswith('.onion') else None,
                ports=conf['ports'],
                directory=directory,
                options=conf['options'],
            ))
        return services

    @staticmethod
    def _hidden_service_conf(controller):
        result = {}
        try:
            conf = controller.get_hidden_service_conf()
        except stem.ProtocolError:
            # Stem solo entiende destinos IPv4; se interpreta la respuesta a mano
            return TorBackend._raw_hidden_service_conf(controller)
        for directory, options in conf.items():
            ports = [(int(port), '%s:%s' % (address, target_port))
                     for port, address, target_port in options.get('HiddenServicePort', [])]
            result[directory] = {
                'ports': ports,
                'options': {key: value for key, value in options.items() if key != 'HiddenServicePort'},
            }
        return result

    @staticmethod
    def _raw_hidden_service_conf(controller):
        response = controller.msg('GETCONF HiddenServiceOptions')
        result, directory = {}, None
        for _code, _divider, content in response.content():
            key, separator, value = content.partition('=')
            if not separator:
                continue
            value = value.strip().strip('"')
            if key == 'HiddenServiceDir':
                directory = value
                result[directory] = {'ports': [], 'options': {}}
            elif directory is None:
                continue
            elif key == 'HiddenServicePort':
                port, _, target = value.partition(' ')
                result[directory]['ports'].append((int(port), target or '127.0.0.1:%s' % port))
            else:
                result[directory]['options'][key] = value
        return result

    @staticmethod
    def _read_hostname(controller, directory):
        if not controller.is_localhost():
            return None
        path = os.path.join(directory, 'hostname')
        if not os.path.isabs(path):
            return None
        try:
            with open(path, encoding='ascii', errors='replace') as handle:
                content = handle.read().split()
        except OSError:
            return None
        return content[0] if content else None

    def create_ephemeral_service(self, ports, key_type='NEW', key_content='ED25519-V3', discard_key=False,
                                 detached=False, await_publication=False, max_streams=None, client_auth_v3=None):
        """ports: lista de (puerto virtual, destino); un destino vacío usa el mismo puerto local."""
        controller = self._require_controller()
        port_map = {int(port): (target.strip() or str(port)) for port, target in ports}

        events = queue.Queue() if await_publication else None
        listener = events.put if events is not None else None
        if listener is not None:
            controller.add_event_listener(listener, EventType.HS_DESC)
        try:
            response = controller.create_ephemeral_hidden_service(
                port_map,
                key_type=key_type,
                key_content=key_content,
                discard_key=discard_key,
                detached=detached,
                max_streams=max_streams or None,
                client_auth_v3=client_auth_v3 or None,
            )
            service_id = response.service_id
            mapped = sorted(port_map.items())
            self._ephemeral_registry[service_id] = {
                'ports': mapped,
                'key_type': response.private_key_type or (key_content if key_type == 'NEW' else key_type),
            }
            publication = None
            if events is not None:
                # Stem lanzaría Timeout sin devolver la clave privada; por eso se espera aquí
                publication = self._await_publication(events, service_id, PUBLICATION_TIMEOUT)
        finally:
            if listener is not None:
                controller.remove_event_listener(listener)

        return OnionServiceCreated(
            kind=ONION_EPHEMERAL,
            address=service_id + '.onion',
            service_id=service_id,
            ports=mapped,
            private_key_type=response.private_key_type,
            private_key=response.private_key,
            client_auth=dict(response.client_auth or {}),
            detached=detached,
            publication=publication,
        )

    @staticmethod
    def _await_publication(events, service_id, timeout):
        deadline = time.monotonic() + timeout
        uploaded_to, failures = set(), []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False, 'No se confirmó la publicación del descriptor en %d segundos.' % timeout
            try:
                event = events.get(timeout=remaining)
            except queue.Empty:
                continue
            action = str(event.action)
            directory = event.directory_fingerprint
            if action == 'UPLOAD' and event.address == service_id:
                uploaded_to.add(directory)
            elif action == 'UPLOADED' and directory in uploaded_to:
                return True, 'Descriptor publicado en el directorio $%s.' % directory
            elif action == 'FAILED' and directory in uploaded_to:
                failures.append('$%s (%s)' % (directory, event.reason))
                if len(failures) >= len(uploaded_to):
                    return False, 'Falló la publicación del descriptor: %s.' % ', '.join(failures)

    @staticmethod
    def _apply_hidden_service_conf(controller, conf):
        """Equivale a Controller.set_hidden_service_conf, pero escapa los valores.

        Stem envía las rutas sin escapar y Tor interpreta las barras invertidas
        de Windows como secuencias de escape; con una ruta corrupta, Tor puede
        llegar a cerrarse al aplicar la configuración.
        """
        if not conf:
            controller.reset_conf('HiddenServiceDir')
            return
        options = []
        for directory, entry in conf.items():
            options.append(('HiddenServiceDir', _escape_conf_value(directory)))
            for port, target in entry['ports']:
                options.append(('HiddenServicePort', _escape_conf_value('%s %s' % (port, target))))
            for key, value in entry['options'].items():
                options.append((key, _escape_conf_value(str(value))))
        try:
            controller.set_options(options)
        finally:
            controller.clear_cache()

    @staticmethod
    def _find_directory_key(conf, directory):
        wanted = os.path.normcase(os.path.abspath(directory))
        for key in conf:
            if os.path.normcase(os.path.abspath(key)) == wanted:
                return key
        return None

    def create_persistent_service(self, directory, ports, save_to_disk=True):
        """ports: lista de (puerto virtual, dirección de destino, puerto de destino)."""
        controller = self._require_controller()
        directory = os.path.abspath(directory)
        if controller.is_localhost():
            # Tor solo crea el último nivel del directorio y, si no puede, se cierra
            os.makedirs(directory, exist_ok=True)

        conf = self._hidden_service_conf(controller)
        directory = self._find_directory_key(conf, directory) or directory
        entry = conf.setdefault(directory, {'ports': [], 'options': {}})
        mappings = [(int(port), '%s:%s' % (address or '127.0.0.1', target_port or port))
                    for port, address, target_port in ports]
        for mapping in mappings:
            if mapping not in entry['ports']:
                entry['ports'].append(mapping)
        self._apply_hidden_service_conf(controller, conf)

        hostname = None
        deadline = time.monotonic() + 3
        while hostname is None and time.monotonic() < deadline:
            hostname = self._read_hostname(controller, directory)
            if hostname is None:
                time.sleep(0.1)

        saved = None
        if save_to_disk:
            try:
                controller.save_conf()
                saved = True
            except stem.ControllerError as exc:
                saved = str(exc)

        return OnionServiceCreated(
            kind=ONION_PERSISTENT,
            address=hostname,
            service_id=hostname[:-len('.onion')] if hostname and hostname.endswith('.onion') else None,
            ports=mappings,
            directory=directory,
            saved=saved,
        )

    def remove_ephemeral_service(self, service_id):
        removed = self._require_controller().remove_ephemeral_hidden_service(service_id)
        self._ephemeral_registry.pop(service_id, None)
        return removed

    def remove_persistent_service(self, directory, save_to_disk=False):
        controller = self._require_controller()
        conf = self._hidden_service_conf(controller)
        key = self._find_directory_key(conf, directory)
        if key is None:
            return False
        del conf[key]
        self._apply_hidden_service_conf(controller, conf)
        if save_to_disk:
            controller.save_conf()
        return True
