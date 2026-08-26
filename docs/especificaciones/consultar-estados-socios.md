# Especificación de ventana: Consultar Estados de Socios

## Descripción general

Panel operativo administrativo para control de vencimientos, saldos y planes de los socios del gimnasio. Estilo WinForms 2010–2018, NO modernizar. Fondo gris claro, bordes clásicos de Windows, controles densos sin padding excesivo.

## Barra de título

- **Título**: "Consultar Estados de Socios"
- Ventana redimensionable (resizable horizontal y vertical).

## Área de búsqueda superior

- TextBox 920x30 px, fondo blanco, borde gris Windows clásico.
- Centrado horizontalmente, y=10.
- Reservada para búsqueda futura. Puede quedar vacía o con placeholder.

## Panel de filtros

- LabelFrame con borde fino gris, título "Filtros" arriba-izquierda.
- Dimensiones: 920x90 px.
- Fondo: #E8E8E8.
- Posición: y=45.

### Primera fila de filtros (y=20 dentro del panel)

Radio buttons horizontales con variable `filter_var` (StringVar, default `"ACTIVOS"`):

| Radio               | Color foreground | Estilo                | Nota                                              |
| ------------------- | ---------------- | --------------------- | ------------------------------------------------- |
| ACTIVOS             | #008000 (verde)  | Negrita               | Seleccionado por defecto                          |
| INACTIVOS           | #FF0000 (rojo)   | Normal                | Label "(Últimos 90 días)" debajo, darkred, 8px    |
| ACTIVOS C/SALDO     | #FF6600 (naranja)| Normal                | —                                                 |
| POR DÍA             | — (default)      | Radio + Entry 200x25  | Fecha "lunes, 11 de agosto de 2026" (español), readonly |

### Segunda fila de filtros (y=55 dentro del panel)

| Radio                   | Color foreground | Widget adicional                          |
| ----------------------- | ---------------- | ----------------------------------------- |
| ACTIVOS POR PLAN        | #008000 (verde)  | ttk.Combobox 160px, valores de tbPlan    |
| INACTIVOS POR PLAN      | #FF0000 (rojo)   | Label "(Últimos 90 días)" darkred 8px     |

## Grilla principal

- ttk.Treeview personalizado, 920x360 px, y=145.
- Columnas en orden exacto:

| Columna         | Ancho | Alineación | Color texto  | Formato                          |
| --------------- | ----- | ---------- | ------------ | -------------------------------- |
| idSocio         | 70px  | Izquierda  | Verde #008000| —                                |
| Nombre Completo | 220px | Izquierda  | Negro        | Apellidos, Nombres (truncado)    |
| Documento       | 120px | Izquierda  | Negro        | —                                |
| Nro             | 70px  | Izquierda  | Negro        | NroInscripcion                   |
| Vencimiento     | 120px | Izquierda  | Negro        | dd/mm/yyyy                       |
| FechaPago       | 120px | Izquierda  | Negro        | dd/mm/yyyy                       |
| Importe         | 90px  | Centrado   | Verde #008000| —                                |
| Saldo           | 70px  | Izquierda  | Verde #008000| —                                |
| Plan            | 150px | Izquierda  | Verde #008000| Nomenclatura del plan            |
| Estado          | 70px  | Izquierda  | —            | ✅ (verde 16x16) si activo       |

- Selección de fila: azul Windows clásico (#0078D7), texto blanco.
- Scroll vertical visible a la derecha, horizontal si necesario.
- Heading background: #E8E8E8, fuente small.

## Barra inferior

- Frame 950x45 px, y=515, fondo #E8E8E8.
- Controles:

| Control          | Tamaño  | Posición         | Estilo                          |
| ---------------- | ------- | ---------------- | ------------------------------- |
| Exportar a Excel | 95x30   | x=10, izquierda  | Botón clásico (relief raised)   |
| Exportar a PDF   | 95x30   | Al lado de Excel | Botón clásico                   |
| Socios: N        | —       | x=650, derecha   | Negrita, muestra conteo         |
| Salir            | 70x30   | x=860, der. fija | Destruye la ventana             |

- Botones Exportar: stub messagebox "Próximamente" por ahora.

## Paleta de colores

| Elemento                | Color     |
| ----------------------- | --------- |
| Fondo general           | #E8E8E8   |
| Fondo filtros           | #E8E8E8   |
| TextBox fondo           | #FFFFFF   |
| TextBox borde           | Gris Windows clásico |
| Radio ACTIVOS           | #008000   |
| Radio INACTIVOS         | #FF0000   |
| Radio ACTIVOS C/SALDO   | #FF6600   |
| Selección fila grilla   | #0078D7   |
| Texto verde columnas    | #008000   |
| Checkmark activo        | Verde #008000 |
| Texto (Últimos 90 días) | Dark red  |
| Botones                 | Sistema por defecto |

## Restricciones visuales

- NO bordes redondeados.
- NO sombras.
- NO Material Design ni web aesthetic.
- Fondos grises claros (#E8E8E8).
- Bordes Windows clásicos (groove, sunken, raised).
- Controles densos, sin padding excesivo.
- Fuentes del sistema (Segoe UI / Helvetica).
