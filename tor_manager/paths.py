"""Rutas de la aplicación y localización del ejecutable de Tor."""

import os
import sys

TOR_EXECUTABLE_NAME = 'tor.exe' if os.name == 'nt' else 'tor'


def get_app_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resources_dir():
    return os.path.join(get_app_root(), 'resources')


def default_bundled_tor_path():
    return os.path.join(resources_dir(), 'tor', TOR_EXECUTABLE_NAME)


def bundled_tor_available():
    return os.path.isfile(default_bundled_tor_path())


def user_data_dir():
    return os.path.join(get_app_root(), 'TorManagerConfig')

def settings_file():
    return os.path.join(user_data_dir(), 'settings.json')


def default_data_directory():
    return os.path.join(user_data_dir(), 'tor-data')


def torrc_file():
    return os.path.join(user_data_dir(), 'torrc')


def app_log_file():
    return os.path.join(user_data_dir(), 'tor-manager.log')


def default_onion_services_dir():
    return os.path.join(user_data_dir(), 'onion-services')


def find_geoip_files(tor_executable):
    """Busca los ficheros geoip del Tor Expert Bundle, de Tor Browser o de una
    instalación con estructura bin/ y share/tor/."""
    tor_dir = os.path.dirname(os.path.abspath(tor_executable))
    parent = os.path.dirname(tor_dir)
    candidates = (
        os.path.join(parent, 'data'),
        os.path.join(tor_dir, 'data'),
        os.path.join(parent, 'share', 'tor'),
        os.path.join(parent, 'Data', 'Tor'),
        tor_dir,
    )
    for directory in candidates:
        geoip = os.path.join(directory, 'geoip')
        if os.path.isfile(geoip):
            geoip6 = os.path.join(directory, 'geoip6')
            return geoip, geoip6 if os.path.isfile(geoip6) else None
    return None, None
