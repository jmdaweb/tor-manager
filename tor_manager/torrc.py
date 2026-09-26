"""Generación del torrc de la aplicación y de los argumentos de arranque de Tor.

Tor se inicia con un torrc real en disco para que SAVECONF pueda guardar la
configuración. Las opciones esenciales (puertos, directorio de datos y
autenticación) se pasan además por la línea de órdenes, de modo que siempre
prevalecen sobre lo que se haya guardado en el torrc.
"""

import os

from . import paths
from .settings import LAUNCH_AUTH_COOKIE, LAUNCH_AUTH_PASSWORD

FACTORY_TORRC = (
    '# Archivo de configuración de Tor gestionado por Tor Manager.\n'
    '# Tor Manager puede sobrescribirlo al guardar la configuración (SAVECONF).\n'
    'Log notice stdout\n'
)

_STDOUT_LOG_LEVELS = ('debug', 'info', 'notice')


def write_factory_torrc(path=None):
    path = path or paths.torrc_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(FACTORY_TORRC)
    return path


def ensure_torrc():
    path = paths.torrc_file()
    if not os.path.isfile(path):
        write_factory_torrc(path)
    return path


def _read_option_lines(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            key, _, value = stripped.partition(' ')
            result.append((key, value.strip()))
    return result


def _remove_options(path, names):
    names = {name.lower() for name in names}
    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            lines = handle.read().splitlines(keepends=True)
    except OSError:
        return
    kept = [line for line in lines if line.strip().partition(' ')[0].lower() not in names]
    if len(kept) != len(lines):
        with open(path, 'w', encoding='utf-8') as handle:
            handle.writelines(kept)


def _is_stdout_log(value):
    parts = value.lower().split()
    return len(parts) >= 2 and parts[-1] == 'stdout' and parts[0].split('-')[0] in _STDOUT_LOG_LEVELS


def parse_extra_options(text):
    """Convierte líneas «Opción valor» en pares para la línea de órdenes."""
    pairs = []
    for line in (text or '').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        key, _, value = stripped.partition(' ')
        pairs.append((key, value.strip()))
    return pairs


def build_launch_args(settings, tor_executable, torrc_path, password_hash=None):
    data_directory = settings.effective_data_directory()
    os.makedirs(data_directory, exist_ok=True)

    args = [
        'SocksPort', str(settings.socks_port),
        'ControlPort', str(settings.control_port),
        'DataDirectory', data_directory,
    ]

    if settings.launch_auth == LAUNCH_AUTH_PASSWORD:
        args += ['HashedControlPassword', password_hash, 'CookieAuthentication', '0']
    else:
        # evita que una contraseña guardada antes en el torrc siga siendo válida
        _remove_options(torrc_path, ['HashedControlPassword'])
        cookie = '1' if settings.launch_auth == LAUNCH_AUTH_COOKIE else '0'
        args += ['CookieAuthentication', cookie]

    options = _read_option_lines(torrc_path)
    if not any(key.lower() == 'log' and _is_stdout_log(value) for key, value in options):
        # Stem necesita leer el progreso del arranque en la salida estándar
        args += ['+Log', 'notice stdout']

    configured = {key.lower() for key, _ in options}
    geoip, geoip6 = paths.find_geoip_files(tor_executable)
    if geoip and 'geoipfile' not in configured:
        args += ['GeoIPFile', geoip]
    if geoip6 and 'geoipv6file' not in configured:
        args += ['GeoIPv6File', geoip6]

    for key, value in parse_extra_options(settings.extra_options):
        args += [key, value]
    return args
