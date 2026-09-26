from .. import constants as C
from ..models import ONION_EPHEMERAL
from ..widgets import ListDetailPanel


def service_key(service):
    if service.kind == ONION_EPHEMERAL:
        return (service.kind, service.service_id)
    return (service.kind, service.directory)


def _ports_text(ports):
    if not ports:
        return 'desconocidos'
    return ', '.join('%s → %s' % (port, target) for port, target in ports)


class OnionServicesPanel(ListDetailPanel):
    def __init__(self, parent):
        super().__init__(
            parent,
            list_label='&Servicios onion:',
            columns=[('Tipo', 190), ('Dirección', 420), ('Puertos', 220)],
            detail_label='&Detalles del servicio seleccionado:',
            actions=[
                (C.ID_ADD_EPHEMERAL, 'Añadir &efímero…'),
                (C.ID_ADD_PERSISTENT, 'Añadir &persistente…'),
                (C.ID_REMOVE_SERVICE, 'E&liminar'),
                (C.ID_COPY_ADDRESS, '&Copiar dirección'),
                (C.ID_REFRESH_SERVICES, 'Ac&tualizar'),
            ],
            activate_id=C.ID_COPY_ADDRESS,
            delete_id=C.ID_REMOVE_SERVICE,
            context_menu=[
                (C.ID_COPY_ADDRESS, 'Copiar dirección'),
                (C.ID_REMOVE_SERVICE, 'Eliminar servicio'),
                None,
                (C.ID_ADD_EPHEMERAL, 'Añadir servicio efímero…'),
                (C.ID_ADD_PERSISTENT, 'Añadir servicio persistente…'),
            ],
        )

    def set_services(self, services):
        self.set_items([(service_key(item), item) for item in services])

    def columns_for(self, service):
        if service.kind == ONION_EPHEMERAL:
            kind = 'Efímero separado' if service.detached else 'Efímero'
        else:
            kind = 'Persistente'
        return [kind, service.address or '(dirección aún no disponible)', _ports_text(service.ports)]

    def empty_detail(self):
        return 'No hay ningún servicio onion seleccionado.'

    def format_detail(self, service):
        lines = ['Dirección: %s' % (service.address or 'aún no disponible')]
        if service.kind == ONION_EPHEMERAL:
            lines.append('Tipo: efímero (se crea con ADD_ONION y no se guarda en el torrc)')
            if service.detached:
                lines.append('Separado: sí; sigue activo aunque se cierre la conexión de control, '
                             'hasta que Tor se detenga.')
            else:
                lines.append('Separado: no; desaparece al cerrar la conexión de control de este programa.')
            if service.key_type:
                lines.append('Tipo de clave: %s' % service.key_type)
            if not service.created_here:
                lines.append('Creado por otro controlador o en una sesión anterior; '
                             'Tor no informa de sus puertos.')
        else:
            lines.append('Tipo: persistente (configurado con HiddenServiceDir)')
            lines.append('Directorio de claves: %s' % service.directory)
            if not service.address:
                lines.append('La dirección se lee del fichero «hostname» del directorio; '
                             'no se ha podido leer todavía.')
            for key, value in sorted(service.options.items()):
                lines.append('%s: %s' % (key, value))

        lines.append('')
        if service.ports:
            lines.append('Correspondencia de puertos:')
            for port, target in service.ports:
                lines.append('  Puerto virtual %s → %s' % (port, target))
        else:
            lines.append('Correspondencia de puertos: desconocida.')
        return '\n'.join(lines)
