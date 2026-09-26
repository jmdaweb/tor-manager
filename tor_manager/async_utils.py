"""Ejecución de tareas bloqueantes fuera del hilo de la interfaz.

Regla de la aplicación: ninguna llamada a Stem se hace en el hilo de wx y
ningún widget se toca desde otro hilo. Los callbacks de run_in_thread se
entregan siempre en el hilo de wx.
"""

import logging
import threading

import wx

log = logging.getLogger(__name__)


def call_after(function, *args, **kwargs):
    """wx.CallAfter tolerante a que la aplicación se esté cerrando."""
    if wx.GetApp() is None:
        return False
    try:
        wx.CallAfter(function, *args, **kwargs)
    except (AssertionError, RuntimeError):
        return False
    return True


def _deliver(owner, callback, value):
    if owner is not None and not owner:
        return
    callback(value)


def run_in_thread(function, *args, on_success=None, on_error=None, owner=None, **kwargs):
    """Ejecuta function en un hilo secundario.

    on_success(resultado) y on_error(excepción) se llaman en el hilo de wx, y
    se omiten si owner es una ventana que ya se ha destruido.
    """

    def worker():
        try:
            result = function(*args, **kwargs)
        except Exception as exc:
            if on_error is None:
                log.exception('Error en una tarea en segundo plano')
            else:
                log.debug('Tarea en segundo plano fallida: %r', exc, exc_info=True)
                call_after(_deliver, owner, on_error, exc)
            return
        if on_success is not None:
            call_after(_deliver, owner, on_success, result)

    name = 'tor-manager-%s' % getattr(function, '__name__', 'task')
    thread = threading.Thread(target=worker, name=name, daemon=True)
    thread.start()
    return thread


def call_in_gui_and_wait(function, *args, **kwargs):
    """Ejecuta function en el hilo de wx y espera su resultado desde otro hilo."""
    if wx.IsMainThread():
        return function(*args, **kwargs)

    done = threading.Event()
    box = {}

    def runner():
        try:
            box['result'] = function(*args, **kwargs)
        except Exception as exc:
            box['error'] = exc
        finally:
            done.set()

    if not call_after(runner):
        raise RuntimeError('La interfaz ya no está disponible.')
    done.wait()
    if 'error' in box:
        raise box['error']
    return box.get('result')
