from .. import constants as C
from ..formatting import format_utc_datetime, label, label_with_code, path_summary, relay_name
from ..widgets import ListDetailPanel

FINISHED_STATUSES = ('CLOSED', 'FAILED')


def _circuit_sort_key(circuit):
    return int(circuit.id) if circuit.id.isdigit() else 0


class CircuitsPanel(ListDetailPanel):
    def __init__(self, parent):
        super().__init__(
            parent,
            list_label='&Circuitos abiertos:',
            columns=[('ID', 60), ('Estado', 130), ('Propósito', 200), ('Ruta', 360), ('Creado', 90)],
            detail_label='&Detalles del circuito seleccionado:',
            actions=[
                (C.ID_NEW_CIRCUIT, '&Nuevo circuito…'),
                (C.ID_EXTEND_CIRCUIT, '&Extender…'),
                (C.ID_CLOSE_CIRCUIT, 'Ce&rrar circuito'),
                (C.ID_REFRESH_CIRCUITS, '&Actualizar'),
            ],
            delete_id=C.ID_CLOSE_CIRCUIT,
            context_menu=[
                (C.ID_NEW_CIRCUIT, 'Nuevo circuito…'),
                (C.ID_EXTEND_CIRCUIT, 'Extender circuito…'),
                (C.ID_REPURPOSE_CIRCUIT, 'Cambiar propósito…'),
                None,
                (C.ID_CLOSE_CIRCUIT, 'Cerrar circuito'),
                (C.ID_CLOSE_CIRCUIT_IF_UNUSED, 'Cerrar si no se usa'),
            ],
        )
        self.streams_provider = None

    def set_circuits(self, circuits):
        circuits = [item for item in circuits if item.status not in FINISHED_STATUSES]
        self.set_items([(item.id, item) for item in sorted(circuits, key=_circuit_sort_key)])

    def apply_event(self, circuit):
        if circuit.status in FINISHED_STATUSES:
            self.remove(circuit.id)
        else:
            self.upsert(circuit.id, circuit)

    def built_circuits(self):
        return [item for item in self.items() if item.status == 'BUILT']

    def columns_for(self, circuit):
        return [
            circuit.id,
            label(C.CIRC_STATUS_LABELS, circuit.status),
            label(C.CIRC_PURPOSE_LABELS, circuit.purpose),
            path_summary(circuit.path),
            format_utc_datetime(circuit.created, with_date=False),
        ]

    def empty_detail(self):
        return 'No hay ningún circuito seleccionado.'

    def format_detail(self, circuit):
        lines = [
            'Circuito: %s' % circuit.id,
            'Estado: %s' % label_with_code(C.CIRC_STATUS_LABELS, circuit.status),
            'Propósito: %s' % label_with_code(C.CIRC_PURPOSE_LABELS, circuit.purpose),
        ]
        if circuit.created:
            lines.append('Creado: %s' % format_utc_datetime(circuit.created))
        if circuit.build_flags:
            flags = ', '.join(C.CIRC_BUILD_FLAG_LABELS.get(flag, flag) for flag in circuit.build_flags)
            lines.append('Opciones de construcción: %s' % flags)
        if circuit.hs_state:
            lines.append('Estado del servicio onion: %s' % circuit.hs_state)
        if circuit.rend_query:
            lines.append('Dirección onion consultada: %s' % circuit.rend_query)
        if circuit.socks_username:
            lines.append('Usuario SOCKS (aislamiento): %s' % circuit.socks_username)
        if circuit.reason:
            lines.append('Motivo del cierre: %s' % circuit.reason)
        if circuit.remote_reason:
            lines.append('Motivo remoto del cierre: %s' % circuit.remote_reason)

        lines.append('')
        lines.append('Ruta (%d saltos):' % len(circuit.path))
        for position, (fingerprint, nickname) in enumerate(circuit.path, start=1):
            lines.append('  %d. %s' % (position, relay_name(fingerprint, nickname)))

        streams = self.streams_provider(circuit.id) if self.streams_provider else []
        lines.append('')
        if streams:
            lines.append('Streams que usan este circuito (%d):' % len(streams))
            for stream in streams:
                lines.append('  Stream %s hacia %s' % (stream.id, stream.target))
        else:
            lines.append('Ningún stream usa este circuito.')
        return '\n'.join(lines)
