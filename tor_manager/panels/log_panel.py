import collections
from datetime import datetime

import wx

from .. import constants as C
from ..errors import show_error
from ..logging_setup import drain_display_queue
from ..widgets import readonly_text, save_text_to_file, set_text_if_changed

MAX_LOG_LINES = 5000
TRIM_LINES = 1000


class LogPanel(wx.Panel):
    """Información general de Tor y registro de eventos en cuadros de solo lectura."""

    def __init__(self, parent, log_level):
        super().__init__(parent)
        self.on_level_changed = None
        self._line_lengths = collections.deque()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label='&Información general de Tor:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        self.info = readonly_text(self, value='Sin conexión con Tor.')
        sizer.Add(self.info, 2, wx.EXPAND | wx.ALL, 6)
        sizer.Add(wx.Button(self, C.ID_REFRESH_INFO, 'Actualizar i&nformación'), 0, wx.LEFT | wx.BOTTOM, 6)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Ni&vel de detalle de los mensajes de Tor:'), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.level_choice = wx.Choice(self, choices=[text for _, text in C.LOG_LEVELS])
        codes = [code for code, _ in C.LOG_LEVELS]
        self.level_choice.SetSelection(codes.index(log_level) if log_level in codes else 2)
        row.Add(self.level_choice, 0, wx.RIGHT, 12)
        self.follow = wx.CheckBox(self, label='Se&guir los mensajes nuevos')
        self.follow.SetValue(True)
        row.Add(self.follow, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        clear_button = wx.Button(self, label='&Limpiar registro')
        row.Add(clear_button, 0, wx.RIGHT, 6)
        save_button = wx.Button(self, label='Guardar regis&tro…')
        row.Add(save_button, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)

        sizer.Add(wx.StaticText(self, label='&Registro de eventos:'), 0, wx.LEFT | wx.RIGHT, 6)
        self.log = readonly_text(self)
        sizer.Add(self.log, 3, wx.EXPAND | wx.ALL, 6)
        self.SetSizer(sizer)

        self.level_choice.Bind(wx.EVT_CHOICE, self._on_level_choice)
        clear_button.Bind(wx.EVT_BUTTON, self._on_clear)
        save_button.Bind(wx.EVT_BUTTON, self._on_save)

        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer, self._timer)
        self._timer.Start(300)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

    def selected_level(self):
        return C.LOG_LEVELS[self.level_choice.GetSelection()][0]

    def set_info(self, items):
        width = max((len(label) for label, _ in items), default=0)
        set_text_if_changed(self.info, '\n'.join('%s: %s' % (label.ljust(width), value) for label, value in items))

    def set_info_text(self, text):
        set_text_if_changed(self.info, text)

    def append(self, source, runlevel, message, timestamp=None):
        timestamp = timestamp or datetime.now()
        level = C.RUNLEVEL_LABELS.get(runlevel, runlevel)
        lines = ['%s [%s, %s] %s' % (timestamp.strftime('%H:%M:%S'), source, level, message.rstrip())]
        self._write(lines)

    def _write(self, lines):
        control = self.log
        text = ''.join(line + '\n' for line in lines)
        follow = self.follow.IsChecked()
        selection = control.GetSelection()

        control.AppendText(text)
        for line in lines:
            self._line_lengths.append(len(line) + 1)

        removed = 0
        if len(self._line_lengths) > MAX_LOG_LINES:
            for _ in range(TRIM_LINES):
                removed += self._line_lengths.popleft()
            control.Remove(0, removed)

        if follow:
            control.SetInsertionPointEnd()
        else:
            start, end = (max(0, position - removed) for position in selection)
            control.SetSelection(start, end)

    def _on_timer(self, event):
        entries = drain_display_queue()
        if entries:
            self._write([
                '%s [Programa, %s] %s' % (datetime.fromtimestamp(created).strftime('%H:%M:%S'),
                                          C.RUNLEVEL_LABELS.get(level, level), message)
                for created, level, message in entries
            ])

    def _on_level_choice(self, event):
        if self.on_level_changed is not None:
            self.on_level_changed(self.selected_level())

    def _on_clear(self, event):
        self.log.Clear()
        self._line_lengths.clear()

    def _on_save(self, event):
        try:
            save_text_to_file(self, self.log.GetValue(), 'Guardar registro de eventos',
                              default_file='registro-tor.txt')
        except OSError as exc:
            show_error(self, exc, 'No se pudo guardar el registro')

    def _on_destroy(self, event):
        if event.GetEventObject() is self:
            self._timer.Stop()
        event.Skip()
