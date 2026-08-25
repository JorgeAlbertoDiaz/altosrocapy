# Especificación de ventana: Principal (Dashboard MDI)

## Descripción general

Ventana principal del sistema, estilo WinForms/VB.NET clásico. Resolución 1366 x 768 px. Define el layout maestro —menú superior + sidebar izquierdo + área de trabajo— que reutilizará el resto de las ventanas de la aplicación.

## Layout

```
+----------------------------------------------------------------------+
| Admin  Alta de Datos  Gráficos Estadísticos  Ayuda   Cerrar Sesión U | <- menú superior (~30px, #EEEEEE)
+---------------------------------------------------+------------------+
|   Acceso Socios                                   |                  |
|   Registrar Socios                                |                  |
|   Consultar Estados Socios                        | (logo ALTOS ROCA)|
|   Consultar Socios                                | derecha, centrado|
|   Registrar Cobros                                |     vertical     |
|   Consultar Caja                                  |                  |
|   Historial de Cobros                             |                  |
|   Registrar Deudas                                |                  |
|   Admin Pantalla                                  |                  |
+---------------------------------------------------+------------------+
^ sidebar ~290px (#1A2430)          ^ área principal ~1070x700
```

## Barra de título

Barra estándar de Windows: "SG GYM - Sistema de Gestion de Gimnasios: ALTOS ROCA GYM - Usuario: \<USUARIO\>". El nombre del usuario logueado siempre visible.

## Menú superior

- Barra horizontal de ~30 px de alto, color `#EEEEEE`.
- Opciones alineadas a la izquierda: **Admin**, **Alta de Datos**, **Gráficos Estadísticos**, **Ayuda**.
- A la derecha, texto en negrita `#000000`: "Cerrar Sesión \<USUARIO\>".

## Sidebar izquierdo

- Ancho ~290 px, color `#1A2430` (alternativa `#18212D`), ocupa toda la altura.
- Solo opciones de menú (sin barra de iconos ni logo; se quitaron por decisión de diseño).

## Menú principal

- Texto blanco, fuente Segoe UI 11–12 px.
- Opciones separadas verticalmente, sin bordes, alineadas a la izquierda:
  Acceso Socios, Registrar Socios, Consultar Estados Socios, Consultar Socios, Registrar Cobros, Consultar Caja, Historial de Cobros, Registrar Deudas, Admin Pantalla.
- Hover con color `#C9A45B` (modernización respecto al original).

## Área principal

- Dimensiones ~1070 x 700 px, fondo `#010D2A` (azul casi negro) con degradado vertical suave.
- Logo corporativo ALTOS ROCA alineado **a la derecha**, **centrado verticalmente** (~40 px del borde derecho), decorativo. Si no hay `logo.png`, texto "ALTOS ROCA" en la misma posición.

## Comportamiento

Primera migración: cada opción del menú abre una ventana Toplevel independiente de 900 x 600 px, titulada con el nombre del módulo y contenido "[Módulo en construcción]".

Tecla global: **ESC cierra la ventana activa**, excepto la ventana principal, la de login y la futura ventana de Acceso Socios.

## Paleta de colores

| Elemento                     | Color     |
| ---------------------------- | --------- |
| Menú superior                | `#EEEEEE` |
| "Cerrar Sesión"              | `#000000` |
| Fondo sidebar                | `#1A2430` |
| Texto menú principal         | blanco    |
| Hover menú principal         | `#C9A45B` |
| Fondo área principal         | `#010D2A` |
| Degradado área (tono claro)  | `#061538` |
