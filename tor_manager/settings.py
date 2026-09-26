"""Preferencias de la aplicación persistidas en JSON."""

import json
import logging
import os
from dataclasses import asdict, dataclass, fields

from . import paths

log = logging.getLogger(__name__)

MODE_BUNDLED = 'bundled'
MODE_CUSTOM = 'custom'
MODE_ATTACH = 'attach'

LAUNCH_AUTH_COOKIE = 'cookie'
LAUNCH_AUTH_PASSWORD = 'password'
LAUNCH_AUTH_NONE = 'none'

AUTH_AUTO = 'auto'
AUTH_NONE = 'none'
AUTH_PASSWORD = 'password'
AUTH_COOKIE = 'cookie'
AUTH_SAFECOOKIE = 'safecookie'


@dataclass
class AppSettings:
    tor_mode: str = MODE_BUNDLED
    custom_tor_path: str = ''
    socks_port: int = 9050
    control_port: int = 9051
    attach_address: str = '127.0.0.1'
    attach_port: int = 9051
    data_directory: str = ''
    launch_auth: str = LAUNCH_AUTH_COOKIE
    auth_method: str = AUTH_AUTO
    saved_password: str = ''
    extra_options: str = ''
    minimize_to_tray: bool = True
    close_to_tray: bool = False
    auto_start: bool = False
    log_level: str = 'NOTICE'

    def effective_data_directory(self):
        return self.data_directory or paths.default_data_directory()

    def copy(self):
        return AppSettings(**asdict(self))

    def update_from(self, other):
        for item in fields(self):
            setattr(self, item.name, getattr(other, item.name))

    def save(self):
        target = paths.settings_file()
        os.makedirs(os.path.dirname(target), exist_ok=True)
        temporary = target + '.tmp'
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(asdict(self), handle, indent=2, ensure_ascii=False)
        os.replace(temporary, target)


def load_settings():
    settings = AppSettings()
    try:
        with open(paths.settings_file(), encoding='utf-8') as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return settings
    except (OSError, ValueError) as exc:
        log.warning('No se pudieron leer los ajustes; se usarán los valores predeterminados (%s).', exc)
        return settings

    if not isinstance(data, dict):
        return settings
    for item in fields(settings):
        value = data.get(item.name)
        if value is not None and isinstance(value, type(item.default)):
            setattr(settings, item.name, value)
    return settings
