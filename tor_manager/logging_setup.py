"""Configuración del registro de la aplicación.

Los mensajes se guardan en un fichero rotativo y además se encolan para que
el panel de registro los muestre (lo drena con un wx.Timer, así ningún hilo
secundario toca la interfaz).
"""

import logging
import logging.handlers
import os
import queue
import sys

from . import paths

_display_queue = queue.Queue(maxsize=10000)


class QueueLogHandler(logging.Handler):
    def emit(self, record):
        try:
            _display_queue.put_nowait((record.created, record.levelname, self.format(record)))
        except queue.Full:
            pass
        except Exception:
            self.handleError(record)


def drain_display_queue(limit=500):
    items = []
    while len(items) < limit:
        try:
            items.append(_display_queue.get_nowait())
        except queue.Empty:
            break
    return items


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    display = QueueLogHandler(level=logging.INFO)
    display.setFormatter(logging.Formatter('%(message)s'))
    root.addHandler(display)

    try:
        os.makedirs(paths.user_data_dir(), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            paths.app_log_file(), maxBytes=1024 * 1024, backupCount=3, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
        root.addHandler(file_handler)
    except OSError:
        pass

    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        console.setFormatter(logging.Formatter('%(levelname)s %(name)s: %(message)s'))
        root.addHandler(console)

    # Stem registra cada mensaje del protocolo en DEBUG/TRACE
    logging.getLogger('stem').setLevel(logging.INFO)
