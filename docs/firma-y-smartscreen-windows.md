# Firma de código y avisos de Windows (SmartScreen / Smart App Control)

> Análisis del build de AltosRoca. Explica por qué Windows muestra avisos al
> ejecutar los `.exe`, qué opciones existen para evitarlos y cuáles sirven
> según el modo de distribución. No reemplaza la guía de compilación
> (`build/README.md`).

---

## 0. Resumen

- Windows **no obliga** a firmar un `.exe`. Un ejecutable sin firma arranca
  igual.
- Lo que aparece es un aviso de **confianza y reputación**, no un requisito
  legal ni técnico de firma.
- Hay **tres mecanismos distintos** que pueden mostrar carteles, y cada uno se
  resuelve de forma diferente:

| Mecanismo | Cuándo aparece | Qué evalúa | Se evita con |
|-----------|----------------|------------|--------------|
| **UAC** ("Editor desconocido") | Solo si el exe pide elevación | Manifest + firma del firmante | Manifest `asInvoker` (ya es el caso); la firma solo muestra el nombre del editor |
| **SmartScreen** ("Windows protegió tu PC") | Al abrir archivos **descargados de internet** | Reputación del hash y del certificado | Quitar Mark-of-the-Web, o firma con reputación |
| **Smart App Control** (Windows 11) | Al abrir cualquier exe, aunque no se haya descargado | Firma válida + reputación | Firma con CA pública, o desactivarlo |
| **Antivirus / Defender** | Al compilar, copiar o ejecutar | Heurística del binario | Menos heurísticas + reportar falso positivo |

- **No existe** una forma gratuita de que un `.exe` sea "globalmente
  confiable". Para uso interno sí hay atajos; para distribución pública por
  internet, no.

---

## 1. Estado actual del build

Verificado sobre `dist-windows/*.exe` (octubre 2026): **todos salen sin firma
Authenticode**. La tabla de certificados del encabezado PE está vacía
(`cert_dir_size = 0`).

El script `scripts/build_windows.py`:

- Compila con `--onefile --windowed` (la variante `Debug` se compila sin
  `--windowed`, es decir, con consola).
- Agrega `--hidden-import cv2`, `pygame.camera` y `pygame._camera`.
- **No** firma, **no** pasa `--noupx` y **no** agrega un recurso de versión.
- No pide elevación: el manifest por defecto de PyInstaller es `asInvoker`, así
  que esta app **no debería mostrar UAC**. Si algún día aparece UAC, revisar el
  manifest, no la firma.

Consecuencia: al bajar el `.zip` desde GitHub Actions, Edge/Chrome le agrega
**Mark-of-the-Web (MOTW)** al archivo; al extraerlo, el MOTW se propaga al
`.exe` y SmartScreen muestra "Windows protegió tu PC".

---

## 2. Qué significa cada aviso

### 2.1 UAC / "Editor desconocido"

Solo aparece si el ejecutable solicita privilegios de administrador. En este
proyecto **no ocurre**: el manifest es `asInvoker`. La firma no elimina UAC; lo
que hace es mostrar el nombre del editor en lugar de "Editor desconocido"
cuando el exe sí pide elevación.

### 2.2 SmartScreen

SmartScreen se activa principalmente con archivos que tienen **MOTW**
(descargados por navegador, email o mensajería). Consulta dos señales:

1. Reputación del **hash** del archivo (cuánta gente lo ejecutó sin problemas).
2. Reputación del **certificado** que lo firmó.

Un archivo nuevo, sin firma y con MOTW falla ambas. Por eso el cartel.
El botón "Más información → Ejecutar de todos modos" aparece para el usuario
final; en equipos con política restrictiva puede no aparecer.

### 2.3 Smart App Control (Windows 11)

Es más estricto que SmartScreen: evalúa **todos** los ejecutables, tengan o no
MOTW. Si no puede predecir que son seguros, exige una **firma válida de una CA
del programa Trusted Root de Microsoft**. Si no hay firma, bloquea.

- **No tiene lista blanca por app, ruta ni hash.**
- Solo se puede apagar (y en muchas instalaciones no se puede volver a
  prender sin reinstalar Windows), o firmar el binario.
- Un certificado **auto-firmado instalado localmente no alcanza** para Smart
  App Control: la CA debe ser públicamente confiable.

### 2.4 Antivirus / Microsoft Defender

No es lo mismo que SmartScreen. Defender puede marcar un `.exe` por heurística
aunque no tenga MOTW. Los disparadores típicos en este proyecto son:

- `--onefile`: el exe se autoextrae en `%TEMP%\_MEIxxxxx` en cada arranque.
- UPX (el `.spec` generado queda con `upx=True`).
- Imports dinámicos de cámara/OpenCV (`cv2`, `pygame`).
- Binario grande (~93 MB) y sin recurso de versión ni firma.

Un falso positivo de Defender **no se arregla** con SmartScreen: se reporta a
Microsoft o se reduce la heurística del build.

---

## 3. Opciones sin comprar certificado

### 3.1 Entregar sin Mark-of-the-Web (la más efectiva y gratis)

Si el programa se instala en PCs conocidas, evitar que el archivo se marque
como "descargado" elimina el cartel de SmartScreen sin firmar nada.

- Copiar por **USB** o por carpeta de red interna (no por navegador, email ni
  Drive).
- Si se descarga un `.zip`, **desbloquear el zip antes de extraer**:

  ```powershell
  Unblock-File .\AltosRoca-modern-x64.zip
  ```

  El MOTW del zip se propaga a los archivos extraídos; si se desbloquea
  primero, los `.exe` quedan limpios.
- Si ya está extraído:

  ```powershell
  Unblock-File .\AltosRoca.exe
  ```

- Verificar si un archivo tiene MOTW:

  ```powershell
  Get-Item .\AltosRoca.exe -Stream Zone.Identifier
  ```

> Esto **no** resuelve Smart App Control ni un antivirus que marque el
> binario. Tampoco sirve si el archivo se publica en internet.

### 3.2 Auto-firma + depósito de confianza local

Windows tiene dos almacenes relevantes:

| Almacén | Para qué sirve |
|---------|----------------|
| `Root` (Autoridades de certificación raíz de confianza) | Que Windows acepte la cadena del certificado |
| `TrustedPublisher` (Editores de confianza) | Que Windows reconozca al editor del software |

Firmar con un certificado propio y agregar su parte pública a `Root` y
`TrustedPublisher` hace que el exe tenga una firma **válida en esas PCs**. Esto
sirve para un despliegue controlado (gimnasio, pocas máquinas, GPO/Intune).

**Qué NO hace:** no le da reputación a SmartScreen. Si el archivo tiene MOTW,
SmartScreen puede seguir advirtiendo. Tampoco sirve para terceros ni para Smart
App Control.

#### Crear el certificado (máquina de build)

```powershell
# Ejecutar en PowerShell (no requiere admin si se usa CurrentUser)
New-Item -ItemType Directory -Force .\certs | Out-Null

$cert = New-SelfSignedCertificate `
  -Type CodeSigningCert `
  -Subject "CN=Altos Roca, O=Altos Roca, C=AR" `
  -FriendlyName "AltosRoca Code Signing" `
  -CertStoreLocation "Cert:\CurrentUser\My" `
  -NotAfter (Get-Date).AddYears(3)

$pfxPass = Read-Host "Password para el .pfx"
Export-PfxCertificate -Cert $cert `
  -FilePath .\certs\altosroca-codesign.pfx -Password (ConvertTo-SecureString $pfxPass -AsPlainText -Force) -Force
Export-Certificate -Cert $cert -FilePath .\certs\altosroca-codesign.cer -Force
```

> **Nunca versionar** el `.pfx`: contiene la clave privada. El `.cer` es público
> y sí se puede distribuir. El `.gitignore` del repo ya excluye `*.pfx` y
> `*.pvk`.

#### Firmar el ejecutable

```powershell
$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" |
  Sort-Object FullName -Descending | Select-Object -First 1

$pfxPass = Read-Host "Password del .pfx"
& $signtool.FullName sign `
  /fd SHA256 /td SHA256 `
  /tr http://timestamp.digicert.com `
  /f .\certs\altosroca-codesign.pfx /p $pfxPass `
  .\dist-windows\AltosRoca.exe
```

- `/tr` + `/td` agregan **timestamp**: la firma sigue siendo válida aunque el
  certificado venza.
- Firmar **después** de compilar y **antes** de copiar/zippear. Cualquier
  modificación posterior al exe invalida la firma.
- Repetir por cada variante (`AltosRoca-64.exe`, `AltosRocaDebug.exe`, etc.).

#### Instalar la confianza en cada PC destino (como administrador)

```powershell
certutil -addstore -f Root             .\certs\altosroca-codesign.cer
certutil -addstore -f TrustedPublisher .\certs\altosroca-codesign.cer
```

Solo para el usuario actual (sin admin):

```powershell
certutil -user -addstore -f Root             .\certs\altosroca-codesign.cer
certutil -user -addstore -f TrustedPublisher .\certs\altosroca-codesign.cer
```

En varias PCs, mejor por directiva:

- **GPO**: `Configuración del equipo → Directivas → Configuración de Windows →
  Configuración de seguridad → Directivas de clave pública → Autoridades de
  certificación raíz de confianza` y `Editores de confianza`.
- **Intune**: perfil de certificado de confianza para `Root`; desplegar el
  `.cer` de `TrustedPublisher` por script o perfil según la licencia.

### 3.3 WDAC / AppLocker (equipos administrados)

Si las PCs están administradas, se puede autorizar el exe por **hash, ruta o
firmante** sin comprar un certificado público:

- **AppLocker**: regla de tipo "Publisher" usando el certificado auto-firmado
  (requiere tener la CA en el almacén de confianza), o regla por hash.
- **WDAC (App Control for Business)**: política que permita el firmante o el
  hash. Es la vía correcta en entornos corporativos.

Esto no evita SmartScreen por sí solo, pero sí evita bloqueos de política y
permite distribuir de forma controlada.

### 3.4 Exclusión de Microsoft Defender

Como último recurso en PCs controladas:

- `Seguridad de Windows → Protección antivirus y contra amenazas →
  Administrar la configuración → Exclusiones`.
- O por GPO/Intune para el proceso o la carpeta del exe.

Es una medida local, no distribuible, y baja la seguridad del equipo. **No
usar** como solución para clientes o terceros.

### 3.5 Reportar un falso positivo a Microsoft

Si Defender marca el exe:

1. Enviar el archivo (o el hash) en
   <https://www.microsoft.com/en-us/wdsi/filesubmission>.
2. Elegir "Software developer" / falso positivo.
3. Microsoft analiza y, si corresponde, actualiza firmas.

No elimina SmartScreen, pero sí los falsos positivos del antivirus.

### 3.6 Bajar el perfil heurístico del build

Cambios recomendados en `scripts/build_windows.py` (no aplicados todavía):

- **`--noupx`**: UPX es un disparador clásico de heurísticas. El script no lo
  desactiva y los `.spec` generados quedan con `upx=True`.
- **`--onedir` en lugar de `--onefile`**: evita la autoextracción en `%TEMP%` en
  cada arranque. Como contrapartida, la distribución pasa a ser una carpeta
  (más archivos) en lugar de un solo `.exe`. Para un programa de ~93 MB con
  OpenCV, suele ser más rápido y más amigable para el antivirus.
- **Recurso de versión** (`--version-file version_info.txt`) con nombre de
  producto, empresa y versión. No da reputación por sí solo, pero hace al
  binario más "normal" y mejora la trazabilidad.
- Evitar ejecutar binarios descargados en tiempo de ejecución (no aplica hoy).

---

## 4. Opciones con certificado

### 4.1 Azure Artifact Signing (antes "Trusted Signing")

Es la opción recomendada por Microsoft para distribución fuera de la Store.

| Dato | Valor (octubre 2026) |
|------|----------------------|
| Costo | ~US$9.99/mes |
| Requisito | Suscripción de Azure **paga** (no free/trial) |
| Organizaciones | EE. UU., Canadá, UE y Reino Unido; antigüedad fiscal verificable ≥ 3 años |
| Individuos | Solo EE. UU. y Canadá |
| Validación | Identidad verificada por Microsoft (días hábiles) |
| Firma | `signtool` + Artifact Signing Client Tools, o GitHub Action `azure/trusted-signing-action` |
| SmartScreen | La reputación se ata a la identidad y crece con el tiempo; los primeros releases pueden advertir igual |

> Para una organización o un particular en **Argentina no está disponible**.
> En ese caso, la alternativa es un certificado OV de una CA tradicional.

### 4.2 Certificado OV (Organization Validated)

| Dato | Valor (octubre 2026) |
|------|----------------------|
| Costo | ~US$150–400/año |
| Validación | Identidad de la empresa/persona por la CA (días) |
| Clave privada | Token USB/HSM o servicio cloud (desde 2023 la CA/B Forum no permite `.pfx` suelto) |
| SmartScreen | Reputación crece con el tiempo; **no es instantáneo** |
| Vigencia | Máx. ~460 días para certificados emitidos desde marzo 2026 |

Es la vía realista para distribuir desde Argentina. CAs habituales: DigiCert,
Sectigo, GlobalSign, Certum.

### 4.3 Certificado EV (Extended Validation)

- ~US$400+/año, también con token/HSM.
- **Desde 2024 ya no da bypass instantáneo de SmartScreen**: Microsoft lo trata
  igual que OV para reputación. No se justifica solo por evitar el cartel.

### 4.4 Microsoft Store

La Store **firma el paquete** al publicarlo, así que la instalación no muestra
SmartScreen. Requiere empaquetar como MSIX y una cuenta de desarrollador; para
una app interna de gimnasio es sobredimensionado. No aplica a los `.zip` que
genera el workflow actual.

---

## 5. Integrar la firma en el build

### 5.1 Build local

El flujo actual es: `build_windows.py` compila y copia al destino. La firma
debe insertarse **entre la compilación y la copia** (o firmar en el destino
antes de zippear):

```text
PyInstaller → signtool sign → copiar a --dest → comprimir
```

`scripts/build_windows.py` no tiene hoy un flag de firma. La forma menos
invasiva es un script `scripts/sign_windows.ps1` que firme todos los `.exe` de
una carpeta, invocado después del build. Si se quiere integrado, agregar un
flag `--sign` que reciba el `.pfx` por variable de entorno (nunca por
argumento, para no dejarlo en el historial).

### 5.2 GitHub Actions

El workflow `.github/workflows/build-windows.yml` compila, comprime y sube
artefactos. Para firmar:

1. Guardar el `.pfx` en base64 en un **secret** (`CODESIGN_PFX_B64`) y la
   password en otro (`CODESIGN_PFX_PASSWORD`).
2. En un paso posterior al build, decodificar el `.pfx` a un archivo temporal y
   ejecutar `signtool` con timestamp.
3. Borrar el `.pfx` temporal al final (`if: always()`).
4. Firmar **antes** de `Compress-Archive`.

Con Azure Artifact Signing, en cambio, se usa la acción oficial
`azure/trusted-signing-action` con federación de identidad (sin secretos de
clave privada).

> Importante: el `.zip` que sube GitHub Actions se descarga con MOTW. Aunque el
> exe esté firmado, los primeros releases pueden mostrar SmartScreen hasta que
> el certificado acumule reputación. La firma **no** es magia instantánea.

---

## 6. Verificación

```powershell
# Estado de la firma
Get-AuthenticodeSignature .\AltosRoca.exe |
  Format-List Status, StatusMessage, SignerCertificate

# Con Sysinternals (opcional)
sigcheck -a -h .\AltosRoca.exe
```

Estados esperados:

- `NotSigned`: no hay firma (estado actual del repo).
- `HashMismatch`: el exe se modificó después de firmar.
- `UnknownError` / `UntrustedRoot`: firmado con un certificado que esa PC no
  confía (falta instalar la CA).
- `Valid`: firma correcta y cadena de confianza OK.

También se puede ver el cartel de propiedades del archivo: con firma y
timestamp aparece la pestaña **Firmas digitales**.

---

## 7. Limitaciones y advertencias

- **Auto-firmar no sirve para terceros.** Un certificado auto-firmado solo es
  confiable en las máquinas donde se instaló su CA. SmartScreen lo ignora.
- **Smart App Control no tiene excepciones.** Ni ruta, ni hash, ni "ejecutar de
  todos modos". Solo firma pública o desactivarlo.
- **La reputación es por archivo y por certificado.** Cambiar el exe (nueva
  compilación, nueva versión) reinicia la reputación del hash; el certificado
  ayuda a heredar parte de la confianza, pero no la garantiza.
- **No modificar un exe firmado.** Cualquier byte cambia el hash e invalida la
  firma.
- **Windows 7 y SHA-256:** una firma SHA-256 requiere la actualización
  **KB3033929** en Windows 7. Si se firma la variante win7-x86, verificar que
  esa PC tenga la actualización; si no, la firma no se valida (el exe puede
  correr igual, pero Windows no la reconoce).
- **El certificado no arregla bugs ni malware.** Solo identifica al editor y
  permite construir reputación.
- **No existe un "registro global gratis".** El programa Trusted Root de
  Microsoft es para CAs auditadas, no para desarrolladores individuales.

---

## 8. Recomendación para AltosRoca

### Escenario A: instalación interna en las PCs del gimnasio (recomendado)

1. Entregar por USB o carpeta de red; si se descarga, `Unblock-File` al zip
   antes de extraer.
2. Auto-firmar los exe y desplegar el `.cer` en `Root` + `TrustedPublisher` por
   GPO/script en cada PC.
3. Si Defender marca el exe, reportar el falso positivo y evaluar `--noupx` /
   `--onedir`.
4. Costo: **$0**. SmartScreen puede seguir advirtiendo si el archivo tiene
   MOTW; el resto de los avisos desaparece.

### Escenario B: distribución pública por internet

1. Certificado **OV** (o Azure Artifact Signing si la organización califica).
2. Firmar cada release con timestamp, en CI.
3. Asumir que los primeros releases pueden mostrar SmartScreen mientras se
   construye reputación (semanas).
4. Publicar el hash SHA-256 junto a cada release para que el usuario verifique
   lo que bajó.
5. Costo: **~US$150–400/año** (o ~US$120/año con Artifact Signing, si aplica).

### Escenario C: equipo con Smart App Control activo

No hay atajo: firmar con CA pública o desactivar Smart App Control en esa PC
(con el costo de seguridad que implica).

---

## 9. Referencias

- Opciones de firma de código en Windows:
  <https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options>
- Reputación de SmartScreen para desarrolladores:
  <https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation>
- Microsoft Defender SmartScreen (overview):
  <https://learn.microsoft.com/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/>
- Smart App Control (FAQ):
  <https://support.microsoft.com/windows/smart-app-control-frequently-asked-questions-285ea03d-fa88-4d56-882e-6698afdb7003>
- Mark-of-the-Web / Attachment Manager:
  <https://support.microsoft.com/windows/security/information-about-the-attachment-manager-in-microsoft-windows>
- `Unblock-File`:
  <https://learn.microsoft.com/powershell/module/microsoft.powershell.utility/unblock-file>
- Envío de archivos para análisis (falsos positivos):
  <https://www.microsoft.com/en-us/wdsi/filesubmission>
