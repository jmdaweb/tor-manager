import wx

from .. import constants as C
from ..formatting import yes_no
from ..widgets import ListDetailPanel

_MAX_COLUMN_TEXT = 120


def _values_text(values):
    if values is None:
        return '(no disponible)'
    if not values:
        return '(sin valor)'
    text = ' | '.join(values)
    return text if len(text) <= _MAX_COLUMN_TEXT else text[:_MAX_COLUMN_TEXT - 1] + '…'


class ConfigPanel(ListDetailPanel):
    def __init__(self, parent):
        self._all_options = []
        self._filter_timer = None
        super().__init__(
            parent,
            list_label='&Parámetros de configuración de Tor:',
            columns=[('Parámetro', 230), ('Valor actual', 330), ('Modificado', 90), ('Tipo', 110)],
            detail_label='&Detalles del parámetro seleccionado:',
            actions=[
                (C.ID_EDIT_OPTION, '&Establecer valor…'),
                (C.ID_RESET_OPTION, '&Restablecer al predeterminado'),
                (C.ID_SAVE_CONFIG, '&Guardar en disco'),
                (C.ID_REFRESH_CONFIG, 'Ac&tualizar'),
            ],
            activate_id=C.ID_EDIT_OPTION,
            delete_id=C.ID_RESET_OPTION,
            context_menu=[
                (C.ID_EDIT_OPTION, 'Establecer valor…'),
                (C.ID_RESET_OPTION, 'Restablecer al valor predeterminado'),
            ],
        )

    def add_header_controls(self, sizer):
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='&Filtrar por nombre:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.filter_text = wx.TextCtrl(self)
        row.Add(self.filter_text, 1, wx.RIGHT, 12)
        self.only_modified = wx.CheckBox(self, label='Mostrar solo los parámetros &modificados')
        row.Add(self.only_modified, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
        self.filter_text.Bind(wx.EVT_TEXT, self._on_filter_text)
        self.only_modified.Bind(wx.EVT_CHECKBOX, lambda event: self._apply_filter())

    def set_options(self, options):
        self._all_options = list(options)
        self._apply_filter()

    def clear(self):
        self._all_options = []
        super().clear()

    def option_names(self):
        return [option.name for option in self._all_options]

    def find_option(self, name):
        lowered = name.lower()
        for option in self._all_options:
            if option.name.lower() == lowered:
                return option
        return None

    def _on_filter_text(self, event):
        # espera a que se deje de escribir para no reconstruir la lista en cada tecla
        if self._filter_timer is not None:
            self._filter_timer.Stop()
        self._filter_timer = wx.CallLater(400, self._apply_filter)

    def _apply_filter(self):
        text = self.filter_text.GetValue().strip().lower()
        only_modified = self.only_modified.IsChecked()
        visible = [
            option for option in self._all_options
            if (not text or text in option.name.lower()) and (not only_modified or option.modified)
        ]
        self.set_items([(option.name, option) for option in visible])

    def columns_for(self, option):
        return [option.name, _values_text(option.values), yes_no(option.modified), option.type]

    def empty_detail(self):
        return 'No hay ningún parámetro seleccionado.'

    def format_detail(self, option):
        lines = [
            'Parámetro: %s' % option.name,
            'Tipo: %s' % (option.type or 'desconocido'),
            'Modificado respecto al valor predeterminado: %s' % yes_no(option.modified),
            '',
        ]
        if option.values is None:
            lines.append('Valor actual: no se pudo consultar.')
        elif not option.values:
            lines.append('Valor actual: sin valor.')
        else:
            lines.append('Valores actuales:')
            lines.extend('  %s' % value for value in option.values)
        if option.defaults:
            lines.append('Valores predeterminados:')
            lines.extend('  %s' % value for value in option.defaults)
        else:
            lines.append('Valor predeterminado: sin valor.')
        if option.description:
            lines.append('')
            lines.append('Descripción: %s' % option.description)
        return '\n'.join(lines)
