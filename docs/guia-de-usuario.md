# Guía de usuario de Tor Manager

Tor Manager le permite iniciar Tor en su equipo, ver y controlar lo que hace, publicar servicios onion y cambiar su configuración, todo desde una ventana de Windows que puede manejarse por completo con el teclado y un lector de pantalla.

## Contenido

1. [Antes de empezar](#1-antes-de-empezar)
2. [Iniciar Tor](#2-iniciar-tor)
3. [La ventana principal](#3-la-ventana-principal)
4. [Usar Tor desde otros programas](#4-usar-tor-desde-otros-programas)
5. [Circuitos](#5-circuitos)
6. [Streams](#6-streams)
7. [Servicios onion](#7-servicios-onion)
8. [Configuración de Tor](#8-configuración-de-tor)
9. [Menú Control](#9-menú-control)
10. [Información y registro](#10-información-y-registro)
11. [La bandeja del sistema](#11-la-bandeja-del-sistema)
12. [Ajustes del programa](#12-ajustes-del-programa)
13. [Detener, reiniciar y salir](#13-detener-reiniciar-y-salir)
14. [Dónde guarda el programa sus datos](#14-dónde-guarda-el-programa-sus-datos)
15. [Atajos de teclado](#15-atajos-de-teclado)
16. [Solución de problemas](#16-solución-de-problemas)

## 1. Antes de empezar

Para usar Tor Manager necesita un ejecutable de Tor, que puede obtener de dos maneras:

- **Tor incorporado**: si la carpeta del programa contiene `resources\tor\tor.exe`, Tor Manager lo encuentra solo. Si no lo tiene, descargue el Tor Expert Bundle para Windows desde la web del Proyecto Tor y extraiga su contenido dentro de la carpeta `resources` del programa (el fichero `resources\tor\LEEME.txt` lo explica).
- **Otro Tor**: puede indicar la ruta de cualquier `tor.exe`, o conectarse a un Tor que ya esté funcionando, por ejemplo el de Tor Browser.

Solo puede haber un Tor Manager abierto a la vez. Si lo abre otra vez, verá el aviso «Tor Manager ya se está ejecutando. Búsquelo en la bandeja del sistema».

## 2. Iniciar Tor

Al abrir el programa aparece el diálogo **Iniciar Tor**. La ventana principal no se muestra hasta que hay conexión con Tor.

### Elegir cómo usar Tor

Elija una de estas tres opciones con las flechas:

- **Iniciar el Tor incorporado en el programa**: debajo, un cuadro de solo lectura indica la ruta del `tor.exe` incorporado o avisa de que no se ha encontrado.
- **Iniciar un ejecutable de Tor personalizado**: escriba la ruta en **Ruta del ejecutable** o pulse **Examinar…** para buscarlo.
- **Conectar a un Tor que ya está en ejecución**: indique la **Dirección IP del puerto de control** (normalmente `127.0.0.1`) y el **Puerto de control**. El Tor de Tor Browser suele usar el puerto 9151, y un Tor instalado como servicio, el 9051.

En **Método de autenticación** elija cómo se identificará el programa ante Tor:

| Método | Cuándo usarlo |
|---|---|
| Automático (recomendado) | Tor Manager usa el mejor método que ofrezca Tor y solo le pide una contraseña si hace falta. |
| Sin autenticación | Tor no está protegido. |
| Contraseña | Tor está protegido con contraseña. |
| Cookie | Tor está protegido con un fichero de cookie que el programa puede leer. |
| SafeCookie | Igual que Cookie, pero con un intercambio más seguro. |

Si elige un método que Tor no ofrece, verá el error «Tor no ofrece el método de autenticación elegido» con la lista de métodos disponibles.

**Ajustes avanzados…** abre los ajustes del programa (puertos, directorio de datos, protección del Tor que se inicia…), que se explican en el [apartado 12](#12-ajustes-del-programa).

### Seguir el arranque

Pulse **Iniciar** (o Intro). A partir de ese momento:

- **Progreso del arranque de Tor** muestra una barra del 0 al 100 %.
- **Estado** resume en una línea lo que está pasando, por ejemplo «Arranque de Tor: 45 % (Loading relay descriptors)».
- **Mensajes de Tor** recoge todo lo que va diciendo Tor, además de los métodos de autenticación que ofrece y la confirmación «Autenticación correcta». El foco pasa a este cuadro para que pueda leerlo.

Cuando Tor llega al 100 %, el diálogo se cierra solo y aparece la ventana principal. Si no quiere esperar (por ejemplo, porque necesita configurar puentes para que Tor pueda conectarse), pulse **Continuar sin esperar**, que se activa en cuanto el programa está conectado.

**Cancelar** detiene Tor si estaba arrancando. Si cancela al abrir el programa, este se cierra.

### Contraseñas

El programa le pedirá una contraseña en dos casos:

- Si configuró el Tor que se inicia para protegerse con contraseña, antes de iniciarlo, para establecerla. No puede dejarla vacía.
- Si Tor exige una contraseña al conectarse. Si la contraseña es incorrecta, el diálogo vuelve a aparecer con el aviso «La contraseña no es correcta. Inténtelo de nuevo».

La casilla **Recordar la contraseña** hace que no se la vuelva a pedir. Tenga en cuenta que se guarda sin cifrar en la carpeta de datos del programa. Puede olvidarla más tarde desde los ajustes.

## 3. La ventana principal

### Menús

La barra de menús contiene todas las acciones del programa: **Archivo**, **Circuitos**, **Streams**, **Servicios onion**, **Configuración**, **Control**, **Ver** y **Ayuda**. Los botones de cada pestaña y los menús contextuales son atajos de las mismas acciones.

Cuando no hay conexión con Tor, los menús Circuitos, Streams, Servicios onion, Configuración y Control aparecen como no disponibles, y en el menú Archivo solo queda activa **Iniciar o conectar Tor…**.

### Pestañas

La ventana tiene cinco pestañas. Puede recorrerlas con Ctrl+Tab o ir directamente a cada una desde el menú **Ver** (Ctrl+1 a Ctrl+5):

1. Circuitos
2. Streams
3. Servicios onion
4. Configuración
5. Información y registro

Las cuatro primeras siguen el mismo esquema, de arriba abajo:

- una **lista** con una fila por elemento;
- una fila de **botones** con las acciones más habituales;
- un cuadro de **detalles** de solo lectura con toda la información del elemento seleccionado. Puede recorrerlo con las flechas y copiar su texto.

En las listas también funcionan estas teclas:

- **Supr**: cierra o elimina el elemento seleccionado.
- **Intro**: ejecuta la acción principal del elemento seleccionado.
- **Aplicaciones** (o Mayús+F10): abre el menú contextual.

### Barra de estado

La barra de estado, en la parte inferior, tiene tres zonas:

1. El resultado de la última acción, por ejemplo «Circuito 15 construido.» o un resumen del error.
2. El progreso del arranque de Tor, por ejemplo «Arranque: 100 % (Done)».
3. El tráfico del último segundo: «Descarga: …, subida: …».

## 4. Usar Tor desde otros programas

Mientras Tor Manager tenga Tor en marcha, cualquier programa puede navegar a través de Tor si se configura con este proxy:

- Tipo: **SOCKS5** (con resolución de nombres a través del proxy si el programa lo permite).
- Servidor: **127.0.0.1**
- Puerto: el **puerto SOCKS** de los ajustes (**9050** por defecto).

Las conexiones de esos programas aparecen en la pestaña Streams.

## 5. Circuitos

Un circuito es el camino cifrado que usa Tor para salir a Internet o llegar a un servicio onion. Normalmente pasa por tres relés: guardia, intermedio y salida.

### Consultar los circuitos

La lista **Circuitos abiertos** muestra el ID, el estado, el propósito, la ruta (los apodos de los relés) y la hora de creación de cada circuito. Se actualiza sola: los circuitos nuevos aparecen y los cerrados desaparecen sin que tenga que hacer nada.

Al seleccionar un circuito, el cuadro de detalles muestra:

- el estado y el propósito;
- la fecha de creación y las opciones de construcción;
- cada salto de la ruta, con apodo y huella digital;
- los streams que lo están usando.

### Crear un circuito

Use **Circuitos > Nuevo circuito…** (Ctrl+N) o el botón **Nuevo circuito…**. En el diálogo:

- **Propósito del circuito**:
  - **General**: Tor lo usa para el tráfico normal.
  - **Controlador**: queda reservado; Tor no lo usará por su cuenta, solo para los streams que usted le asocie.
- **Ruta**: déjela vacía para que Tor elija los relés, o escriba huellas digitales o apodos en orden (guardia, intermedio, salida), separados por comas o espacios.
- **Añadir un relé de la lista…**: abre la lista de relés de la red para añadir uno a la ruta sin escribirlo (vea abajo).
- **Esperar a que el circuito esté construido**: si la marca, el programa espera hasta 60 segundos y le confirma que el circuito está listo. Si no, solo lo solicita.

Resultado: la barra de estado indica «Circuito N solicitado» o «Circuito N construido», y el circuito aparece en la lista. Si Tor no puede construirlo, verá un mensaje con el motivo.

### Elegir relés de la lista

El diálogo de selección de relés carga todos los relés de la red, ordenados de mayor a menor ancho de banda. Para encontrar uno:

- escriba en **Buscar** parte del apodo, de la huella digital o de la dirección;
- en **Tipo**, limite la lista a guardias, salidas, relés rápidos o estables.

Al seleccionar un relé verá sus datos (dirección, indicadores, ancho de banda, versión de Tor…). Pulse Intro o **Aceptar** para elegirlo.

### Otras acciones sobre un circuito

Seleccione el circuito en la lista y use el menú **Circuitos**:

- **Extender circuito…**: añade uno o varios relés al final del circuito.
- **Cambiar propósito…**: cambia entre General y Controlador.
- **Cerrar circuito** (o Supr): lo cierra tras pedirle confirmación. Los streams que lo usaban se interrumpen.
- **Cerrar si no se usa**: lo cierra solo cuando deje de tener streams.
- **Actualizar lista**: vuelve a pedir la lista completa a Tor.

## 6. Streams

Un stream es cada conexión que un programa hace a través de Tor, por ejemplo la carga de una página web.

### Consultar los streams

La lista **Streams activos** muestra el ID, el estado, el destino (dirección y puerto), el circuito que usa y el propósito de cada stream. El cuadro de detalles añade el origen de la conexión y la ruta completa de su circuito.

### Cerrar un stream

Seleccione el stream y use **Streams > Cerrar stream…** (o Supr). Elija el motivo que se comunicará (por ejemplo «Otro motivo» o «Tiempo agotado») y acepte. El stream desaparece de la lista.

### Decidir qué circuito usa cada conexión

Tor asocia cada conexión nueva a un circuito automáticamente. Si prefiere decidirlo usted:

1. Active **Streams > Asociar streams manualmente**. El programa le advertirá de que, a partir de ese momento, cada conexión nueva esperará a que usted la asocie y, si no lo hace, fallará por tiempo agotado.
2. Cuando aparezca un stream en estado «Nuevo», selecciónelo y pulse Intro o **Asociar a un circuito…**.
3. En **Circuito construido**, elija el circuito.
4. Opcionalmente, en **Salto de salida** indique por qué relé del circuito debe salir la conexión (0 significa el último).

Para volver al funcionamiento normal, desactive **Asociar streams manualmente**. Si se conectó a un Tor que no inició el programa, esta opción se desactiva sola al desconectarse.

Tor solo permite asociar streams nuevos o desvinculados. Si intenta asociar uno ya establecido, verá el motivo del rechazo.

## 7. Servicios onion

Un servicio onion publica en la red Tor un servicio que funciona en su equipo (una web, un servidor de chat…) con una dirección terminada en `.onion`. Antes de crearlo, ponga en marcha el servicio local, por ejemplo un servidor web en `127.0.0.1:8080`.

### Servicios efímeros y persistentes

| | Efímero | Persistente |
|---|---|---|
| Dónde se guarda | En ninguna parte: solo existe mientras dure la conexión o Tor | Sus claves se guardan en un directorio |
| Dirección | Nueva cada vez, salvo que reutilice su clave privada | Siempre la misma |
| Tras reiniciar Tor | Desaparece | Sigue existiendo si guardó la configuración |

### Crear un servicio efímero

Use **Servicios onion > Añadir servicio efímero…**. El diálogo contiene:

- **Correspondencia de puertos**: qué puerto verán los visitantes (puerto virtual) y a qué servicio de su equipo llega (destino). Por defecto propone `80 → 127.0.0.1:8080`.
  - **Añadir puerto…**, **Modificar…** (o Intro) y **Quitar** permiten gestionar las correspondencias.
  - En cada una, el destino puede ser un puerto, «dirección:puerto» o vacío (el mismo puerto en 127.0.0.1).
- **Clave del servicio**:
  - **Generar una clave nueva ED25519-V3** (recomendado).
  - **Generar una clave nueva del tipo que elija Tor**.
  - **Usar una clave privada existente**: pegue en el cuadro siguiente la clave que guardó al crear el servicio (por ejemplo «ED25519-V3:…») para recuperar la misma dirección.
- **No devolver la clave privada**: Tor no le entrega la clave, así que el servicio no podrá volver a crearse con la misma dirección.
- **Separado**: el servicio sigue activo aunque cierre Tor Manager, mientras Tor siga en marcha. Solo tiene sentido si se conectó a un Tor que no inició el programa, porque al cerrar el programa se detiene el Tor que él inició.
- **Esperar a que se publique el descriptor**: el programa espera hasta 2 minutos a que el servicio sea localizable en la red y le informa del resultado.
- **Máximo de streams simultáneos**: 0 significa sin límite.
- **Clave pública de cliente autorizado**: si la indica, solo el cliente con la clave privada correspondiente podrá acceder al servicio.

Al aceptar, verá el diálogo **Servicio onion creado**, con un cuadro de solo lectura que contiene:

- la dirección `.onion`;
- la correspondencia de puertos;
- si está separado y el resultado de la publicación, si lo pidió;
- la **clave privada**, salvo que eligiera no recibirla.

Con los botones puede **Copiar la dirección**, **Copiar todo** o **Guardar en un fichero…**.

Guarde la clave privada en un lugar seguro: es lo único que permite recuperar la misma dirección, y cualquiera que la tenga podría suplantar su servicio. El programa no la vuelve a mostrar.

### Crear un servicio persistente

Use **Servicios onion > Añadir servicio persistente…**. Además de la correspondencia de puertos (aquí el destino debe ser un puerto o una dirección IPv4 con puerto, como `127.0.0.1:8080`), indique:

- **Directorio del servicio**: dónde se guardarán sus claves. Se propone uno nuevo dentro de la carpeta de datos del programa (`onion-services\servicio-1`, `servicio-2`…). Si no existe, se crea.
- **Guardar la configuración en el torrc…** (marcada por defecto): hace que el servicio siga existiendo cuando Tor se reinicie. Si la desmarca, el servicio desaparecerá al detener Tor, aunque sus claves permanezcan en el directorio.

El diálogo de resultado muestra la dirección `.onion`, el directorio de claves y si la configuración se guardó.

Si crea otro servicio persistente con el mismo directorio, las nuevas correspondencias de puertos se añaden al servicio existente, con la misma dirección.

### Consultar, copiar y eliminar servicios

La pestaña **Servicios onion** lista todos los servicios que conoce Tor:

- La columna Tipo indica si es **Efímero**, **Efímero separado** o **Persistente**.
- De los servicios efímeros creados por otros programas o en sesiones anteriores, Tor no informa de sus puertos.

Para actuar sobre un servicio, selecciónelo:

- **Copiar dirección** (Ctrl+Mayús+C, o Intro en la lista) copia la dirección `.onion` al portapapeles.
- **Eliminar servicio** (o Supr):
  - Un servicio **efímero** se elimina tras confirmarlo.
  - En uno **persistente** puede elegir **Eliminar y guardar** (desaparece también del torrc), **Eliminar solo ahora** (volverá al reiniciar Tor) o **Cancelar**.

Las claves de los servicios persistentes nunca se borran: siguen en su directorio por si quiere recuperar el servicio más adelante.

## 8. Configuración de Tor

La pestaña **Configuración** permite ver y cambiar cualquier parámetro de Tor mientras funciona, sin reiniciarlo.

### Consultar parámetros

La lista muestra cada parámetro con su valor actual, si está **Modificado** respecto al predeterminado y su tipo. Para encontrar un parámetro:

- escriba parte del nombre en **Filtrar por nombre** (la lista se actualiza al dejar de escribir);
- marque **Mostrar solo los parámetros modificados** para ver solo los que ha cambiado.

El cuadro de detalles muestra todos los valores actuales (uno por línea si hay varios), los valores predeterminados y la descripción, si Tor la ofrece.

### Cambiar un parámetro

Seleccione el parámetro y pulse Intro, **Establecer valor…** o **Configuración > Establecer parámetro…** (Ctrl+E). En el diálogo:

- **Parámetro**: puede cambiarlo o escribir cualquier otro nombre.
- **Información del parámetro**: su tipo y sus valores actual y predeterminado.
- **Valores nuevos, uno por línea**: escriba el valor. Para parámetros que admiten varios valores (como `Bridge`), escriba uno por línea. Si lo deja vacío, el parámetro queda sin valor.

El cambio se aplica al instante: el registro lo anota y la lista se actualiza. Si Tor no acepta el valor, verá su respuesta en un mensaje de error.

Los cambios se pierden al reiniciar Tor, salvo que los guarde en disco.

### Restablecer, guardar y cargar

Estas acciones están en el menú **Configuración**:

- **Restablecer parámetro al predeterminado** (o Supr en la lista): devuelve el parámetro seleccionado a su valor por defecto.
- **Guardar configuración en disco** (Ctrl+S): escribe la configuración actual en el torrc para que se mantenga en el próximo arranque.
  - La primera vez, Tor conserva una copia del torrc anterior con el nombre `torrc.orig.1`.
- **Restablecer valores de fábrica…**: devuelve a su valor predeterminado todos los parámetros modificados y guarda el resultado en el torrc.
  - Se conservan los que mantienen la conexión: puertos, directorio de datos, autenticación, registro y bases de datos geográficas.
  - Los servicios onion persistentes se quitan de la configuración, aunque sus claves no se borran.
  - Al terminar, un resumen indica qué parámetros se restablecieron y si alguno falló.
- **Cargar configuración (LOADCONF)…**: abre un editor con la configuración actual, que puede modificar o sustituir con **Abrir un fichero torrc…**. Al pulsar **Cargar en Tor**, Tor sustituye toda su configuración por ese texto; lo que no aparezca vuelve a su valor predeterminado.
  - Si está conectado a un Tor que no inició el programa, no elimine su `ControlPort` o perderá la conexión.
- **Ver configuración actual…**: muestra en un cuadro de solo lectura todas las opciones distintas de las predeterminadas, con botones para copiarlas o guardarlas en un fichero.

### Ejemplo: usar puentes

Si Tor no consigue conectarse porque su red lo bloquea, puede configurar puentes. Obtenga líneas de puente en bridges.torproject.org y, con Tor en marcha (use **Continuar sin esperar** si el arranque no avanza):

1. Si los puentes usan un transporte como obfs4, establezca `ClientTransportPlugin` con el programa de transporte. Por ejemplo, `obfs4 exec` seguido de la ruta de `lyrebird.exe`, que se encuentra en `resources\tor\pluggable_transports` si su Tor Expert Bundle lo incluye.
2. Establezca `Bridge` con una línea de puente por línea.
3. Establezca `UseBridges` con el valor `1`.
4. Use **Guardar configuración en disco** para conservarlos en los próximos arranques.

En la zona de estado del arranque verá cómo Tor se conecta a través de los puentes.

## 9. Menú Control

- **Nueva identidad** (Ctrl+I): las conexiones nuevas usarán circuitos nuevos, así que los sitios web verán otra dirección.
  - Tor solo lo permite cada pocos segundos; si lo pide antes, un mensaje le indica cuántos segundos faltan.
  - También está en el menú del icono de la bandeja.
- **Recargar configuración (RELOAD)**: Tor vuelve a leer su torrc.
- **Vaciar la caché DNS**: Tor olvida las direcciones que había resuelto.
- **Pasar a modo latente (DORMANT)**: Tor deja de construir circuitos y reduce su actividad al mínimo.
- **Pasar a modo activo (ACTIVE)**: Tor sale del modo latente.
- **Registrar un heartbeat**: Tor escribe en el registro un resumen de su actividad.
- **Descartar los nodos guardia…**: Tor olvida sus relés de entrada y elige otros. Hacerlo sin motivo reduce su anonimato, por eso le pide confirmación.
- **Consultar información (GETINFO)…** (Ctrl+G): permite consultar a Tor cualquier dato.
  1. En **Clave que se consultará** elija una clave de la lista o escríbala. Las que terminan en «*» necesitan un dato en lugar del asterisco.
  2. Lea su **Descripción**.
  3. Pulse **Consultar** (o Intro). La respuesta aparece en **Resultado**, que puede copiar.
- **Consultar un relé…** (Ctrl+R):
  1. Escriba la huella digital o el apodo de un relé, o pulse **Elegir de la lista…**.
  2. Pulse **Buscar**. Verá su dirección, indicadores, ancho de banda, versión, política de salida y los datos completos que Tor tiene de él.
- **Actualizar información general**: actualiza el cuadro de información de la pestaña Información y registro.

## 10. Información y registro

La última pestaña contiene dos cuadros de solo lectura.

### Información general de Tor

El cuadro **Información general de Tor** se actualiza al conectar y cuando pulsa **Actualizar información**. Muestra:

- la versión de Tor y si lo inició este programa;
- el identificador del proceso y el tiempo en funcionamiento;
- el estado del arranque, si hay circuitos establecidos, el estado de la red y si está en modo latente;
- si se puede pedir una nueva identidad;
- la dirección IP externa y la huella digital (solo si su Tor funciona como relé);
- las direcciones donde escucha;
- el tráfico total leído y escrito, y el ancho de banda disponible;
- la contabilidad de tráfico y si la base de datos geográfica está disponible;
- los métodos de autenticación que ofrece Tor;
- la ubicación del torrc y del directorio de datos.

### Registro de eventos

El cuadro **Registro de eventos** recoge, con la hora, los mensajes de Tor y del propio programa. Por ejemplo:

```
10:15:02 [Tor, Aviso] Bootstrapped 100% (done): Done
10:15:40 [Programa, Aviso] Circuito 15 construido.
```

Controles del registro:

- **Nivel de detalle de los mensajes de Tor**: elija entre **Solo errores**, **Advertencias**, **Avisos (recomendado)**, **Información detallada** o **Depuración (muy detallado)**. El cambio se aplica al instante y se recuerda.
- **Seguir los mensajes nuevos**: si está marcada, el cuadro avanza con cada mensaje. Desmárquela si quiere leer mensajes anteriores sin que el cursor salte al final.
- **Limpiar registro**: vacía el cuadro.
- **Guardar registro…**: guarda todo su contenido en un fichero de texto.

El registro conserva los últimos 5000 mensajes; los más antiguos se descartan.

## 11. La bandeja del sistema

Mientras Tor Manager está abierto, su icono aparece en la bandeja del sistema: morado cuando hay conexión con Tor y gris cuando no. Al situarse sobre él, se muestra el estado, por ejemplo «Tor Manager: conectado, arranque al 100 %».

- **Minimizar la ventana** la oculta en la bandeja (se puede desactivar en los ajustes). También puede ocultarla con **Archivo > Ocultar en la bandeja del sistema** (Ctrl+H).
- **Hacer clic en el icono** vuelve a mostrar la ventana, con el foco donde lo dejó. Con el teclado, pulse Windows+B para ir a la bandeja, llegue al icono con las flechas, pulse Intro para abrir su menú y elija **Mostrar Tor Manager**.
- **Su menú contextual** ofrece **Mostrar** u **Ocultar Tor Manager**, **Nueva identidad** y **Salir**.

Con la ventana oculta, el programa le avisa mediante notificaciones de Windows de estos hechos:

- sigue en ejecución en la bandeja (solo la primera vez que se oculta);
- Tor ha terminado de arrancar;
- se ha perdido la conexión con Tor;
- se ha solicitado una nueva identidad.

## 12. Ajustes del programa

Abra **Archivo > Ajustes…** o el botón **Ajustes avanzados…** del diálogo de arranque. Los cambios de puertos, directorio de datos, autenticación y opciones de arranque se aplican la próxima vez que se inicie Tor.

- **Puerto SOCKS**: el que usarán los demás programas para conectarse a Tor (9050 por defecto).
- **Puerto de control**: el que usa Tor Manager para controlar el Tor que inicia (9051 por defecto). Cámbielo si ya tiene otro Tor usando ese puerto.
- **Directorio de datos**: dónde guarda Tor su estado. Si lo cambia, Tor empezará de cero en el nuevo directorio.
- **Autenticación del Tor iniciado**: cómo se protege el Tor que inicia el programa.
  - **Cookie** (recomendado).
  - **Contraseña**: se le pedirá al iniciar Tor.
  - **Sin autenticación**: cualquier programa del equipo podría controlar Tor, por eso se muestra un aviso de seguridad.
- **Opciones adicionales de arranque**: opciones de Tor que se aplicarán cada vez que el programa lo inicie, una por línea con el formato «Opción valor». Por ejemplo, `ExitNodes {es}` y `StrictNodes 1`, en dos líneas.
- **Minimizar a la bandeja del sistema al minimizar la ventana** (activada por defecto).
- **Al cerrar la ventana, ocultarla en la bandeja en lugar de salir**: si la activa, el botón de cerrar solo oculta la ventana. Para salir, use **Archivo > Salir** o el menú de la bandeja.
- **Iniciar Tor automáticamente al abrir el programa**: el diálogo de arranque empieza solo con las opciones que usó la última vez.
- **Olvidar la contraseña guardada**: borra la contraseña recordada al aceptar los ajustes.
- **Restablecer el torrc de fábrica…**: sustituye el torrc del programa por el original. Se pierde todo lo que guardó con «Guardar configuración en disco», incluidos los servicios onion persistentes (no sus claves). Funciona aunque Tor no esté en marcha, lo que es útil si una configuración guardada impide que Tor arranque. Reinicie Tor para aplicarlo.
- **Valores predeterminados**: devuelve los campos del diálogo a sus valores originales.

## 13. Detener, reiniciar y salir

En el menú **Archivo**:

- **Detener Tor o desconectar**: tras confirmarlo, detiene el Tor que inició el programa o, si se conectó a uno existente, solo cierra la conexión y deja ese Tor en marcha. La ventana sigue abierta, sin conexión.
- **Reiniciar Tor**: detiene Tor (o cierra la conexión) y vuelve a mostrar el diálogo de arranque. Si el programa había iniciado Tor, se cierran todos los circuitos y desaparecen los servicios onion efímeros; si se había conectado a un Tor existente, solo desaparecen los servicios efímeros que no estaban separados.
- **Iniciar o conectar Tor…**: disponible cuando no hay conexión; muestra el diálogo de arranque.
- **Salir** (Ctrl+Q): cierra el programa y detiene el Tor que haya iniciado. Si se conectó a un Tor existente, ese Tor sigue funcionando.

Si Tor se detiene de forma inesperada, el programa lo anota en el registro y le pregunta si quiere iniciarlo o conectarse de nuevo.

## 14. Dónde guarda el programa sus datos

Todo se guarda en la carpeta **TorManagerConfig**, junto al programa:

| Elemento | Qué contiene |
|---|---|
| `settings.json` | Sus ajustes y, si lo pidió, la contraseña recordada. |
| `torrc` | La configuración de Tor que guarda con «Guardar configuración en disco». |
| `tor-data` | Los datos de Tor. |
| `onion-services` | Los directorios de los servicios onion persistentes, con sus claves privadas. |
| `tor-manager.log` | Un registro técnico del programa, útil si necesita informar de un problema. |

Esta carpeta contiene información delicada (claves de sus servicios onion y, quizá, una contraseña). Haga copias de seguridad de `onion-services` si quiere conservar sus direcciones `.onion`, y no la comparta con nadie.

## 15. Atajos de teclado

| Atajo | Acción |
|---|---|
| Ctrl+1 … Ctrl+5 | Ir a las pestañas Circuitos, Streams, Servicios onion, Configuración o Información y registro |
| Ctrl+Tab / Ctrl+Mayús+Tab | Pestaña siguiente / anterior |
| F5 | Actualizar la pestaña actual |
| Ctrl+N | Nuevo circuito |
| Ctrl+I | Nueva identidad |
| Ctrl+Mayús+C | Copiar la dirección del servicio onion seleccionado |
| Ctrl+E | Establecer un parámetro de configuración |
| Ctrl+S | Guardar la configuración en disco |
| Ctrl+G | Consultar información (GETINFO) |
| Ctrl+R | Consultar un relé |
| Ctrl+H | Ocultar en la bandeja del sistema |
| Ctrl+Q | Salir |
| Supr (en una lista) | Cerrar el circuito o stream, eliminar el servicio o restablecer el parámetro |
| Intro (en una lista) | Streams: asociar a un circuito. Servicios: copiar la dirección. Configuración: establecer el valor |
| Aplicaciones o Mayús+F10 (en una lista) | Menú contextual |
| Alt+letra subrayada | Ir al control o botón correspondiente dentro de un diálogo o pestaña |

## 16. Solución de problemas

**«No se encontró el Tor incorporado»**
Coloque el Tor Expert Bundle en la carpeta `resources` como se indica en el [apartado 1](#1-antes-de-empezar), o elija **Iniciar un ejecutable de Tor personalizado**.

**Tor no arranca y los mensajes hablan de «Could not bind» o «Address already in use»**
Otro programa, a menudo otro Tor, ya usa el puerto SOCKS o el de control. Cambie los puertos en los ajustes o cierre el otro Tor. También puede conectarse a ese Tor con la tercera opción del diálogo de arranque.

**El arranque se queda parado en un porcentaje**
Su red puede estar bloqueando Tor. Revise los **Mensajes de Tor**, pulse **Continuar sin esperar** y configure puentes (vea el [apartado 8](#ejemplo-usar-puentes)).

**Tor dejó de arrancar después de guardar una configuración**
Abra **Ajustes avanzados…** en el diálogo de arranque, pulse **Restablecer el torrc de fábrica…** y vuelva a iniciar Tor.

**«Tor ha rechazado la contraseña»**
Compruebe la contraseña. Si la tenía recordada y ya no es válida, use **Olvidar la contraseña guardada** en los ajustes.

**«No se pudo autenticar con el fichero de cookie de Tor»**
El mensaje indica la ruta del fichero de cookie. El programa necesita poder leerlo; con un Tor instalado como servicio de otro usuario, puede que no tenga permiso. Use en su lugar la autenticación por contraseña.

**Un servicio persistente aparece sin dirección**
Tor tarda un momento en generar las claves. Pulse **Actualizar** en la pestaña Servicios onion. Si se conectó a un Tor de otro equipo, el programa no puede leer la dirección.

**«Tor solo permite pedir una identidad nueva cada pocos segundos»**
Espere los segundos que indica el mensaje y vuelva a intentarlo.

**Algo falla y no sabe por qué**
Consulte la pestaña **Información y registro** (suba el nivel de detalle si hace falta) y el fichero `tor-manager.log` de la carpeta de datos. Los mensajes de error incluyen siempre, cuando existe, la respuesta original de Tor.
