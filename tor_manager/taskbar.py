import wx
import wx.adv

from . import APP_NAME
from . import constants as C
from .icons import make_icon


class TorTaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        super().__init__()
        self._frame = frame
        self._connected = False
        self.update(False, 'sin conexión')
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_UP, self._on_activate)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self._on_activate)
        self.Bind(wx.EVT_MENU, self._on_toggle_window, id=C.ID_SHOW_WINDOW)
        self.Bind(wx.EVT_MENU, lambda event: self._frame.request_new_identity(), id=C.ID_NEW_IDENTITY)
        self.Bind(wx.EVT_MENU, lambda event: self._frame.request_exit(), id=wx.ID_EXIT)

    def update(self, connected, status):
        self._connected = connected
        tooltip = '%s: %s' % (APP_NAME, status)
        self.SetIcon(make_icon(32, connected), tooltip[:120])

    def notify(self, title, message):
        if self.IsIconInstalled() and hasattr(self, 'ShowBalloon'):
            self.ShowBalloon(title, message, 5000, wx.ICON_INFORMATION)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        visible = self._frame.IsShown() and not self._frame.IsIconized()
        menu.Append(C.ID_SHOW_WINDOW, '&Ocultar Tor Manager' if visible else '&Mostrar Tor Manager')
        menu.Append(C.ID_NEW_IDENTITY, 'Nueva &identidad').Enable(self._connected)
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT, '&Salir')
        return menu

    def _on_activate(self, event):
        self._frame.restore_from_tray()

    def _on_toggle_window(self, event):
        if self._frame.IsShown() and not self._frame.IsIconized():
            self._frame.hide_to_tray()
        else:
            self._frame.restore_from_tray()
