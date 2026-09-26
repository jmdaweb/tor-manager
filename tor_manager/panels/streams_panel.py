from .. import constants as C
from ..formatting import label, label_with_code, relay_name
from ..widgets import ListDetailPanel

FINISHED_STATUSES = ('CLOSED', 'FAILED')


def _stream_sort_key(stream):
    return int(stream.id) if stream.id.isdigit() else 0


class StreamsPanel(ListDetailPanel):
    def __init__(self, parent):
        super().__init__(
            parent,
            list_label='&Streams activos:',
            columns=[('ID', 60), ('Estado', 150), ('Destino', 300), ('Circuito', 80), ('Propósito', 160)],
            detail_label='&Detalles del stream seleccionado:',
            actions=[
                (C.ID_ATTACH_STREAM, '&Asociar a un circuito…'),
                (C.ID_CLOSE_STREAM, 'Ce&rrar stream…'),
                (C.ID_REFRESH_STREAMS, 'Ac&tualizar'),
            ],
            activate_id=C.ID_ATTACH_STREAM,
            delete_id=C.ID_CLOSE_STREAM,
            context_menu=[
                (C.ID_ATTACH_STREAM, 'Asociar a un circuito…'),
                (C.ID_CLOSE_STREAM, 'Cerrar stream…'),
            ],
        )
        self.circuit_provider = None

    def set_streams(self, streams):
        streams = [item for item in streams if item.status not in FINISHED_STATUSES]
        self.set_items([(item.id, item) for item in sorted(streams, key=_stream_sort_key)])

    def apply_event(self, stream):
        if stream.status in FINISHED_STATUSES:
            self.remove(stream.id)
        else:
            self.upsert(stream.id, stream)

    def streams_for_circuit(self, circuit_id):
        return [item for item in self.items() if item.circ_id == circuit_id]

    def columns_for(self, stream):
        return [
            stream.id,
            label(C.STREAM_STATUS_LABELS, stream.status),
            stream.target,
            stream.circ_id or 'sin asociar',
            label(C.STREAM_PURPOSE_LABELS, stream.purpose) or 'Usuario',
        ]

    def empty_detail(self):
        return 'No hay ningún stream seleccionado.'

    def format_detail(self, stream):
        lines = [
            'Stream: %s' % stream.id,
            'Estado: %s' % label_with_code(C.STREAM_STATUS_LABELS, stream.status),
            'Destino: %s' % stream.target,
        ]
        if stream.target_address:
            lines.append('Dirección de destino: %s' % stream.target_address)
        if stream.target_port:
            lines.append('Puerto de destino: %s' % stream.target_port)
        lines.append('Propósito: %s' % label_with_code(C.STREAM_PURPOSE_LABELS, stream.purpose))
        if stream.source_addr:
            lines.append('Origen de la conexión: %s' % stream.source_addr)
        if stream.reason:
            lines.append('Motivo del cierre: %s' % stream.reason)
        if stream.remote_reason:
            lines.append('Motivo remoto del cierre: %s' % stream.remote_reason)

        lines.append('')
        if not stream.circ_id:
            lines.append('El stream no está asociado a ningún circuito.')
        else:
            circuit = self.circuit_provider(stream.circ_id) if self.circuit_provider else None
            lines.append('Circuito: %s' % stream.circ_id)
            if circuit is not None:
                for position, (fingerprint, nickname) in enumerate(circuit.path, start=1):
                    lines.append('  %d. %s' % (position, relay_name(fingerprint, nickname)))
        return '\n'.join(lines)
