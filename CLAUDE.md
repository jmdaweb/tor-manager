# CLAUDE.md

Guía para trabajar con el código de Tor Manager, un gestor de Tor para Windows con interfaz wxPython accesible para lectores de pantalla, basado en la biblioteca Stem.

## Idioma

- La interfaz, los mensajes, los comentarios y la documentación están en español, con tildes y signos de apertura (¿, ¡). Los identificadores del código están en inglés.
- Las respuestas de Tor (en inglés) se muestran tal cual como «Respuesta de Tor: …» dentro de los mensajes en español.

## Órdenes habituales

```powershell
# Ejecutar desde el código fuente
python -m tor_manager        # o bien: python main.py

# Comprobar que todo compila e importa
python -m compileall -q tor_manager
python -c "import tor_manager.app"

# Generar el ejecutable (ver README.md)
pyinstaller --noconfirm --windowed --name TorManager main.py
```

No hay suite de pruebas automatizada ni linter configurado. Dependencias: `requirements.txt` (wxPython y Stem). Probado con Python 3.13, wxPython 4.3.1, Stem 1.8.2 y Tor 0.4.9 en Windows 11.

## Estructura

```
main.py                  Punto de entrada (también para PyInstaller)
resources/tor/           Aquí el usuario coloca tor.exe (Tor Expert Bundle); no se versiona el binario
tor_manager/
  app.py                 TorManagerApp: instancia única, excepthook, diálogo de arranque inicial
  main_frame.py          Ventana principal: menús, pestañas, barra de estado, eventos de Tor, cierre
  tor_backend.py         TorBackend: proceso de Tor y Controller de Stem (sin wx)
  tor_events.py          StemEventBridge: eventos de Stem -> eventos wx en el hilo de la interfaz
  async_utils.py         run_in_thread, call_after, call_in_gui_and_wait
  models.py              Dataclasses planas que viajan entre backend e interfaz
  exceptions.py          Excepciones propias; el backend traduce las de Stem a estas
  errors.py              describe_exception, show_error, show_message, confirm
  torrc.py               torrc de fábrica y argumentos de línea de órdenes para lanzar Tor
  settings.py            AppSettings (JSON)
  paths.py               Rutas: carpeta de configuración, tor.exe incorporado, geoip
  constants.py           IDs de órdenes y tablas de textos (estados, propósitos, motivos…)
  formatting.py          Formato de bytes, fechas, rutas de circuitos (sin wx)
  widgets.py             ListDetailPanel, readonly_text, portapapeles, guardar texto
  icons.py               Iconos dibujados en tiempo de ejecución (no hay ficheros .ico)
  taskbar.py             Icono de la bandeja del sistema
  logging_setup.py       Registro a fichero y a una cola que drena el panel de registro
  panels/                Una pestaña por fichero (circuitos, streams, servicios onion, configuración, registro)
  dialogs/               Diálogos: arranque, autenticación, ajustes, circuitos, onion, configuración, consultas
```

## Datos del usuario

`paths.user_data_dir()` es la carpeta `TorManagerConfig`, junto al programa (junto a `TorManager.exe` en la versión compilada y en la raíz del repositorio al ejecutar desde el código fuente). Contiene `settings.json` (puede incluir la contraseña de control en claro si el usuario marcó «Recordar»), `torrc`, `tor-data/`, `onion-services/` y `tor-manager.log`. Nunca debe versionarse.

## Reglas de arquitectura

- **Solo `tor_backend.py` y `tor_events.py` importan `stem`.** El resto de la aplicación trabaja con los modelos de `models.py` y las excepciones de `exceptions.py`.
- **`tor_backend.py` no importa wx** (ni directa ni indirectamente: `formatting.py` no debe importar `constants.py`, que carga wx). Compruébalo con `python -c "import sys, tor_manager.tor_backend; print('wx' in sys.modules)"`.
- **Ninguna llamada a Stem en el hilo de wx.** Toda llamada al backend se hace con `async_utils.run_in_thread(fn, …, on_success=…, on_error=…, owner=ventana)`; los callbacks llegan siempre al hilo de wx y se omiten si `owner` ya se destruyó. En `MainFrame` se usa el envoltorio `_run(…, busy=…, done=…, quiet=…)`, que además actualiza la barra de estado y el registro.
- **Ningún widget se toca desde otro hilo.** Los listeners de Stem se ejecutan en su hilo lector; `StemEventBridge` los convierte en modelos y los entrega con `call_after` + `wx.PostEvent`.
- Los métodos públicos de `TorBackend` se envuelven automáticamente (`_translate_public_methods`) para traducir excepciones de Stem. Los métodos privados deben empezar por `_`.
- No hay bloqueo global sobre el Controller: Stem ya serializa sus mensajes, y bloquear impediría otras operaciones durante `await_build` o la espera de publicación de un servicio onion. `TorBackend._lock` solo protege el estado del ciclo de vida.

## Particularidades de Stem y Tor (no revertir)

- **Lanzamiento**: `stem.process.launch_tor` con un torrc real en disco (SAVECONF necesita un fichero), `completion_percent=0`, `take_ownership=True`, `close_output=False` y sin `timeout` (Stem no lo admite en Windows). El resto del arranque se sigue por el puerto de control; la salida estándar se vacía en hilos propios para que Tor no se bloquee.
- Las opciones esenciales (puertos, `DataDirectory`, autenticación, geoip, opciones adicionales) se pasan por la línea de órdenes y prevalecen sobre el torrc. Solo se añade `+Log notice stdout` si el torrc no registra ya en stdout (si no, las líneas se duplicarían en cada SAVECONF).
- `_StemSubprocess` sustituye a `subprocess` dentro de `stem.process` y `stem.util.system`: oculta la consola de tor.exe (robaba el foco al lector de pantalla) y registra el proceso en arranque para poder cancelarlo.
- `stem.util.system.is_windows()` se precalcula al importar el backend: `platform.system()` usa WMI/COM la primera vez y fallaba desde un hilo secundario durante un diálogo modal.
- **Autenticación**: solo `stem.connection.authenticate()` llama a `controller._post_authentication()`. Tras `authenticate_none/password/cookie/safecookie` hay que llamarlo a mano; si no, Stem no activa los eventos ni envía TAKEOWNERSHIP.
- **Valores de SETCONF**: Stem los envía entre comillas sin escapar, y Tor interpreta las barras invertidas. Usa siempre `_escape_conf_value` (ya lo hace `set_option`).
- **Servicios onion persistentes**: no se usan `create_hidden_service`, `remove_hidden_service` ni `set_hidden_service_conf` de Stem (envían las rutas de Windows sin escapar). Se lee con `get_hidden_service_conf()` y se escribe con `_apply_hidden_service_conf`. Antes hay que crear el directorio: Tor solo crea el último nivel y, si falla, **se cierra** («Acting on config options left us in a broken state»).
- **Servicios efímeros con espera de publicación**: se escuchan los eventos HS_DESC en el backend en lugar de usar `await_publication` de Stem, que lanza `Timeout` sin devolver la clave privada del servicio ya creado.
- `get_hidden_service_conf` falla con destinos que no son IPv4; hay una lectura alternativa en `_raw_hidden_service_conf`.
- La contraseña de control se cifra con `hash_control_password` (equivalente a `tor --hash-password`).

## Convenciones de interfaz y accesibilidad

- Solo controles nativos de wx. Cada control se crea **justo después** de su `wx.StaticText`: así Windows usa la etiqueta como nombre accesible. Los mnemónicos (`&`) no deben repetirse dentro de una misma ventana.
- La información que devuelve Tor se muestra en cuadros de texto de solo lectura (`widgets.readonly_text`), nunca solo en etiquetas o celdas. Usa `set_text_if_changed` para no mover el cursor del lector de pantalla sin necesidad.
- Las pestañas con lista heredan de `ListDetailPanel` (lista en modo informe, botones de acción, cuadro de detalle, Supr, Intro y menú contextual). Las actualizaciones por eventos usan `upsert`/`remove`, sin reconstruir la lista entera.
- Toda acción debe estar en la barra de menús; los botones y menús contextuales son atajos. Para añadir una acción: ID en `constants.py`, entrada en `_build_menu`, manejador en el diccionario de `_bind_events` (se enlaza a la vez `EVT_MENU` y `EVT_BUTTON`) y, si habla con Tor, método público en `TorBackend`.
- Errores, avisos y confirmaciones pasan por `errors.py` (`wx.MessageDialog`), nunca `wx.MessageBox` suelto. Las acciones destructivas piden confirmación. Las acciones largas informan en la barra de estado.
- Los menús 1 a 5 (Circuitos…Control) y las pestañas que dependen de Tor se desactivan sin conexión (`MainFrame._set_connected`).

## Ciclo de vida

- Al salir (botón cerrar, Archivo > Salir o Salir en la bandeja) todo pasa por `EVT_CLOSE`: se destruye el icono de la bandeja, se ejecuta `backend.shutdown()` en segundo plano y la ventana se destruye al terminar (con un límite de 9 s). Si el sistema cierra la sesión (`CanVeto()` falso), el cierre es síncrono.
- `shutdown()` envía SHUTDOWN y escala a `terminate`/`kill` si Tor no termina. Si la aplicación se conectó a un Tor existente, no lo detiene; solo restablece `__LeaveStreamsUnattached` si lo activó.
- Cancelar el diálogo de arranque detiene cualquier Tor a medio iniciar; el backend comprueba `_abort_requested` bajo `_lock` para no dejar procesos huérfanos.

## Cómo probar

- Hay que probar con un Tor real. Usa puertos que no choquen con otro Tor (por ejemplo, 19050/19051) y una carpeta de datos temporal: en los scripts de prueba se puede redirigir la configuración con `paths.user_data_dir = lambda: carpeta_temporal` antes de importar el resto de la aplicación.
- Los flujos de interfaz se pueden automatizar con `wx.CallLater`: localizar el diálogo modal en `wx.GetTopLevelWindows()`, rellenar sus controles y llamar a `EndModal`. No llames a `TaskBarIcon.CreatePopupMenu()` directamente desde Python: provoca un fallo de acceso a memoria.
- Casos que conviene cubrir tras cambios en el backend: cookie y contraseña (incluida una incorrecta), conexión a un Tor existente, servicios persistentes con rutas con espacios, cancelación durante el arranque y comprobar que no quedan procesos `tor.exe` tras salir.
