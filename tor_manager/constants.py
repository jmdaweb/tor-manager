"""Identificadores de órdenes y textos de presentación compartidos."""

import itertools

import wx

_ids = itertools.count(wx.ID_HIGHEST + 100)


def _new_id():
    return next(_ids)


# Archivo
ID_CONNECT = _new_id()
ID_RESTART_TOR = _new_id()
ID_DISCONNECT = _new_id()
ID_SETTINGS = _new_id()
ID_HIDE_TO_TRAY = _new_id()
ID_SHOW_WINDOW = _new_id()

# Circuitos
ID_NEW_CIRCUIT = _new_id()
ID_EXTEND_CIRCUIT = _new_id()
ID_REPURPOSE_CIRCUIT = _new_id()
ID_CLOSE_CIRCUIT = _new_id()
ID_CLOSE_CIRCUIT_IF_UNUSED = _new_id()
ID_REFRESH_CIRCUITS = _new_id()

# Streams
ID_ATTACH_STREAM = _new_id()
ID_CLOSE_STREAM = _new_id()
ID_MANUAL_ATTACH = _new_id()
ID_REFRESH_STREAMS = _new_id()

# Servicios onion
ID_ADD_EPHEMERAL = _new_id()
ID_ADD_PERSISTENT = _new_id()
ID_REMOVE_SERVICE = _new_id()
ID_COPY_ADDRESS = _new_id()
ID_REFRESH_SERVICES = _new_id()

# Configuración
ID_EDIT_OPTION = _new_id()
ID_RESET_OPTION = _new_id()
ID_LOAD_TORRC = _new_id()
ID_SAVE_CONFIG = _new_id()
ID_FACTORY_RESET = _new_id()
ID_VIEW_CONFIG_TEXT = _new_id()
ID_REFRESH_CONFIG = _new_id()

# Control
ID_NEW_IDENTITY = _new_id()
ID_RELOAD = _new_id()
ID_CLEAR_DNS = _new_id()
ID_HEARTBEAT = _new_id()
ID_DORMANT = _new_id()
ID_ACTIVE = _new_id()
ID_DROP_GUARDS = _new_id()
ID_GETINFO = _new_id()
ID_RELAY_LOOKUP = _new_id()
ID_REFRESH_INFO = _new_id()

# Ver
ID_VIEW_CIRCUITS = _new_id()
ID_VIEW_STREAMS = _new_id()
ID_VIEW_SERVICES = _new_id()
ID_VIEW_CONFIG = _new_id()
ID_VIEW_LOG = _new_id()
ID_REFRESH_CURRENT = _new_id()

CIRC_STATUS_LABELS = {
    'LAUNCHED': 'Iniciado',
    'BUILT': 'Construido',
    'GUARD_WAIT': 'Esperando al guardia',
    'EXTENDED': 'Extendiéndose',
    'FAILED': 'Fallido',
    'CLOSED': 'Cerrado',
}

CIRC_PURPOSE_LABELS = {
    'GENERAL': 'General',
    'HS_CLIENT_INTRO': 'Cliente onion: introducción',
    'HS_CLIENT_REND': 'Cliente onion: encuentro',
    'HS_SERVICE_INTRO': 'Servicio onion: introducción',
    'HS_SERVICE_REND': 'Servicio onion: encuentro',
    'TESTING': 'Pruebas',
    'CONTROLLER': 'Controlador',
    'MEASURE_TIMEOUT': 'Medición de tiempos',
    'HS_VANGUARDS': 'Vanguardias onion',
    'PATH_BIAS_TESTING': 'Prueba de sesgo de ruta',
    'CIRCUIT_PADDING': 'Relleno de circuito',
    'CONFLUX_LINKED': 'Conflux enlazado',
    'CONFLUX_UNLINKED': 'Conflux sin enlazar',
}

CIRC_BUILD_FLAG_LABELS = {
    'ONEHOP_TUNNEL': 'túnel de un salto',
    'IS_INTERNAL': 'interno',
    'NEED_CAPACITY': 'requiere capacidad',
    'NEED_UPTIME': 'requiere estabilidad',
}

STREAM_STATUS_LABELS = {
    'NEW': 'Nuevo',
    'NEWRESOLVE': 'Nueva resolución DNS',
    'REMAP': 'Redirigido',
    'SENTCONNECT': 'Conexión enviada',
    'SENTRESOLVE': 'Resolución enviada',
    'SUCCEEDED': 'Establecido',
    'FAILED': 'Fallido',
    'DETACHED': 'Desvinculado',
    'CLOSED': 'Cerrado',
}

STREAM_PURPOSE_LABELS = {
    'DIR_FETCH': 'Descarga de directorio',
    'DIR_UPLOAD': 'Subida de directorio',
    'DNS_REQUEST': 'Consulta DNS',
    'DIRPORT_TEST': 'Prueba de DirPort',
    'USER': 'Usuario',
}

RELAY_END_REASONS = [
    ('MISC', 'Otro motivo'),
    ('DONE', 'Conexión terminada'),
    ('DESTROY', 'Circuito destruido'),
    ('TIMEOUT', 'Tiempo agotado'),
    ('CONNECTREFUSED', 'Conexión rechazada'),
    ('EXITPOLICY', 'Política de salida'),
    ('RESOLVEFAILED', 'Fallo de resolución DNS'),
    ('NOROUTE', 'Sin ruta'),
    ('HIBERNATING', 'Relé en hibernación'),
    ('INTERNAL', 'Error interno'),
    ('RESOURCELIMIT', 'Límite de recursos'),
    ('CONNRESET', 'Conexión restablecida'),
    ('TORPROTOCOL', 'Error de protocolo de Tor'),
    ('NOTDIRECTORY', 'No es un directorio'),
]
RELAY_END_REASON_LABELS = dict(RELAY_END_REASONS)

LOG_LEVELS = [
    ('ERR', 'Solo errores'),
    ('WARN', 'Advertencias'),
    ('NOTICE', 'Avisos (recomendado)'),
    ('INFO', 'Información detallada'),
    ('DEBUG', 'Depuración (muy detallado)'),
]
RUNLEVEL_LABELS = {
    'ERR': 'Error',
    'WARN': 'Advertencia',
    'NOTICE': 'Aviso',
    'INFO': 'Información',
    'DEBUG': 'Depuración',
    'ERROR': 'Error',
    'WARNING': 'Advertencia',
    'CRITICAL': 'Crítico',
}

AUTH_METHOD_LABELS = {
    'none': 'Sin autenticación',
    'password': 'Contraseña',
    'cookie': 'Cookie',
    'safecookie': 'SafeCookie',
    'unknown': 'Desconocido',
}

CIRCUIT_PURPOSE_CHOICES = [
    ('general', 'General (uso normal)'),
    ('controller', 'Controlador (reservado para este programa)'),
]
