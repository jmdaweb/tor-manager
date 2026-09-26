"""Presentación uniforme de errores, avisos y confirmaciones."""

import logging

import wx

from .exceptions import (
    AuthenticationError,
    AuthMethodUnavailableError,
    CircuitExtensionError,
    CookieAuthError,
    IncorrectPasswordError,
    PasswordRequiredError,
    TorConnectionError,
    TorLaunchError,
    TorManagerError,
    TorNotConnectedError,
    TorTimeoutError,
    UnsupportedFeatureError,
)

log = logging.getLogger(__name__)

_TITLES = (
    (PasswordRequiredError, 'Contraseña necesaria'),
    (IncorrectPasswordError, 'Contraseña incorrecta'),
    (CookieAuthError, 'Error de autenticación por cookie'),
    (AuthMethodUnavailableError, 'Método de autenticación no disponible'),
    (AuthenticationError, 'Error de autenticación'),
    (TorLaunchError, 'No se pudo iniciar Tor'),
    (TorNotConnectedError, 'Sin conexión con Tor'),
    (TorConnectionError, 'Error de conexión'),
    (TorTimeoutError, 'Tiempo de espera agotado'),
    (CircuitExtensionError, 'Error en el circuito'),
    (UnsupportedFeatureError, 'Operación no disponible'),
    (TorManagerError, 'Tor ha rechazado la petición'),
)


def describe_exception(exc):
    """Devuelve (título, mensaje) para mostrar una excepción al usuario."""
    for exception_type, title in _TITLES:
        if isinstance(exc, exception_type):
            message = exc.message
            if isinstance(exc, CookieAuthError) and exc.cookie_path:
                message += '\nFichero de cookie: %s' % exc.cookie_path
            if exc.detail and exc.detail != exc.message:
                message += '\n\nRespuesta de Tor: %s' % exc.detail
            return title, message
    if isinstance(exc, ValueError):
        return 'Valor no válido', str(exc)
    if isinstance(exc, OSError):
        return 'Error del sistema', str(exc)
    log.error('Error inesperado', exc_info=exc)
    return 'Error inesperado', '%s\n\nConsulte la pestaña de registro para más detalles.' % exc


def short_description(exc):
    title, message = describe_exception(exc)
    return '%s: %s' % (title, message.splitlines()[0])


def show_error(parent, exc, title=None):
    default_title, message = describe_exception(exc)
    show_message(parent, message, title or default_title, wx.ICON_ERROR)


def show_message(parent, message, title, icon=wx.ICON_INFORMATION):
    with wx.MessageDialog(parent, message, title, wx.OK | icon) as dialog:
        dialog.ShowModal()


def confirm(parent, message, title='Confirmar', default_no=True):
    style = wx.YES_NO | wx.ICON_QUESTION | (wx.NO_DEFAULT if default_no else wx.YES_DEFAULT)
    with wx.MessageDialog(parent, message, title, style) as dialog:
        dialog.SetYesNoLabels('&Sí', '&No')
        return dialog.ShowModal() == wx.ID_YES
