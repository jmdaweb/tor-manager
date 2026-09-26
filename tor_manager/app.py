"""Punto de entrada de la aplicación."""

import ctypes
import logging
import os
import sys
import threading
import locale
locale.setlocale(locale.LC_ALL, "es_ES")

import wx

from . import APP_NAME, paths
from .errors import show_message
from .logging_setup import setup_logging
from .main_frame import MainFrame
from .settings import load_settings
from .tor_backend import TorBackend

log = logging.getLogger(__name__)


class TorManagerApp(wx.App):
    def __init__(self, *args):
        super().__init__(*args)
        self.lc = wx.Locale()
        wxLang=self.lc.FindLanguageInfo("es_ES")
        self.lc.Init(wxLang.Language)

    def OnInit(self):
        self.SetAppName('TorManager')
        self.SetAppDisplayName(APP_NAME)
        self._showing_error = False

        self.instance_checker = wx.SingleInstanceChecker('TorManager-%s' % wx.GetUserId())
        if self.instance_checker.IsAnotherRunning():
            show_message(None, 'Tor Manager ya se está ejecutando. Búsquelo en la bandeja del sistema.', APP_NAME)
            return False

        sys.excepthook = self._excepthook
        threading.excepthook = self._thread_excepthook

        self.settings = load_settings()
        self.backend = TorBackend()
        self.frame = MainFrame(self.backend, self.settings)
        self.SetTopWindow(self.frame)
        wx.CallAfter(self._initial_startup)
        return True

    def _initial_startup(self):
        if self.frame.run_startup():
            self.frame.Show()
            self.frame.Raise()
        else:
            self.frame.exit_without_connection()

    def _excepthook(self, exc_type, exc_value, exc_traceback):
        log.error('Excepción no controlada', exc_info=(exc_type, exc_value, exc_traceback))
        if self._showing_error or not wx.IsMainThread():
            return
        self._showing_error = True
        try:
            show_message(None, 'Se ha producido un error inesperado: %s\n\nLos detalles se han guardado en %s.'
                         % (exc_value, paths.app_log_file()), 'Error inesperado', wx.ICON_ERROR)
        finally:
            self._showing_error = False

    @staticmethod
    def _thread_excepthook(args):
        log.error('Excepción no controlada en el hilo %s', args.thread.name if args.thread else '?',
                  exc_info=(args.exc_type, args.exc_value, args.exc_traceback))


def _enable_dpi_awareness():
    if os.name != 'nt':
        return
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2: texto nítido con escalado alto
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass


def main():
    _enable_dpi_awareness()
    setup_logging()
    app = TorManagerApp(False)
    app.MainLoop()
