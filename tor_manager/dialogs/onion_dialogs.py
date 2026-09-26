"""Creación de servicios onion efímeros y persistentes, y presentación del resultado."""

import ipaddress
import os

import wx

from .. import paths
from ..errors import show_error, show_message
from ..models import ONION_EPHEMERAL
from ..widgets import copy_to_clipboard, readonly_text, save_text_to_file

KEY_CHOICES = [
    ('new-v3', 'Generar una clave nueva ED25519-V3 (onion v3, recomendado)'),
    ('new-best', 'Generar una clave nueva del tipo que elija Tor'),
    ('existing', 'Usar una clave privada existente'),
]
_KEY_TYPES = ('ED25519-V3', 'RSA1024')


def _valid_port(text):
    return text.isdigit() and 1 <= int(text) <= 65535


def parse_target(text, ipv4_only):
    """Valida un destino: vacío, «puerto» o «dirección:puerto». Devuelve (dirección, puerto)."""
    text = text.strip()
    if not text:
        return None, None
    if _valid_port(text):
        return None, int(text)
    address, separator, port = text.rpartition(':')
    if not separator or not _valid_port(port):
        raise ValueError('El destino debe ser un puerto o «dirección:puerto», por ejemplo 127.0.0.1:8080.')
    address = address.strip('[]')
    if ipv4_only:
        try:
            ipaddress.IPv4Address(address)
        except ValueError:
            raise ValueError('Para servicios persistentes, la dirección de destino debe ser una IPv4, '
                             'por ejemplo 127.0.0.1.') from None
    elif not address:
        raise ValueError('Falta la dirección de destino.')
    return address, int(port)


class PortMappingDialog(wx.Dialog):
    def __init__(self, parent, ipv4_only, port=80, target=''):
        super().__init__(parent, title='Correspondencia de puertos')
        self._ipv4_only = ipv4_only
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label='&Puerto virtual (el que usan los visitantes del servicio):'),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.port = wx.SpinCtrl(self, min=1, max=65535, initial=port)
        sizer.Add(self.port, 0, wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='&Destino local (puerto o dirección:puerto; vacío = mismo puerto '
                                            'en 127.0.0.1):'), 0, wx.LEFT | wx.RIGHT, 8)
        self.target = wx.TextCtrl(self, value=target)
        sizer.Add(self.target, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.port.SetFocus()
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_ok(self, event):
        try:
            parse_target(self.target.GetValue(), self._ipv4_only)
        except ValueError as exc:
            show_message(self, str(exc), 'Destino no válido', wx.ICON_ERROR)
            self.target.SetFocus()
            return
        event.Skip()

    def get_result(self):
        return self.port.GetValue(), self.target.GetValue().strip()


class OnionServiceCreateDialog(wx.Dialog):
    def __init__(self, parent, kind):
        self.kind = kind
        ephemeral = kind == ONION_EPHEMERAL
        title = 'Añadir un servicio onion efímero' if ephemeral else 'Añadir un servicio onion persistente'
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._mappings = []

        sizer = wx.BoxSizer(wx.VERTICAL)
        if ephemeral:
            intro = ('Los servicios efímeros se crean con ADD_ONION: no se escriben en el disco y desaparecen '
                     'al cerrar la conexión de control o al detener Tor.')
        else:
            intro = ('Los servicios persistentes se configuran con HiddenServiceDir: Tor guarda sus claves en '
                     'el directorio indicado y conservan la misma dirección tras reiniciar.')
        text = wx.StaticText(self, label=intro)
        text.Wrap(560)
        sizer.Add(text, 0, wx.ALL, 8)

        sizer.Add(wx.StaticText(self, label='Co&rrespondencia de puertos:'), 0, wx.LEFT | wx.RIGHT, 8)
        self.ports = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 110))
        self.ports.InsertColumn(0, 'Puerto virtual', width=130)
        self.ports.InsertColumn(1, 'Destino', width=300)
        sizer.Add(self.ports, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        add = wx.Button(self, label='&Añadir puerto…')
        edit = wx.Button(self, label='&Modificar…')
        remove = wx.Button(self, label='&Quitar')
        for button in (add, edit, remove):
            buttons.Add(button, 0, wx.RIGHT, 6)
        sizer.Add(buttons, 0, wx.LEFT | wx.RIGHT, 8)

        if ephemeral:
            self._build_ephemeral(sizer)
        else:
            self._build_persistent(sizer)

        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()

        add.Bind(wx.EVT_BUTTON, self._on_add)
        edit.Bind(wx.EVT_BUTTON, self._on_edit)
        remove.Bind(wx.EVT_BUTTON, self._on_remove)
        self.ports.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

        self._add_mapping(80, '127.0.0.1:8080')
        self.ports.Select(0)
        self.ports.Focus(0)
        self.ports.SetFocus()

    def _build_ephemeral(self, sizer):
        sizer.Add(wx.StaticText(self, label='C&lave del servicio:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.key_choice = wx.Choice(self, choices=[text for _, text in KEY_CHOICES])
        self.key_choice.SetSelection(0)
        sizer.Add(self.key_choice, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label='Clave privada e&xistente (por ejemplo «ED25519-V3:…»):'),
                  0, wx.LEFT | wx.RIGHT, 8)
        self.key_text = wx.TextCtrl(self)
        self.key_text.Disable()
        sizer.Add(self.key_text, 0, wx.EXPAND | wx.ALL, 8)

        self.discard_key = wx.CheckBox(self, label='&No devolver la clave privada (el servicio no podrá recrearse)')
        self.detached = wx.CheckBox(self, label='&Separado: mantenerlo activo aunque se cierre este programa '
                                                'mientras Tor siga en ejecución')
        self.await_publication = wx.CheckBox(self, label='&Esperar a que se publique el descriptor '
                                                         '(hasta 2 minutos)')
        for checkbox in (self.discard_key, self.detached, self.await_publication):
            sizer.Add(checkbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=6)
        grid.AddGrowableCol(1)
        grid.Add(wx.StaticText(self, label='Máximo de s&treams simultáneos (0 = sin límite):'), 0,
                 wx.ALIGN_CENTER_VERTICAL)
        self.max_streams = wx.SpinCtrl(self, min=0, max=65535, initial=0)
        grid.Add(self.max_streams, 0)
        grid.Add(wx.StaticText(self, label='Clave pública de cliente &autorizado (x25519 en base32, opcional):'),
                 0, wx.ALIGN_CENTER_VERTICAL)
        self.client_auth = wx.TextCtrl(self)
        grid.Add(self.client_auth, 1, wx.EXPAND)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        self.key_choice.Bind(wx.EVT_CHOICE, self._on_key_choice)

    def _build_persistent(self, sizer):
        sizer.Add(wx.StaticText(self, label='&Directorio del servicio (Tor lo crea si no existe):'),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.directory = wx.TextCtrl(self, value=self._suggest_directory())
        row.Add(self.directory, 1, wx.RIGHT, 6)
        browse = wx.Button(self, label='E&xaminar…')
        row.Add(browse, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        self.save_to_disk = wx.CheckBox(self, label='&Guardar la configuración en el torrc para que el servicio '
                                                    'se mantenga al reiniciar Tor')
        self.save_to_disk.SetValue(True)
        sizer.Add(self.save_to_disk, 0, wx.ALL, 8)
        browse.Bind(wx.EVT_BUTTON, self._on_browse)

    @staticmethod
    def _suggest_directory():
        base = paths.default_onion_services_dir()
        index = 1
        while os.path.exists(os.path.join(base, 'servicio-%d' % index)):
            index += 1
        return os.path.join(base, 'servicio-%d' % index)

    # --- Correspondencia de puertos ------------------------------------------

    def _add_mapping(self, port, target):
        index = self.ports.InsertItem(self.ports.GetItemCount(), str(port))
        self.ports.SetItem(index, 1, target or '127.0.0.1:%d' % port)
        self._mappings.append((port, target))
        return index

    def _on_add(self, event):
        with PortMappingDialog(self, self.kind != ONION_EPHEMERAL, port=80, target='') as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                port, target = dialog.get_result()
                index = self._add_mapping(port, target)
                self.ports.Select(index)
                self.ports.Focus(index)
        self.ports.SetFocus()

    def _on_edit(self, event):
        index = self.ports.GetFirstSelected()
        if index < 0:
            return
        port, target = self._mappings[index]
        with PortMappingDialog(self, self.kind != ONION_EPHEMERAL, port=port, target=target) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                port, target = dialog.get_result()
                self._mappings[index] = (port, target)
                self.ports.SetItem(index, 0, str(port))
                self.ports.SetItem(index, 1, target or '127.0.0.1:%d' % port)
        self.ports.SetFocus()

    def _on_remove(self, event):
        index = self.ports.GetFirstSelected()
        if index < 0:
            return
        self.ports.DeleteItem(index)
        del self._mappings[index]
        if self._mappings:
            index = min(index, len(self._mappings) - 1)
            self.ports.Select(index)
            self.ports.Focus(index)
        self.ports.SetFocus()

    # --- Otros controles -----------------------------------------------------

    def _on_key_choice(self, event):
        existing = KEY_CHOICES[self.key_choice.GetSelection()][0] == 'existing'
        self.key_text.Enable(existing)
        if existing:
            self.key_text.SetFocus()

    def _on_browse(self, event):
        with wx.DirDialog(self, 'Elija el directorio del servicio onion', self.directory.GetValue()) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.directory.SetValue(dialog.GetPath())
        self.directory.SetFocus()

    def _on_ok(self, event):
        try:
            self.get_spec()
        except ValueError as exc:
            show_message(self, str(exc), 'Datos no válidos', wx.ICON_ERROR)
            return
        event.Skip()

    def _key_spec(self):
        choice = KEY_CHOICES[self.key_choice.GetSelection()][0]
        if choice == 'new-v3':
            return 'NEW', 'ED25519-V3'
        if choice == 'new-best':
            return 'NEW', 'BEST'
        text = ''.join(self.key_text.GetValue().split())
        if not text:
            raise ValueError('Pegue la clave privada existente del servicio.')
        key_type, separator, blob = text.partition(':')
        if separator and key_type.upper() in _KEY_TYPES:
            return key_type.upper(), blob
        return 'ED25519-V3', text

    def get_spec(self):
        if not self._mappings:
            raise ValueError('Añada al menos una correspondencia de puertos.')
        virtual_ports = [port for port, _ in self._mappings]
        if len(set(virtual_ports)) != len(virtual_ports):
            raise ValueError('Hay puertos virtuales repetidos.')

        if self.kind == ONION_EPHEMERAL:
            key_type, key_content = self._key_spec()
            return {
                'ports': list(self._mappings),
                'key_type': key_type,
                'key_content': key_content,
                'discard_key': self.discard_key.IsChecked(),
                'detached': self.detached.IsChecked(),
                'await_publication': self.await_publication.IsChecked(),
                'max_streams': self.max_streams.GetValue() or None,
                'client_auth_v3': self.client_auth.GetValue().strip() or None,
            }

        directory = self.directory.GetValue().strip()
        if not directory:
            raise ValueError('Indique el directorio del servicio.')
        ports = []
        for port, target in self._mappings:
            address, target_port = parse_target(target, ipv4_only=True)
            ports.append((port, address, target_port))
        return {'directory': directory, 'ports': ports, 'save_to_disk': self.save_to_disk.IsChecked()}


def describe_created_service(created):
    ephemeral = created.kind == ONION_EPHEMERAL
    lines = ['Servicio onion %s creado.' % ('efímero' if ephemeral else 'persistente'), '']
    lines.append('Dirección: %s' % (created.address or 'todavía no disponible; actualice la lista en unos segundos'))
    lines.append('Correspondencia de puertos:')
    for port, target in created.ports:
        lines.append('  Puerto virtual %s → %s' % (port, target))

    if ephemeral:
        lines.append('Separado de la conexión de control: %s' % ('sí' if created.detached else 'no'))
        if created.publication is not None:
            published, message = created.publication
            lines.append('Publicación del descriptor: %s. %s' % ('confirmada' if published else 'sin confirmar',
                                                                 message))
        if created.private_key:
            lines += [
                '',
                'Clave privada (%s):' % created.private_key_type,
                '%s:%s' % (created.private_key_type, created.private_key),
                '',
                'Guarde esta clave en un lugar seguro: permite volver a crear el servicio con la misma '
                'dirección (opción «Usar una clave privada existente»). Quien la obtenga podrá suplantar '
                'el servicio.',
            ]
        else:
            lines.append('Tor no ha devuelto la clave privada.')
        if created.client_auth:
            lines.append('')
            lines.append('Credenciales de clientes:')
            for name, credential in created.client_auth.items():
                lines.append('  %s: %s' % (name, credential))
    else:
        lines.append('Directorio de claves: %s' % created.directory)
        if created.saved is True:
            lines.append('La configuración se ha guardado en el torrc.')
        elif created.saved:
            lines.append('No se pudo guardar la configuración en el torrc: %s' % created.saved)
        else:
            lines.append('La configuración no se ha guardado en el torrc; se perderá al reiniciar Tor '
                         'salvo que use Configuración > Guardar configuración en disco.')
    return '\n'.join(lines)


class OnionServiceResultDialog(wx.Dialog):
    def __init__(self, parent, created):
        super().__init__(parent, title='Servicio onion creado', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._created = created
        self._text = describe_created_service(created)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label='&Información del servicio:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.info = readonly_text(self, value=self._text)
        self.info.SetMinSize((620, 300))
        sizer.Add(self.info, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy_address = wx.Button(self, label='Copiar la &dirección')
        copy_address.Enable(bool(created.address))
        copy_all = wx.Button(self, label='Copiar &todo')
        save = wx.Button(self, label='&Guardar en un fichero…')
        for button in (copy_address, copy_all, save):
            buttons.Add(button, 0, wx.RIGHT, 6)
        sizer.Add(buttons, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.CreateSeparatedButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetEscapeId(wx.ID_CLOSE)
        self.CentreOnParent()

        copy_address.Bind(wx.EVT_BUTTON, lambda event: copy_to_clipboard(created.address))
        copy_all.Bind(wx.EVT_BUTTON, lambda event: copy_to_clipboard(self._text))
        save.Bind(wx.EVT_BUTTON, self._on_save)
        self.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
        self.info.SetFocus()

    def _on_save(self, event):
        try:
            save_text_to_file(self, self._text, 'Guardar la información del servicio onion',
                              default_file='servicio-onion.txt')
        except OSError as exc:
            show_error(self, exc, 'No se pudo guardar el fichero')
