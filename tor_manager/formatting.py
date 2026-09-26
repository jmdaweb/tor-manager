"""Funciones de formato de datos para mostrarlos en la interfaz."""

from datetime import timezone


def _decimal(value, digits=1):
    return ('%.*f' % (digits, value)).replace('.', ',')


def format_bytes(value):
    if value is None:
        return 'desconocido'
    size = float(value)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(size) < 1024:
            return '%d %s' % (size, unit) if unit == 'B' else '%s %s' % (_decimal(size), unit)
        size /= 1024
    return '%s TB' % _decimal(size)


def format_rate(bytes_per_second):
    return '%s/s' % format_bytes(bytes_per_second)


def format_duration(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append('%d d' % days)
    if hours:
        parts.append('%d h' % hours)
    if minutes:
        parts.append('%d min' % minutes)
    parts.append('%d s' % seconds)
    return ' '.join(parts)


def format_utc_datetime(value, with_date=True):
    """Stem entrega las fechas de Tor como datetime en UTC sin zona horaria."""
    if value is None:
        return ''
    local = value.replace(tzinfo=timezone.utc).astimezone()
    return local.strftime('%d/%m/%Y %H:%M:%S' if with_date else '%H:%M:%S')


def label(mapping, code):
    if code is None or code == '':
        return ''
    return mapping.get(code, code)


def label_with_code(mapping, code):
    if not code:
        return 'ninguno'
    text = mapping.get(code)
    return '%s (%s)' % (text, code) if text else code


def relay_name(fingerprint, nickname):
    if nickname and fingerprint:
        return '%s ($%s)' % (nickname, fingerprint)
    return nickname or ('$' + fingerprint if fingerprint else 'desconocido')


def path_summary(path):
    if not path:
        return '(sin saltos)'
    return ' → '.join(nickname or fingerprint[:8] for fingerprint, nickname in path)


def yes_no(value):
    return 'Sí' if value else 'No'
