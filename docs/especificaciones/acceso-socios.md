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

## Estado inicial

- Campo de búsqueda vacío y con foco.
- Panel de resultado visible pero sin datos: sin nombre, plan, vencimiento ni foto;
  mensaje de ingreso previo y rótulo de estado ocultos.

## Barra superior

- Alto ~75 px, fondo `#2D4864`.
- Logo corporativo a la izquierda (`temps/logo.png`; si no existe o falla, texto
  "ALTOS ROCA" como fallback).
- Texto centrado "ACCESO SOCIOS", color `#D7D7D7`, Segoe UI Light ~40–48 px
  (fallback Helvetica).

## Campo de búsqueda

- Dimensiones visuales 690 x 60 px, fondo `#E7E8EB`, fuente grande.
- Solo acepta **dígitos**: validador Tk (`validatecommand` con `%P`, `vcmd =
  window.register(...)`, `isdigit()`). Rechaza letras y entradas mixtas como
  `123.5` o `12-34`.
- ENTER sobre el campo dispara la máquina de estados.

## Área de resultado

- Panel de 690 x 280 px, fondo `#E7E8EB`.
- Nombre en negrita, color oscuro: `APELLIDOS, NOMBRES` (mayúsculas).
- Línea `Plan: <Nomenclatura>`.
- Línea `Vencimiento: dd-mm-yyyy`.
- Mensaje de ingreso previo, color `#456FE5`: "Ya registró ingreso al día de hoy
  hh:mm:ss" (solo si ya hubo acceso hoy; oculto inicialmente).
- Rótulo de estado, negrita ~24–28 px (implementado con 26):
  - `SOCIO HABILITADO` en `#008000`.
  - `SOCIO INHABILITADO` en `#FF0000`.
  - Oculto hasta la primera búsqueda.
- Fotografía a la derecha, 140 x 130 px. No hay fotos reales cargadas: se muestra
  una silueta/placeholder gris con el texto "SIN FOTO". No se decodifican los blobs
  de `tbImagen`.

## Botón VER SOCIO

Centrado en la parte inferior. Fondo `#314863`, texto blanco. Abre la ventana
Consultar Socios posicionada en el socio mostrado actualmente (stub 900 x 600 que
indica el socio actual).

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
| Fondo barra superior        | `#2D4864` |
| Texto "ACCESO SOCIOS"       | `#D7D7D7` |
| Campo de búsqueda / panel   | `#E7E8EB` |
| Mensaje ingreso previo      | `#456FE5` |
| SOCIO HABILITADO            | `#008000` |
| SOCIO INHABILITADO          | `#FF0000` |
| Botón VER SOCIO             | `#314863` |
