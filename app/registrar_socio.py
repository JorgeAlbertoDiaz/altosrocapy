"""Registrar Socio — formulario de alta de socios.

Réplica WinForms 2015 de la ventana de registro de socios.
Distribución por regiones con coordenadas absolutas tipo VB.NET.
"""

import calendar
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 900, 600
BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#000000"
FG_GROUP = "#333333"
ENTRY_BG = "#FFFFFF"
BTN_SAVE = "#3B6FA0"
BTN_SAVE_ACTIVE = "#2D5A85"
GBD = 2  # groove border width


# ── Helpers ───────────────────────────────────────────────────────────────

def _next_id(table, column):
    """Get next integer ID for a table (TEXT column with numeric values)."""
    conn = db.get_connection()
    try:
        row = conn.execute(
            f"SELECT MAX(CAST({column} AS INTEGER)) FROM {table}"
        ).fetchone()
        max_val = row[0] if row and row[0] else 0
        return str(max_val + 1)
    finally:
        conn.close()


def _next_nro_inscripcion():
    """Get next NroInscripcion (max + 1)."""
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(CAST(NroInscripcion AS INTEGER)) FROM tbSocios "
            "WHERE NroInscripcion GLOB '[0-9]*'"
        ).fetchone()
        max_val = row[0] if row and row[0] else 0
        return str(max_val + 1)
    finally:
        conn.close()


def _calc_imc(altura_cm, peso_kg):
    """Calculate IMC from height (cm) and weight (kg)."""
    try:
        a = float(altura_cm)
        p = float(peso_kg)
        if a <= 0:
            return None, ""
        imc = p / ((a / 100) ** 2)
        if imc < 18.5:
            cls = "Bajo peso"
        elif imc < 25:
            cls = "Normal"
        elif imc < 30:
            cls = "Sobrepeso"
        else:
            cls = "Obesidad"
        return round(imc, 1), cls
    except (ValueError, TypeError, ZeroDivisionError):
        return None, ""


def _load_plans():
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT idPlan, Nomenclatura, Descripcion "
            "FROM tbPlan WHERE idPlan != '------' "
            "ORDER BY Descripcion"
        ).fetchall()
        return [(r["idPlan"], f"{r['Nomenclatura']} - {r['Descripcion']}") for r in rows]
    finally:
        conn.close()


def _save_socio(data):
    """Insert a new socio into tbSocios. Returns the new idSocio."""
    conn = db.get_connection()
    try:
        id_socio = _next_id("tbSocios", "idSocio")
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")

        conn.execute(
            "INSERT INTO tbSocios "
            "(idSocio, NroInscripcion, Apellidos, Nombres, Documento, Sexo, "
            " FecNac, Edad, Domicilio, Localidad, ObraSocial, Provincia, "
            " TelefonoUrgencia, Telefono, Email, InformacionMedica, AlergicoA, "
            " Medicacion, Altura, Peso, Estado, FechaAlta, id_Plan, Ocupacion, "
            " Password) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            " '1', ?, ?, ?, '')",
            (
                id_socio,
                data.get("nro_inscripcion", ""),
                data.get("apellidos", ""),
                data.get("nombres", ""),
                data.get("documento", ""),
                data.get("sexo", ""),
                data.get("fec_nac", ""),
                data.get("edad", ""),
                data.get("domicilio", ""),
                data.get("localidad", ""),
                data.get("obra_social", ""),
                data.get("provincia", ""),
                data.get("tel_urgencia", ""),
                data.get("telefono", ""),
                data.get("email", ""),
                data.get("info_medica", ""),
                data.get("alergico", ""),
                data.get("medicacion", ""),
                data.get("altura", ""),
                data.get("peso", ""),
                ahora,
                data.get("id_plan", ""),
                data.get("ocupacion", ""),
            ),
        )
        conn.commit()
        return id_socio
    finally:
        conn.close()


# ── Main Window ───────────────────────────────────────────────────────────

class RegistrarSocioWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Registrar Socio")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self._build()
        self._prefill_ids()

        # Documento gets focus
        self.entry_doc.focus_set()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # ================================================================
        # GroupBox 1 — Datos Personales
        # ================================================================
        gb1 = tk.LabelFrame(
            self, text=" Datos Personales ", bg=BG,
            font=("Helvetica", 9, "bold"), fg=FG_GROUP,
            relief="groove", bd=GBD, labelanchor="nw",
        )
        gb1.place(x=10, y=45, width=860, height=160)

        # ── Columna izquierda ──
        # Documento
        tk.Label(gb1, text="Documento", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=35, y=25)
        self.entry_doc = tk.Entry(
            gb1, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_doc.place(x=115, y=15, width=210, height=22)

        # Nro Inscripción
        tk.Label(gb1, text="Nro Inscripción", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=20, y=50)
        self.entry_nro = tk.Entry(
            gb1, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_nro.place(x=115, y=40, width=210, height=22)

        # Apellidos
        tk.Label(gb1, text="Apellidos", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=55, y=75)
        self.entry_apellido = tk.Entry(
            gb1, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_apellido.place(x=115, y=65, width=210, height=22)

        # Fecha Nacimiento
        tk.Label(gb1, text="Fec. de Nac.", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=25, y=100)
        self.entry_fnac = tk.Entry(
            gb1, bg=ENTRY_BG, fg="#888888", font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_fnac.place(x=115, y=90, width=210, height=22)
        self.entry_fnac.insert(0, "__/__/____")
        self.entry_fnac.bind("<FocusIn>", self._fnac_focus_in)
        self.entry_fnac.bind("<FocusOut>", self._fnac_focus_out)
        self.entry_fnac.bind("<KeyRelease>", self._fnac_format)

        # Sexo
        tk.Label(gb1, text="Sexo", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=70, y=125)
        self.sexo_var = tk.StringVar()
        self.combo_sexo = ttk.Combobox(
            gb1, textvariable=self.sexo_var,
            values=["Masculino", "Femenino", "Otro"],
            state="readonly", width=20,
        )
        self.combo_sexo.place(x=115, y=115, width=210, height=24)

        # ── Columna central ──
        # Nombres
        tk.Label(gb1, text="Nombres", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=370, y=75)
        self.entry_nombre = tk.Entry(
            gb1, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_nombre.place(x=430, y=65, width=210, height=22)

        # Ocupación
        tk.Label(gb1, text="Ocupación", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=360, y=100)
        self.entry_ocupacion = tk.Entry(
            gb1, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_ocupacion.place(x=430, y=90, width=210, height=22)

        # ── Columna derecha — Foto ──
        self.foto_frame = tk.Frame(gb1, bg="#000000")
        self.foto_frame.place(x=715, y=5, width=125, height=120)

        self.lbl_foto = tk.Label(
            self.foto_frame, text="👤", bg="#000000", fg="#FFFFFF",
            font=("Helvetica", 36),
        )
        self.lbl_foto.place(relx=0.5, rely=0.5, anchor="center")

        tk.Button(
            gb1, text="Capturar Foto", bg="#888888", fg="#FFF",
            font=("Helvetica", 8, "bold"), relief="flat",
            activebackground="#666666", cursor="hand2",
            command=self._capture_photo,
        ).place(x=715, y=130, width=125, height=22)

        # ================================================================
        # GroupBox 2 — Datos de Contacto
        # ================================================================
        gb2 = tk.LabelFrame(
            self, text=" Datos de Contacto ", bg=BG,
            font=("Helvetica", 9, "bold"), fg=FG_GROUP,
            relief="groove", bd=GBD, labelanchor="nw",
        )
        gb2.place(x=10, y=215, width=860, height=90)

        # ── Columna izquierda ──
        tk.Label(gb2, text="Domicilio", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=45, y=25)
        self.entry_domicilio = tk.Entry(
            gb2, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_domicilio.place(x=110, y=15, width=280, height=22)

        tk.Label(gb2, text="E-Mail", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=60, y=50)
        self.entry_email = tk.Entry(
            gb2, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_email.place(x=110, y=40, width=280, height=22)

        tk.Label(gb2, text="Teléfono", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=45, y=75)
        self.entry_telefono = tk.Entry(
            gb2, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_telefono.place(x=110, y=65, width=280, height=22)

        # ── Columna derecha ──
        tk.Label(gb2, text="Localidad", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=575, y=25)
        self.entry_localidad = tk.Entry(
            gb2, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_localidad.place(x=640, y=15, width=195, height=22)

        tk.Label(gb2, text="Obra Social", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=565, y=50)
        self.entry_obra_social = tk.Entry(
            gb2, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_obra_social.place(x=640, y=40, width=195, height=22)

        tk.Label(gb2, text="Teléfono de Urgencia", bg=BG,
                 font=("Helvetica", 9), fg=FG_LABEL).place(x=490, y=75)
        self.entry_tel_urgencia = tk.Entry(
            gb2, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_tel_urgencia.place(x=640, y=65, width=195, height=22)

        # ================================================================
        # GroupBox 3 — Datos Médicos
        # ================================================================
        gb3 = tk.LabelFrame(
            self, text=" Datos Médicos ", bg=BG,
            font=("Helvetica", 9, "bold"), fg=FG_GROUP,
            relief="groove", bd=GBD, labelanchor="nw",
        )
        gb3.place(x=10, y=320, width=860, height=125)

        # ── Columna izquierda ──
        tk.Label(gb3, text="Información de importancia", bg=BG,
                 font=("Helvetica", 9), fg=FG_LABEL).place(x=20, y=20)
        self.entry_info_medica = tk.Entry(
            gb3, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_info_medica.place(x=15, y=35, width=430, height=20)

        tk.Label(gb3, text="Alérgico a", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=35, y=65)
        self.entry_alergico = tk.Entry(
            gb3, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_alergico.place(x=105, y=60, width=340, height=22)

        tk.Label(gb3, text="Medicación", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=30, y=90)
        self.entry_medicacion = tk.Entry(
            gb3, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_medicacion.place(x=105, y=85, width=340, height=22)

        # ── Sector derecho ──
        tk.Label(gb3, text="Altura (cm)", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=520, y=35)
        self.entry_altura = tk.Entry(
            gb3, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_altura.place(x=580, y=35, width=60, height=20)
        self.entry_altura.bind("<KeyRelease>", lambda _: self._recalc_imc())

        tk.Label(gb3, text="Peso (kg)", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=525, y=60)
        self.entry_peso = tk.Entry(
            gb3, bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_peso.place(x=580, y=60, width=60, height=20)
        self.entry_peso.bind("<KeyRelease>", lambda _: self._recalc_imc())

        # IMC
        tk.Label(gb3, text="IMC:", bg=BG, font=("Helvetica", 9, "bold"),
                 fg=FG_LABEL).place(x=545, y=92)
        self.lbl_imc_val = tk.Label(gb3, text="0", bg=BG,
                                     font=("Helvetica", 9), fg=FG)
        self.lbl_imc_val.place(x=605, y=92)

        self.lbl_imc_cls = tk.Label(gb3, text="", bg=BG,
                                     font=("Helvetica", 9, "bold"), fg="#006600")
        self.lbl_imc_cls.place(x=685, y=92)

        # ================================================================
        # GroupBox 4 — Datos Socio
        # ================================================================
        gb4 = tk.LabelFrame(
            self, text=" Datos Socio ", bg=BG,
            font=("Helvetica", 9, "bold"), fg=FG_GROUP,
            relief="groove", bd=GBD, labelanchor="nw",
        )
        gb4.place(x=10, y=465, width=860, height=70)

        # Tipo Plan
        tk.Label(gb4, text="Tipo Plan", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=40, y=25)
        self.plan_var = tk.StringVar()
        self.combo_plan = ttk.Combobox(
            gb4, textvariable=self.plan_var,
            state="readonly", width=28,
        )
        self.combo_plan.place(x=100, y=15, width=280, height=24)

        # Load plans
        self._plans = _load_plans()
        self.combo_plan["values"] = [p[1] for p in self._plans]

        # Socio Desde
        tk.Label(gb4, text="Socio Desde:", bg=BG, font=("Helvetica", 9),
                 fg=FG_LABEL).place(x=650, y=25)
        self.fecha_alta_var = tk.StringVar(
            value=datetime.date.today().strftime("%d/%m/%Y"))
        self.entry_fecha_alta = tk.Entry(
            gb4, textvariable=self.fecha_alta_var,
            bg=ENTRY_BG, fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_fecha_alta.place(x=740, y=15, width=110, height=24)

        # ================================================================
        # Botonera inferior
        # ================================================================
        tk.Button(
            self, text="Guardar", bg=BTN_SAVE, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_SAVE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_save,
        ).place(x=670, y=550, width=90, height=30)

        tk.Button(
            self, text="Cancelar", bg="#888", fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground="#666", activeforeground="#FFF",
            cursor="hand2", command=self.destroy,
        ).place(x=780, y=550, width=90, height=30)

    # ── ID prefill ────────────────────────────────────────────────────────

    def _prefill_ids(self):
        next_id = _next_id("tbSocios", "idSocio")
        next_nro = _next_nro_inscripcion()
        self.entry_nro.configure(state="normal")
        self.entry_nro.delete(0, "end")
        self.entry_nro.insert(0, next_nro)
        self.entry_nro.configure(state="readonly")

    # ── Fecha Nacimiento mask ─────────────────────────────────────────────

    def _fnac_focus_in(self, _event):
        val = self.entry_fnac.get()
        if val == "__/__/____":
            self.entry_fnac.delete(0, "end")
            self.entry_fnac.configure(fg=FG)

    def _fnac_focus_out(self, _event):
        val = self.entry_fnac.get().strip()
        if not val:
            self.entry_fnac.configure(fg="#888888")
            self.entry_fnac.delete(0, "end")
            self.entry_fnac.insert(0, "__/__/____")

    def _fnac_format(self, _event):
        raw = self.entry_fnac.get()
        digits = "".join(c for c in raw if c.isdigit())
        formatted = ""
        for i, d in enumerate(digits[:8]):
            if i == 2 or i == 4:
                formatted += "/"
            formatted += d
        self.entry_fnac.delete(0, "end")
        self.entry_fnac.insert(0, formatted)

    # ── IMC ───────────────────────────────────────────────────────────────

    def _recalc_imc(self):
        imc, cls = _calc_imc(self.entry_altura.get(), self.entry_peso.get())
        self.lbl_imc_val.configure(text=str(imc) if imc is not None else "0")
        self.lbl_imc_cls.configure(text=cls)

    # ── Photo (placeholder) ───────────────────────────────────────────────

    def _capture_photo(self):
        messagebox.showinfo(
            "Foto",
            "Función de captura de foto no disponible en esta versión.\n"
            "Se utilizará la silueta por defecto.")

    # ── Save ──────────────────────────────────────────────────────────────

    def _on_save(self):
        doc = self.entry_doc.get().strip()
        apellido = self.entry_apellido.get().strip()
        nombre = self.entry_nombre.get().strip()

        if not doc:
            messagebox.showwarning("Guardar", "El campo Documento es obligatorio.")
            self.entry_doc.focus_set()
            return
        if not apellido:
            messagebox.showwarning("Guardar", "El campo Apellidos es obligatorio.")
            self.entry_apellido.focus_set()
            return
        if not nombre:
            messagebox.showwarning("Guardar", "El campo Nombres es obligatorio.")
            self.entry_nombre.focus_set()
            return

        # Get selected plan
        plan_idx = self.combo_plan.current()
        id_plan = self._plans[plan_idx][0] if plan_idx >= 0 else ""

        # Parse fecha nacimiento
        fnac_raw = self.entry_fnac.get().strip()
        fnac_db = ""
        edad = ""
        if fnac_raw and fnac_raw != "__/__/____":
            try:
                parts = fnac_raw.split("/")
                fnac_date = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                fnac_db = fnac_date.strftime("%Y-%m-%d")
                today = datetime.date.today()
                edad = str(today.year - fnac_date.year -
                          ((today.month, today.day) < (fnac_date.month, fnac_date.day)))
            except (ValueError, IndexError):
                messagebox.showwarning("Guardar", "Fecha de nacimiento inválida.")
                self.entry_fnac.focus_set()
                return

        # Parse fecha alta
        alta_raw = self.fecha_alta_var.get().strip()
        alta_db = ""
        if alta_raw:
            try:
                parts = alta_raw.split("/")
                alta_date = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                alta_db = alta_date.strftime("%Y-%m-%d")
            except (ValueError, IndexError):
                pass

        data = {
            "documento": doc,
            "nro_inscripcion": self.entry_nro.get().strip(),
            "apellidos": apellido,
            "nombres": nombre,
            "sexo": self.sexo_var.get(),
            "fec_nac": fnac_db,
            "edad": edad,
            "domicilio": self.entry_domicilio.get().strip(),
            "localidad": self.entry_localidad.get().strip(),
            "obra_social": self.entry_obra_social.get().strip(),
            "provincia": "",
            "tel_urgencia": self.entry_tel_urgencia.get().strip(),
            "telefono": self.entry_telefono.get().strip(),
            "email": self.entry_email.get().strip(),
            "info_medica": self.entry_info_medica.get().strip(),
            "alergico": self.entry_alergico.get().strip(),
            "medicacion": self.entry_medicacion.get().strip(),
            "altura": self.entry_altura.get().strip(),
            "peso": self.entry_peso.get().strip(),
            "id_plan": id_plan,
            "ocupacion": self.entry_ocupacion.get().strip(),
        }

        try:
            id_socio = _save_socio(data)
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}")
            return

        messagebox.showinfo(
            "Éxito",
            f"Socio registrado exitosamente.\n\n"
            f"ID: {id_socio}\n"
            f"Documento: {doc}\n"
            f"Nombre: {apellido}, {nombre}")
        self.destroy()


def open_window(parent=None):
    return RegistrarSocioWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
