# Especificación de ventana: Login

## Descripción general

Ventana de login de escritorio con diseño oscuro minimalista, compuesta por dos paneles verticales. El panel izquierdo aloja únicamente el logotipo de Altos Roca; el panel derecho contiene el formulario de acceso (título, campos y botón).

## Layout

- Dimensiones de la ventana: 730 x 330 px, proporción 2.2:1. Tamaño fijo, sin barra de menú tradicional.
- **Panel izquierdo**: ~27 % del ancho, fondo `#E9E9E9`. Únicamente el logotipo de Altos Roca centrado vertical y horizontalmente (logo disponible en `temps/logo.png`, no crítico en esta versión). Sin otros controles.
- **Panel derecho**: ~73 % restante, fondo oscuro uniforme `#232428` (alternativa `#26272B`), sin bordes visibles.
- Márgenes del panel derecho: padding superior 20 px, izquierdo ~65 px, derecho ~45 px.
- En la esquina superior derecha, botón X estilo Windows, color `#555555`, tamaño 12–14 px.

## Controles

- **Título LOGIN**: centrado horizontalmente sobre el panel derecho, mayúsculas, sans serif de peso ligero, color `#8D7B63`, 18–22 px.
- **Campo Usuario**: debajo del título, sin borde rectangular; solo línea inferior (`#707070`, 1 px, estilo material design), ~410 px de ancho, ~28 px de alto visual, texto `#F0F0F0`.
- **Campo Contraseña**: igual al campo Usuario, 410 px de ancho, separación vertical de 35 px.
- **Botón ACCEDER**: debajo de los campos, ~445 x 40 px, rectangular sin bordes, fondo `#404040`, texto `#E8D7C2`, sans serif mayúsculas de peso normal.

Jerarquía visual: 1) LOGIN, 2) botón ACCEDER, 3) campos de texto, 4) logo.

## Paleta de colores

| Elemento                  | Color     |
| ------------------------- | --------- |
| Fondo panel izquierdo     | `#E9E9E9` |
| Fondo panel derecho       | `#232428` |
| Título LOGIN              | `#8D7B63` |
| Línea inferior de campos  | `#707070` |
| Texto de campos           | `#F0F0F0` |
| Fondo botón ACCEDER       | `#404040` |
| Texto botón ACCEDER       | `#E8D7C2` |
| Botón cerrar (X)          | `#555555` |

## Reconstrucción en Tkinter

- Ventana fija de 730 x 330 px (`resizable(False, False)`), centrada en pantalla.
- Dos `Frame`: izquierdo al 27 % del ancho con `place`, derecho con el resto.
- Campos implementados como `Entry` con `relief="flat"` sobre un `Frame` contenedor; la línea inferior se simula con un `Frame` de altura 1 px y color `#707070`.
- Botón ACCEDER como `Button` plano de 445 x 40 px con los colores especificados.
- Logotipo cargado con `PhotoImage` desde `temps/logo.png`; si no está disponible, se omite silenciosamente.
