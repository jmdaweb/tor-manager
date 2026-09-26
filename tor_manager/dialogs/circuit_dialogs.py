"""Diálogos para crear y extender circuitos y para asociar streams."""

import re

import wx

from .. import constants as C
from ..errors import show_message
from ..formatting import label, path_summary
from .relay_dialogs import RelayPickerDialog


def circuit_description(circuit):
    return 'Circuito %s, %s, %s: %s' % (
        circuit.id,
        label(C.CIRC_STATUS_LABELS, circuit.status),
        label(C.CIRC_PURPOSE_LABELS, circuit.purpose),
        path_summary(circuit.path),
    )

_FINGERPRINT = re.compile(r'^[0-9A-Fa-f]{40}$')
_NICKNAME = re.compile(r'^[A-Za-z0-9]{1,19}$')


def parse_path(text):
    """Convierte el texto de la ruta en una lista de relés, o lanza ValueError."""
    relays = []
    for token in re.split(r'[\s,]+', text.strip()):
        if not token:
            continue
        relay = token.lstrip('$')
        if not (_FINGERPRINT.match(relay) or _NICKNAME.match(relay)):
            raise ValueError('«%s» no es una huella digital (40 caracteres hexadecimales) '
                             'ni un apodo de relé válido.' % token)
        relays.append(relay)
    return relays


class CircuitDialog(wx.Dialog):
    """Crea un circuito nuevo o extiende uno existente."""

    def __init__(self, parent, backend, circuit=None):
        self._extend = circuit is not None
        title = 'Extender el circuito %s' % circuit.id if self._extend else 'Nuevo circuito'
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.backend = backend

        sizer = wx.BoxSizer(wx.VERTICAL)
        if self._extend:
            info = wx.StaticText(self, label=circuit_description(circuit))
            info.Wrap(520)
            sizer.Add(info, 0, wx.ALL, 8)
            self.purpose = None
        else:
            sizer.Add(wx.StaticText(self, label='&Propósito del circuito:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.purpose = wx.Choice(self, choices=[text for _, text in C.CIRCUIT_PURPOSE_CHOICES])
            self.purpose.SetSelection(0)
            sizer.Add(self.purpose, 0, wx.EXPAND | wx.ALL, 8)

        if self._extend:
            label = '&Relés que se añadirán al final del circuito, en orden:'
        else:
            label = '&Ruta, en orden (guardia, intermedio, salida). Déjela vacía para que Tor la elija:'
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.path = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(520, 70))
        sizer.Add(self.path, 1, wx.EXPAND | wx.ALL, 8)
        hint = wx.StaticText(self, label='Escriba huellas digitales o apodos separados por comas o espacios.')
        sizer.Add(hint, 0, wx.LEFT | wx.RIGHT, 8)
        add_relay = wx.Button(self, label='&Añadir un relé de la lista…')
        sizer.Add(add_relay, 0, wx.ALL, 8)

        self.await_build = wx.CheckBox(self, label='&Esperar a que el circuito esté construido (hasta 60 segundos)')
        sizer.Add(self.await_build, 0, wx.ALL, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()

        add_relay.Bind(wx.EVT_BUTTON, self._on_add_relay)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        (self.path if self._extend else self.purpose).SetFocus()

    def _on_add_relay(self, event):
        with RelayPickerDialog(self, self.backend) as dialog:
            if dialog.ShowModal() == wx.ID_OK and dialog.get_selected() is not None:
                current = self.path.GetValue().strip()
                fingerprint = '$' + dialog.get_selected().fingerprint
                self.path.SetValue('%s, %s' % (current, fingerprint) if current else fingerprint)
        self.path.SetFocus()
        self.path.SetInsertionPointEnd()

    def _on_ok(self, event):
        try:
            relays = parse_path(self.path.GetValue())
        except ValueError as exc:
            show_message(self, str(exc), 'Ruta no válida', wx.ICON_ERROR)
            self.path.SetFocus()
            return
        if self._extend and not relays:
            show_message(self, 'Indique al menos un relé para extender el circuito.', 'Ruta vacía', wx.ICON_ERROR)
            self.path.SetFocus()
            return
        event.Skip()

    def get_result(self):
        """Devuelve (ruta, propósito, esperar)."""
        purpose = C.CIRCUIT_PURPOSE_CHOICES[self.purpose.GetSelection()][0] if self.purpose else 'general'
        return parse_path(self.path.GetValue()), purpose, self.await_build.IsChecked()


class AttachStreamDialog(wx.Dialog):
    def __init__(self, parent, stream, circuits):
        super().__init__(parent, title='Asociar el stream %s a un circuito' % stream.id)
        self._circuits = circuits

        sizer = wx.BoxSizer(wx.VERTICAL)
        info = wx.StaticText(self, label='Stream %s hacia %s.' % (stream.id, stream.target))
        sizer.Add(info, 0, wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Circuito construido:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.circuit = wx.Choice(self, choices=[circuit_description(item) for item in circuits])
        self.circuit.SetSelection(0)
        sizer.Add(self.circuit, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='Salto de sali&da (0 significa el último relé del circuito):'),
                  0, wx.LEFT | wx.RIGHT, 8)
        self.hop = wx.SpinCtrl(self, min=0, max=16, initial=0)
        sizer.Add(self.hop, 0, wx.ALL, 8)
        note = wx.StaticText(self, label='Tor solo acepta asociar streams nuevos o desvinculados. Para decidir '
                                         'usted el circuito de cada conexión, active «Asociar streams '
                                         'manualmente» en el menú Streams.')
        note.Wrap(480)
        sizer.Add(note, 0, wx.ALL, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.circuit.SetFocus()

    def get_result(self):
        """Devuelve (id del circuito, salto de salida o None)."""
        circuit = self._circuits[self.circuit.GetSelection()]
        return circuit.id, self.hop.GetValue() or None
