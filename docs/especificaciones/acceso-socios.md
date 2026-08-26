# Especificación de ventana: Acceso Socios (módulo persistente de recepción)

## Importancia y objetivo

Ventana central de la operación diaria del gimnasio. Flujo de trabajo en recepción:
ingresar DNI (escaneado o tecleado) → validar estado de cuota → registrar/mostrar el
resultado → esperar el próximo socio. El flujo es **100% teclado**: el lector USB de
códigos actúa como teclado y envía un ENTER al final, por lo que toda la interacción
se resuelve con el campo de búsqueda y la tecla ENTER.

## Apertura automática

Tras el login → dashboard → la ventana **Acceso Socios se abre automáticamente**
(`principal` invoca `acceso_socios.open_window`). Es la ventana de trabajo por
defecto de la recepción.

## Restricción crítica

La ventana **no se cierra realmente**. El botón [X] de la barra de título se
intercepta (`WM_DELETE_WINDOW`) y hace `withdraw()` (ocultar/minimizar), nunca
`destroy()`. Volver a abrirla desde el sidebar o la apertura automática hace
`deiconify()` + `lift()` + foco en el input.

## Dimensiones generales

- **Tamaño fijo**: 800 x 600 px, **no redimensionable** (`resizable(False, False)`).
- **Fondo general**: `#08142C` (azul muy oscuro).
- **Gradiente vertical sutil**: ~30 bandas horizontales delgadas interpolando
  `#08142C` → `#0C1D3A` de arriba a abajo. **NO** un fondo plano uniforme.
- **NO** usar fondo gris.

## Encabezado (barra superior)

- **Alto**: ~75 px.
- **Color de fondo**: `#304A66`.
- Logo corporativo **alineado a la izquierda**, dentro del header, centrado
  verticalmente (`temps/logo.png`; si no existe o falla, se omite — **NO** se usa
  texto "ALTOS ROCA" como fallback).
- **Título "ACCESO SOCIOS"** centrado horizontalmente en el header.
- **Color del título**: `#D9D9D9`.
- **Fuente del título**: Segoe UI Light, ~44 px, peso light.
- **Fallback de fuente**: Helvetica (Linux).

## Campo de búsqueda

- **Fondo del campo**: BLANCO (`#FFFFFF`), **NO** `#E7E8EB`.
- **Dimensiones visuales**: 690 x 60 px.
- **Centrado horizontalmente**.
- **Posición**: 16 px de gap debajo del encabezado (y = 91).
- **Separación visible**: entre encabezado → campo → panel de resultado, **NO** deben
  tocarse entre sí.
- **Validador de solo dígitos**: lógica existente, conservar (`validatecommand` con
  `%P`, `vcmd = window.register(...)`, `isdigit()`). Rechaza letras y entradas mixtas.
- **Fuente grande**: ~22–26 px.

## Panel de resultado

- **Fondo**: gris claro `#E7E8EB`.
- **Dimensiones**: 690 x 280 px.
- **Centrado horizontalmente**.
- **Posición**: y = 167 (91 input + 60 alto input + 16 gap).
- **Separación visible** del campo de entrada (no deben tocarse).

### Nombre del socio

- **Posición**: esquina superior-izquierda del panel, `place(x=15, y=15)`.
- **Formato**: `APELLIDOS, NOMBRES` (mayúsculas).
- **Color**: negro.
- **Fuente**: Helvetica 18, **no bold** (peso normal).

### Plan

- Debajo del nombre, `place(x=15, y=55)`.
- Formato: `Plan: <Nomenclatura>`.
- Fuente: Helvetica 13.

### Vencimiento

- Debajo del plan, `place(x=15, y=80)`.
- Formato: `Vencimiento: dd-mm-yyyy`.
- Fuente: Helvetica 13.

### Mensaje de ingreso previo

- Debajo del vencimiento, `place(x=15, y=110)`.
- Formato: `"Ya registra ingreso al dia de hoy, horas: hh:mm:ss"`.
- Color: `#4169E1` (azul royal).
- Fuente: Helvetica 12.
- **Oculto inicialmente**.

### Estado

- Debajo del mensaje de ingreso, `place(x=15, y=170)`.
- `SOCIO HABILITADO` en `#008000` (verde).
- `SOCIO INHABILITADO` en `#FF0000` (rojo).
- Fuente: Helvetica 24 bold.
- **Oculto inicialmente**.

### Foto

- **Posición**: sector superior-derecha del panel, `place(x=535, y=15)`.
- **Tamaño**: 140 x 130 px.
- **Fondo**: NEGRO (`#000000`).
- **Silueta**: color BLANCO (`#FFFFFF`), NO gris. Se dibuja con un Canvas
  conteniendo óvalos blancos (cabeza + hombros) sobre fondo negro.
- **Borde delgado**: `highlightthickness=1`, `highlightbackground="#888888"`.

## Botón VER SOCIO

- **Tamaño**: ~130 x 36 px.
- **Posición**: centrado horizontalmente, y = 482 (167 panel + 280 panel + 35 gap).
- **Color de fondo**: `#314863`.
- **Borde gris visible**: `borderwidth=1`, `relief=solid`.
- **Texto**: blanco.
- **Separación mínima**: 35 px entre el panel de resultado y el botón.

## Máquina de estados

```
+--------------+  ENTER (DNI válido)   +---------------+
| Esperando    | --------------------> | Buscar Socio  |
| DNI          |                       +-------+-------+
+--------------^                               |
|                     ^                        v
|                     |               +------------------+
| ENTER       +-------+-----------+   | Mostrar Resultado|
|             | Limpiar Datos     |   +--------+---------+
+-------------+ (volver a inicio)  <------------+
```

1. **Esperando DNI** → ENTER con texto no vacío y solo dígitos → **Buscar Socio**.
2. **Buscar Socio** → consulta DB → **Mostrar Resultado** (panel poblado, estado
   `showing`, input limpio y con foco).
3. **Mostrar Resultado** → ENTER → **Limpiar Datos**: borra labels, oculta estado,
   mensaje y foto, vuelve a **Esperando DNI** con foco en el input.

## Reglas de consulta

Tablas implicadas (todas TEXT):

| Tabla           | Columnas relevantes                                        |
| --------------- | ---------------------------------------------------------- |
| `tbSocios`      | idSocio, Apellidos, Nombres, Documento, Estado, id_Plan    |
| `tbPlan`        | idPlan, Nomenclatura, Descripcion                          |
| `tbPagos`       | idSocio, FechaVencimineto (`YYYY-MM-DD HH:MM:SS.000`), Saldo, Eliminado |
| `tbSociosAcceso`| idSocio, FechaAcceso (`YYYY-MM-DD HH:MM:SS.000`), Estado   |

Criterios:

- Búsqueda: `tbSocios.Documento = <dni>`; si no hay coincidencia, fallback a
  `tbSocios.idSocio = <dni>`. La primera fila de `tbSocios` es un placeholder
  basura (`Apellidos = '-------'`): se ignoran filas cuyo Documento no contenga
  dígitos.
- **Habilitado**: máximo `tbPagos.FechaVencimineto` (ignorando NULL) del socio
  `>=` fecha de hoy.
- **Ingreso previo**: existe alguna fila en `tbSociosAcceso` de ese socio cuya
  `FechaAcceso` comience con la fecha de hoy (formato `YYYY-MM-DD`); se muestra la
  parte horaria `hh:mm:ss`.

## Paleta de colores

| Elemento                    | Color     |
| --------------------------- | --------- |
| Fondo general               | `#08142C` |
| Fondo gradiente inferior    | `#0C1D3A` |
| Encabezado                  | `#304A66` |
| Texto "ACCESO SOCIOS"       | `#D9D9D9` |
| Input fondo                 | `#FFFFFF` |
| Panel resultado             | `#E7E8EB` |
| Mensaje ingreso previo      | `#4169E1` |
| SOCIO HABILITADO            | `#008000` |
| SOCIO INHABILITADO          | `#FF0000` |
| Botón VER SOCIO             | `#314863` |
| Foto fondo                  | `#000000` |
| Foto silueta                | `#FFFFFF` |
