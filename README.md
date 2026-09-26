# Tor Manager

Nota: este software se ha elaborado mediante inteligencia artificial. El código fuente no se ha revisado manualmente. La interfaz, los comportamientos y la documentación se han revisado parcialmente. Esta nota se actualizará a medida que la revisión manual se complete.

Tor Manager es un programa de escritorio para Windows que inicia y controla Tor desde una interfaz gráfica pensada para usarse con lectores de pantalla como NVDA o JAWS. Está escrito en Python, usa [Stem](https://stem.torproject.org/) para comunicarse con Tor y [wxPython](https://wxpython.org/) para la interfaz.

Consulte la [guía de usuario](docs/guia-de-usuario.md) para aprender a usar el programa paso a paso.

## Características

### Inicio de Tor y autenticación

- Inicia el Tor incorporado en la carpeta del programa o cualquier otro `tor.exe` que elija el usuario.
- También puede conectarse a un Tor que ya esté en ejecución, como el de Tor Browser.
- Métodos de autenticación: automático, sin autenticación, contraseña, cookie y SafeCookie. El Tor que inicia el programa puede protegerse con cookie o con contraseña, y la contraseña puede recordarse si se desea.
- Muestra el progreso del arranque y los mensajes de Tor mientras se inicia, y permite cancelarlo en cualquier momento.

### Circuitos y streams

- Lista de circuitos actualizada en tiempo real, con su estado, propósito y ruta completa.
- Crear circuitos con una ruta automática o elegida por el usuario, a partir de la lista de relés de la red. También permite extender circuitos, cambiar su propósito y cerrarlos.
- Lista de streams en tiempo real. Los streams se pueden cerrar indicando el motivo o asociar manualmente a un circuito concreto.

### Servicios onion

- **Efímeros**: se crean sin escribir nada en el disco. Se pueden generar con una clave nueva o reutilizar una existente, mantener activos aunque se cierre el programa, esperar a que se publique su descriptor, limitar los streams simultáneos y autorizar a un cliente.
- **Persistentes**: conservan su dirección porque guardan las claves en un directorio. Se pueden guardar en la configuración de Tor para que sobrevivan a un reinicio.
- Lista de todos los servicios con su dirección `.onion` y sus puertos. Permite copiar la dirección y eliminar servicios.

### Configuración de Tor

- Lista de todos los parámetros de Tor con su valor actual y su valor predeterminado. Se puede filtrar por nombre o mostrar solo los modificados.
- Los parámetros se pueden cambiar en tiempo de ejecución o devolver a su valor predeterminado.
- Permite guardar la configuración en disco y restablecer los valores de fábrica.
- También se puede cargar un torrc completo en el Tor en ejecución.

### Otros controles

- Nueva identidad, recargar la configuración, vaciar la caché DNS, modo latente y activo, y descartar los nodos guardia.
- Información general de Tor (versión, tiempo en marcha, tráfico, escuchas…), consultas GETINFO libres y consulta de relés de la red.
- Registro de eventos de Tor con nivel de detalle ajustable, que se puede guardar en un fichero.

### Interfaz

- Solo controles nativos de Windows, con etiquetas accesibles y teclas de acceso rápido.
- Todas las acciones están disponibles en la barra de menús, y la información de Tor se muestra en cuadros de texto de solo lectura.
- Se minimiza a un icono en la bandeja del sistema.
- Al cerrar el programa se detiene el Tor que haya iniciado.

## Requisitos

- Windows 10 u 11 de 64 bits.
- Para ejecutar desde el código fuente: Python 3 con wxPython y Stem (probado con Python 3.13, wxPython 4.3.1 y Stem 1.8.2).
- Un ejecutable de Tor (probado con Tor 0.4.9).

## Incorporar Tor al programa

El repositorio no incluye el binario de Tor. Para que el programa lo encuentre como «Tor incorporado»:

1. Descargue el **Tor Expert Bundle** para Windows (x86_64) desde la [página de descargas de Tor](https://www.torproject.org/download/tor/) y compruebe su firma.
2. Extraiga su contenido en la carpeta `resources`, de modo que queden estas rutas:

   ```
   resources\tor\tor.exe        (y las DLL que lo acompañan)
   resources\data\geoip
   resources\data\geoip6
   ```

También puede usar cualquier otro `tor.exe` con la opción «Iniciar un ejecutable de Tor personalizado».

## Ejecutar desde el código fuente

```powershell
git clone <url-del-repositorio>
cd tor-manager
python -m pip install -r requirements.txt
python -m tor_manager
```

`python main.py` también funciona.

## Compilar con PyInstaller

PyInstaller genera una carpeta con `TorManager.exe` que no necesita tener Python instalado.

1. Instale PyInstaller en el mismo entorno que las dependencias:

   ```powershell
   python -m pip install -r requirements.txt pyinstaller
   ```

2. Desde la raíz del repositorio, compile en modo carpeta (`--onedir`, el predeterminado) y sin ventana de consola:

   ```powershell
   pyinstaller --noconfirm --windowed --name TorManager --optimize 2 --onefile main.py
   ```

   No hace falta indicar importaciones ocultas: PyInstaller detecta por sí mismo todos los módulos de Stem y wxPython que usa el programa.

3. Copie la carpeta `resources` (con Tor ya incorporado) junto al ejecutable:

   ```powershell
   Copy-Item -Recurse resources dist\TorManager\
   ```

   El programa busca `resources` en la misma carpeta que `TorManager.exe`, no dentro de `_internal`, así que no use `--add-data` para esta carpeta.

El resultado queda en `dist\TorManager`:

```
dist\TorManager\
    TorManager.exe
    _internal\             bibliotecas de Python, wxPython y Stem
    resources\
        tor\tor.exe
        data\geoip, geoip6
```

Esa carpeta se puede comprimir y distribuir tal cual. Los ficheros `build\` y `TorManager.spec` que genera PyInstaller son temporales.

## Dónde se guardan los datos

El programa guarda su configuración en la carpeta `TorManagerConfig`, junto a `TorManager.exe` (o en la raíz del repositorio si se ejecuta desde el código fuente). Por eso el programa necesita permiso de escritura en su propia carpeta. Contenido:

| Elemento | Contenido |
|---|---|
| `settings.json` | Ajustes del programa. Incluye la contraseña de control si se marcó «Recordar la contraseña». |
| `torrc` | Configuración de Tor que se guarda con «Guardar configuración en disco». |
| `tor-data\` | Directorio de datos de Tor (estado, caché de directorio, cookie de autenticación). |
| `onion-services\` | Directorio predeterminado de los servicios onion persistentes y sus claves privadas. |
| `tor-manager.log` | Registro técnico del programa, útil para diagnosticar problemas. |

Esta carpeta contiene información sensible, como claves de servicios onion y, a veces, una contraseña. No la comparta ni la suba al repositorio.

## Documentación

- [Guía de usuario](docs/guia-de-usuario.md): cómo usar el programa.
- [CLAUDE.md](CLAUDE.md): notas técnicas sobre la organización del código para quien vaya a modificarlo.
