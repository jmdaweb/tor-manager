"""Selección y consulta de relés de la red Tor."""

import wx

from ..async_utils import run_in_thread
from ..errors import short_description
from ..formatting import format_rate, format_utc_datetime
from ..widgets import readonly_text, set_text_if_changed

FLAG_FILTERS = [
    ('', 'Todos los relés'),
    ('Guard', 'Guardias (Guard)'),
    ('Exit', 'Salidas (Exit)'),
    ('Fast', 'Rápidos (Fast)'),
    ('Stable', 'Estables (Stable)'),
]


def _bandwidth_text(relay):
    return format_rate(relay.bandwidth * 1000) if relay.bandwidth is not None else 'desconocido'


def format_relay(relay):
    lines = [
        'Apodo: %s' % relay.nickname,
        'Huella digital: $%s' % relay.fingerprint,
        'Dirección: %s:%s' % (relay.address, relay.or_port),
        'Indicadores: %s' % (', '.join(relay.flags) or 'ninguno'),
        'Ancho de banda del consenso: %s' % _bandwidth_text(relay),
    ]
    if relay.version:
        lines.append('Versión de Tor: %s' % relay.version)
    if relay.published:
        lines.append('Publicado: %s' % format_utc_datetime(relay.published))
    return '\n'.join(lines)


class RelayListCtrl(wx.ListCtrl):
    COLUMNS = [('Apodo', 160), ('Huella digital', 320), ('Dirección', 150), ('Indicadores', 260),
               ('Ancho de banda', 110)]

    def __init__(self, parent):
        super().__init__(parent, style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL)
        for index, (title, width) in enumerate(self.COLUMNS):
            self.InsertColumn(index, title, width=width)
        self.relays = []

    def set_relays(self, relays):
        self.relays = relays
        self.SetItemCount(len(relays))
        self.Refresh()

    def selected(self):
        index = self.GetFirstSelected()
        return self.relays[index] if 0 <= index < len(self.relays) else None

    def OnGetItemText(self, item, column):
        relay = self.relays[item]
        if column == 0:
            return relay.nickname
        if column == 1:
            return relay.fingerprint
        if column == 2:
            return '%s:%s' % (relay.address, relay.or_port)
        if column == 3:
            return ', '.join(relay.flags)
        return _bandwidth_text(relay)


class RelayPickerDialog(wx.Dialog):
    def __init__(self, parent, backend, title='Elegir un relé'):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._all = []
        self._filter_timer = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='&Buscar (apodo, huella o dirección):'), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.search = wx.TextCtrl(self)
        row.Add(self.search, 1, wx.RIGHT, 12)
        row.Add(wx.StaticText(self, label='&Tipo:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.flag_choice = wx.Choice(self, choices=[text for _, text in FLAG_FILTERS])
        self.flag_choice.SetSelection(0)
        row.Add(self.flag_choice, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)

        sizer.Add(wx.StaticText(self, label='&Relés (ordenados por ancho de banda):'), 0, wx.LEFT | wx.RIGHT, 8)
        self.list = RelayListCtrl(self)
        self.list.SetMinSize((760, 260))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Detalles del relé seleccionado:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.detail = readonly_text(self, value='Cargando la lista de relés…')
        self.detail.SetMinSize((-1, 110))
        sizer.Add(self.detail, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()

        self.FindWindowById(wx.ID_OK).Disable()
        self.search.Bind(wx.EVT_TEXT, self._on_search)
        self.flag_choice.Bind(wx.EVT_CHOICE, lambda event: self._apply_filter())
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selected)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda event: self.EndModal(wx.ID_OK))
        self.search.SetFocus()

        run_in_thread(backend.get_relays, on_success=self._on_loaded, on_error=self._on_load_failed, owner=self)

    def _on_loaded(self, relays):
        self._all = sorted(relays, key=lambda relay: relay.bandwidth or 0, reverse=True)
        self._apply_filter()
        self.FindWindowById(wx.ID_OK).Enable()

    def _on_load_failed(self, exc):
        self.detail.SetValue('No se pudo obtener la lista de relés: %s' % short_description(exc))

    def _on_search(self, event):
        if self._filter_timer is not None:
            self._filter_timer.Stop()
        self._filter_timer = wx.CallLater(400, self._apply_filter)

    def _apply_filter(self):
        text = self.search.GetValue().strip().lower().lstrip('$')
        flag = FLAG_FILTERS[self.flag_choice.GetSelection()][0]
        relays = [
            relay for relay in self._all
            if (not flag or flag in relay.flags)
            and (not text or text in relay.nickname.lower() or text in relay.fingerprint.lower()
                 or text in (relay.address or ''))
        ]
        self.list.set_relays(relays)
        set_text_if_changed(self.detail, '%d relés coinciden con el filtro. Seleccione uno en la lista.' % len(relays))

    def _on_selected(self, event):
        relay = self.list.selected()
        if relay is not None:
            self.detail.SetValue(format_relay(relay))

    def get_selected(self):
        return self.list.selected()


class RelayLookupDialog(wx.Dialog):
    def __init__(self, parent, backend):
        super().__init__(parent, title='Consultar un relé', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.backend = backend

        sizer = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='&Huella digital o apodo del relé:'), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.query = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        row.Add(self.query, 1, wx.RIGHT, 6)
        search = wx.Button(self, label='Bu&scar')
        row.Add(search, 0, wx.RIGHT, 6)
        pick = wx.Button(self, label='Elegir de la &lista…')
        row.Add(pick, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Información del relé:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.result = readonly_text(self)
        self.result.SetMinSize((720, 360))
        sizer.Add(self.result, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetEscapeId(wx.ID_CLOSE)
        self.CentreOnParent()

        search.Bind(wx.EVT_BUTTON, self._on_search)
        self.query.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        pick.Bind(wx.EVT_BUTTON, self._on_pick)
        self.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
        self.query.SetFocus()

    def _on_pick(self, event):
        with RelayPickerDialog(self, self.backend) as dialog:
            if dialog.ShowModal() == wx.ID_OK and dialog.get_selected() is not None:
                self.query.SetValue(dialog.get_selected().fingerprint)
                self._on_search(None)

    def _on_search(self, event):
        query = self.query.GetValue().strip()
        if not query:
            self.query.SetFocus()
            return
        self.result.SetValue('Consultando…')
        run_in_thread(self.backend.describe_relay, query, on_success=self._on_result,
                      on_error=lambda exc: self._show(short_description(exc)), owner=self)

    def _on_result(self, details):
        lines = [format_relay(details.relay)]
        if details.exit_policy:
            lines += ['', 'Política de salida (resumen): %s' % details.exit_policy]
        lines += ['', 'Entrada del consenso:', details.network_status_text]
        if details.microdescriptor_text:
            lines += ['', 'Microdescriptor:', details.microdescriptor_text]
        self._show('\n'.join(lines))

    def _show(self, text):
        self.result.SetValue(text)
        self.result.SetFocus()
