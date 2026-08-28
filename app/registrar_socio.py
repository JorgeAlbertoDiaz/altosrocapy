"""Registrar Socio — formulario de alta de socios.

Réplica WinForms 2015 de la ventana de registro de socios.
Distribución por regiones con coordenadas absolutas tipo VB.NET.
"""

import calendar
import datetime
import os
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

try:
    from app import db
except ImportError:
    import db

try:
    from app import socios_foto
except ImportError:
    import socios_foto

try:
    import pygame
except ImportError:
    pygame = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 900, 650
BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#000000"
FG_GROUP = "#333333"
ENTRY_BG = "#FFFFFF"
BTN_SAVE = "#3B6FA0"
BTN_SAVE_ACTIVE = "#2D5A85"
GBD = 2  # groove border width

# Font
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")

# Entry dimensions per column
COL_L_W = 220   # left column entry width
COL_C_W = 220   # center column entry width
COL_R_W = 195   # right column entry width
EH = 22         # entry height


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


def _load_socio(id_socio):
    """Load a socio's full record. Returns a dict or None."""
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT idSocio, NroInscripcion, Apellidos, Nombres, Documento, Sexo, "
            " FecNac, Edad, Domicilio, Localidad, ObraSocial, Provincia, "
            " TelefonoUrgencia, Telefono, Email, InformacionMedica, AlergicoA, "
            " Medicacion, Altura, Peso, Estado, FechaAlta, FechaBaja, Password, "
            " id_Plan, Ocupacion, pathImage "
            "FROM tbSocios WHERE idSocio = ?",
            (str(id_socio),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _save_socio(data, socio_id=None):
    """Insert (socio_id None) or update (socio_id given) a socio.

    En edición NUNCA se tocan: idSocio, NroInscripcion, EStado, FechaAlta,
    FechaBaja, Password (campos de sistema). Devuelve el idSocio.
    """
    conn = db.get_connection()
    try:
        if socio_id is None:
            # ── ALTA: INSERT con id auto-generado ──
            id_socio = _next_id("tbSocios", "idSocio")
            ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
            conn.execute(
                "INSERT INTO tbSocios "
                "(idSocio, NroInscripcion, Apellidos, Nombres, Documento, Sexo, "
                " FecNac, Edad, Domicilio, Localidad, ObraSocial, Provincia, "
                " TelefonoUrgencia, Telefono, Email, InformacionMedica, AlergicoA, "
                " Medicacion, Altura, Peso, Estado, FechaAlta, id_Plan, Ocupacion, "
                " Password, pathImage) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                " '1', ?, ?, ?, '', ?)",
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
                    data.get("pathImage", ""),
                ),
            )
        else:
            # ── EDICIÓN: UPDATE, no tocar campos de sistema ──
            id_socio = str(socio_id)
            conn.execute(
                "UPDATE tbSocios SET "
                " Apellidos=?, Nombres=?, Documento=?, Sexo=?, FecNac=?, Edad=?, "
                " Domicilio=?, Localidad=?, ObraSocial=?, Provincia=?, "
                " TelefonoUrgencia=?, Telefono=?, Email=?, InformacionMedica=?, "
                " AlergicoA=?, Medicacion=?, Altura=?, Peso=?, id_Plan=?, "
                " Ocupacion=?, pathImage=? "
                "WHERE idSocio=?",
                (
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
                    data.get("id_plan", ""),
                    data.get("ocupacion", ""),
                    data.get("pathImage", ""),
                    id_socio,
                ),
            )
        conn.commit()
        return id_socio
    finally:
        conn.close()


# ── Main Window ───────────────────────────────────────────────────────────

class RegistrarSocioWindow(tk.Toplevel):
    def __init__(self, parent=None, socio_id=None):
        super().__init__(parent)
        self.title("Editar Socio" if socio_id else "Registrar Socio")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self.socio_id = str(socio_id) if socio_id else None
        self._plans = _load_plans()
        self._foto_rel = None
        self._foto_doc = None
        self._foto_origen = None

        self._build()

        if self.socio_id:
            self._load_existing()
        else:
            self._prefill_ids()

        if self.socio_id:
            self.combo_plan.focus_set()
        else:
            # Documento gets focus
            self.entry_doc.focus_set()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # ================================================================
        # GroupBox 1 — Datos Personales  (x=10, y=45, 860x190)
        # ================================================================
        gb1 = tk.LabelFrame(
            self, text=" Datos Personales ", bg=BG,
            font=FN_B, fg=FG_GROUP, relief="groove", bd=GBD, labelanchor="nw",
        )
        gb1.place(x=10, y=45, width=860, height=190)

        # ── Columna izquierda ──
        # Row 1: Documento
        tk.Label(gb1, text="Documento", bg=BG, font=FN, fg=FG_LABEL).place(x=30, y=25)
        self.entry_doc = tk.Entry(gb1, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_doc.place(x=115, y=18, width=COL_L_W, height=EH)

        # Row 2: Nro Inscripción
        tk.Label(gb1, text="Nro Inscripción", bg=BG, font=FN, fg=FG_LABEL).place(x=15, y=52)
        self.entry_nro = tk.Entry(gb1, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_nro.place(x=115, y=45, width=COL_L_W, height=EH)

        # Row 3: Apellidos
        tk.Label(gb1, text="Apellidos", bg=BG, font=FN, fg=FG_LABEL).place(x=50, y=79)
        self.entry_apellido = tk.Entry(gb1, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_apellido.place(x=115, y=72, width=COL_L_W, height=EH)

        # Row 4: Fecha Nacimiento (DateEntry)
        tk.Label(gb1, text="Fec. de Nac.", bg=BG, font=FN, fg=FG_LABEL).place(x=25, y=106)
        if DateEntry is not None:
            self.dt_fnac = DateEntry(
                gb1, width=12, background="#3B6FA0", foreground="white",
                borderwidth=1, date_pattern="dd/mm/yyyy",
                font=FN,
            )
            self.dt_fnac.place(x=115, y=100, width=COL_L_W, height=24)
        else:
            self.dt_fnac = None
            self.entry_fnac = tk.Entry(gb1, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
            self.entry_fnac.place(x=115, y=100, width=COL_L_W, height=EH)

        # Row 5: Sexo
        tk.Label(gb1, text="Sexo", bg=BG, font=FN, fg=FG_LABEL).place(x=68, y=133)
        self.sexo_var = tk.StringVar()
        self.combo_sexo = ttk.Combobox(
            gb1, textvariable=self.sexo_var,
            values=["Masculino", "Femenino", "Otro"],
            state="readonly", width=20,
        )
        self.combo_sexo.place(x=115, y=127, width=COL_L_W, height=24)

        # ── Columna central ──
        # Row 3: Nombres (misma fila que Apellidos)
        tk.Label(gb1, text="Nombres", bg=BG, font=FN, fg=FG_LABEL).place(x=340, y=79)
        self.entry_nombre = tk.Entry(gb1, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_nombre.place(x=400, y=72, width=COL_C_W, height=EH)

        # Row 4: Ocupación (misma fila que Fec. Nac.)
        tk.Label(gb1, text="Ocupación", bg=BG, font=FN, fg=FG_LABEL).place(x=338, y=106)
        self.entry_ocupacion = tk.Entry(gb1, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_ocupacion.place(x=400, y=100, width=COL_C_W, height=EH)

        # ── Columna derecha — Foto ──
        self.foto_frame = tk.Frame(gb1, bg="#000000")
        # Foto centrada verticalmente: (190-125)/2 = 32
        self.foto_frame.place(x=720, y=22, width=125, height=125)

        self.lbl_foto = tk.Label(
            self.foto_frame, text="👤", bg="#000000", fg="#FFFFFF",
            font=("Helvetica", 40),
        )
        self.lbl_foto.place(relx=0.5, rely=0.5, anchor="center")

        tk.Button(
            gb1, text="Capturar Foto", bg="#888888", fg="#FFF",
            font=("Helvetica", 8, "bold"), relief="flat",
            activebackground="#666666", cursor="hand2",
            command=self._capture_photo,
        ).place(x=720, y=152, width=125, height=24)

        # ================================================================
        # GroupBox 2 — Datos de Contacto  (x=10, y=243, 860x105)
        # ================================================================
        gb2 = tk.LabelFrame(
            self, text=" Datos de Contacto ", bg=BG,
            font=FN_B, fg=FG_GROUP, relief="groove", bd=GBD, labelanchor="nw",
        )
        gb2.place(x=10, y=243, width=860, height=105)

        # ── Columna izquierda ──
        tk.Label(gb2, text="Domicilio", bg=BG, font=FN, fg=FG_LABEL).place(x=45, y=20)
        self.entry_domicilio = tk.Entry(gb2, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_domicilio.place(x=110, y=13, width=280, height=EH)

        tk.Label(gb2, text="E-Mail", bg=BG, font=FN, fg=FG_LABEL).place(x=62, y=46)
        self.entry_email = tk.Entry(gb2, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_email.place(x=110, y=39, width=280, height=EH)

        tk.Label(gb2, text="Teléfono", bg=BG, font=FN, fg=FG_LABEL).place(x=48, y=72)
        self.entry_telefono = tk.Entry(gb2, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_telefono.place(x=110, y=65, width=280, height=EH)

        # ── Columna derecha ──
        tk.Label(gb2, text="Localidad", bg=BG, font=FN, fg=FG_LABEL).place(x=575, y=20)
        self.entry_localidad = tk.Entry(gb2, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_localidad.place(x=640, y=13, width=COL_R_W, height=EH)

        tk.Label(gb2, text="Obra Social", bg=BG, font=FN, fg=FG_LABEL).place(x=565, y=46)
        self.entry_obra_social = tk.Entry(gb2, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_obra_social.place(x=640, y=39, width=COL_R_W, height=EH)

        tk.Label(gb2, text="Tel. de Urgencia", bg=BG, font=FN, fg=FG_LABEL).place(x=540, y=72)
        self.entry_tel_urgencia = tk.Entry(gb2, bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1)
        self.entry_tel_urgencia.place(x=640, y=65, width=COL_R_W, height=EH)

        # ================================================================
        # GroupBox 3 — Datos Médicos  (x=10, y=356, 860x135)
        # ================================================================
        gb3 = tk.LabelFrame(
            self, text=" Datos Médicos ", bg=BG,
            font=FN_B, fg=FG_GROUP, relief="groove", bd=GBD, labelanchor="nw",
        )
        gb3.place(x=10, y=356, width=860, height=135)

        # ── Columna izquierda ──
        tk.Label(gb3, text="Información de importancia", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=15, y=18)
        self.entry_info_medica = tk.Entry(gb3, bg=ENTRY_BG, fg=FG, font=FN,
                                          relief="solid", bd=1)
        self.entry_info_medica.place(x=15, y=35, width=430, height=EH)

        tk.Label(gb3, text="Alérgico a", bg=BG, font=FN, fg=FG_LABEL).place(x=30, y=65)
        self.entry_alergico = tk.Entry(gb3, bg=ENTRY_BG, fg=FG, font=FN,
                                       relief="solid", bd=1)
        self.entry_alergico.place(x=105, y=60, width=340, height=EH)

        tk.Label(gb3, text="Medicación", bg=BG, font=FN, fg=FG_LABEL).place(x=30, y=93)
        self.entry_medicacion = tk.Entry(gb3, bg=ENTRY_BG, fg=FG, font=FN,
                                         relief="solid", bd=1)
        self.entry_medicacion.place(x=105, y=88, width=340, height=EH)

        # ── Sector derecho ──
        tk.Label(gb3, text="Altura (cm)", bg=BG, font=FN, fg=FG_LABEL).place(x=500, y=35)
        self.entry_altura = tk.Entry(gb3, bg=ENTRY_BG, fg=FG, font=FN,
                                     relief="solid", bd=1)
        self.entry_altura.place(x=580, y=35, width=65, height=EH)
        self.entry_altura.bind("<KeyRelease>", lambda _: self._recalc_imc())

        tk.Label(gb3, text="Peso (kg)", bg=BG, font=FN, fg=FG_LABEL).place(x=505, y=63)
        self.entry_peso = tk.Entry(gb3, bg=ENTRY_BG, fg=FG, font=FN,
                                   relief="solid", bd=1)
        self.entry_peso.place(x=580, y=63, width=65, height=EH)
        self.entry_peso.bind("<KeyRelease>", lambda _: self._recalc_imc())

        # IMC row — aligned horizontally
        tk.Label(gb3, text="IMC:", bg=BG, font=FN_B, fg=FG_LABEL).place(x=500, y=95)
        self.lbl_imc_val = tk.Label(gb3, text="0", bg=BG, font=FN, fg=FG)
        self.lbl_imc_val.place(x=540, y=95)
        self.lbl_imc_cls = tk.Label(gb3, text="", bg=BG, font=FN_B, fg="#006600")
        self.lbl_imc_cls.place(x=580, y=95)

        # ================================================================
        # GroupBox 4 — Datos Socio  (x=10, y=499, 860x70)
        # ================================================================
        gb4 = tk.LabelFrame(
            self, text=" Datos Socio ", bg=BG,
            font=FN_B, fg=FG_GROUP, relief="groove", bd=GBD, labelanchor="nw",
        )
        gb4.place(x=10, y=499, width=860, height=70)

        # Tipo Plan
        tk.Label(gb4, text="Tipo Plan", bg=BG, font=FN, fg=FG_LABEL).place(x=30, y=25)
        self.plan_var = tk.StringVar()
        self.combo_plan = ttk.Combobox(
            gb4, textvariable=self.plan_var,
            state="readonly", width=28,
        )
        self.combo_plan.place(x=95, y=18, width=280, height=24)
        self.combo_plan["values"] = [p[1] for p in self._plans]

        # Socio Desde
        tk.Label(gb4, text="Socio Desde:", bg=BG, font=FN, fg=FG_LABEL).place(x=640, y=25)
        if DateEntry is not None:
            self.dt_alta = DateEntry(
                gb4, width=10, background="#3B6FA0", foreground="white",
                borderwidth=1, date_pattern="dd/mm/yyyy",
                font=FN,
            )
            self.dt_alta.place(x=735, y=18, width=115, height=24)
        else:
            self.dt_alta = None
            self.fecha_alta_var = tk.StringVar(
                value=datetime.date.today().strftime("%d/%m/%Y"))
            self.entry_fecha_alta = tk.Entry(
                gb4, textvariable=self.fecha_alta_var,
                bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1,
            )
            self.entry_fecha_alta.place(x=735, y=18, width=115, height=24)

        # ================================================================
        # Botonera inferior
        # ================================================================
        tk.Button(
            self, text="Guardar", bg=BTN_SAVE, fg="#FFF",
            font=FN_B, relief="flat",
            activebackground=BTN_SAVE_ACTIVE, activeforeground="#FFF",
            cursor="hand2",             command=self._on_save,
        ).place(x=670, y=590, width=90, height=30)

        tk.Button(
            self, text="Cancelar", bg="#888", fg="#FFF",
            font=FN_B, relief="flat",
            activebackground="#666", activeforeground="#FFF",
            cursor="hand2", command=self.destroy,
        ).place(x=780, y=590, width=90, height=30)

    # ── ID prefill ────────────────────────────────────────────────────────

    def _prefill_ids(self):
        next_nro = _next_nro_inscripcion()
        self.entry_nro.configure(state="normal")
        self.entry_nro.delete(0, "end")
        self.entry_nro.insert(0, next_nro)
        self.entry_nro.configure(state="readonly")

    # ── Load existing socio (edit mode) ──────────────────────────────────

    def _load_existing(self):
        socio = _load_socio(self.socio_id)
        if socio is None:
            messagebox.showerror(
                "Error",
                f"Socio ID {self.socio_id} no encontrado.\n"
                "La edición se cerrará.", parent=self)
            self.destroy()
            return

        data = socio
        self.entry_doc.delete(0, "end")
        self.entry_doc.insert(0, data.get("Documento") or "")

        self.entry_nro.configure(state="normal")
        self.entry_nro.delete(0, "end")
        self.entry_nro.insert(0, data.get("NroInscripcion") or "")
        self.entry_nro.configure(state="readonly")

        self.entry_apellido.delete(0, "end")
        self.entry_apellido.insert(0, data.get("Apellidos") or "")

        # Fecha nacimiento
        fnac = data.get("FecNac") or ""
        if self.dt_fnac is not None:
            try:
                d = datetime.datetime.strptime(str(fnac)[:10], "%Y-%m-%d").date()
                self.dt_fnac.set_date(d)
            except (ValueError, TypeError):
                pass
        else:
            self.entry_fnac.delete(0, "end")
            if fnac:
                try:
                    d = datetime.datetime.strptime(str(fnac)[:10], "%Y-%m-%d").date()
                    self.entry_fnac.insert(0, d.strftime("%d/%m/%Y"))
                except (ValueError, TypeError):
                    pass

        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, data.get("Nombres") or "")
        self.entry_ocupacion.delete(0, "end")
        self.entry_ocupacion.insert(0, data.get("Ocupacion") or "")

        # Sexo
        sexo = data.get("Sexo") or ""
        valores_sexo = ["Masculino", "Femenino", "Otro"]
        self.sexo_var.set(sexo if sexo in valores_sexo
                          else ({'M': 'Masculino', 'F': 'Femenino'}.get(sexo, "")))

        # Datos de contacto
        self._set_entry(self.entry_domicilio, data.get("Domicilio"))
        self._set_entry(self.entry_email, data.get("Email"))
        self._set_entry(self.entry_telefono, data.get("Telefono"))
        self._set_entry(self.entry_localidad, data.get("Localidad"))
        self._set_entry(self.entry_obra_social, data.get("ObraSocial"))
        self._set_entry(self.entry_tel_urgencia, data.get("TelefonoUrgencia"))

        # Datos médicos
        self._set_entry(self.entry_info_medica, data.get("InformacionMedica"))
        self._set_entry(self.entry_alergico, data.get("AlergicoA"))
        self._set_entry(self.entry_medicacion, data.get("Medicacion"))
        self._set_entry(self.entry_altura, data.get("Altura"))
        self._set_entry(self.entry_peso, data.get("Peso"))
        self._recalc_imc()

        # Datos socio — plan
        id_plan = data.get("id_Plan")
        idx = next((i for i, (pid, _) in enumerate(self._plans)
                    if str(pid) == str(id_plan)), -1)
        if idx >= 0:
            self.combo_plan.current(idx)
        else:
            self.plan_var.set("")

        # Socio Desde (FechaAlta) — solo se muestra, no se edita
        alta = data.get("FechaAlta") or ""
        if self.dt_alta is not None:
            try:
                d = datetime.datetime.strptime(str(alta)[:10], "%Y-%m-%d").date()
                self.dt_alta.set_date(d)
            except (ValueError, TypeError):
                pass
        else:
            self.entry_fecha_alta.delete(0, "end")
            if alta:
                try:
                    d = datetime.datetime.strptime(str(alta)[:10], "%Y-%m-%d").date()
                    self.entry_fecha_alta.insert(0, d.strftime("%d/%m/%Y"))
                except (ValueError, TypeError):
                    pass

        # Foto
        path_img = data.get("pathImage") or ""
        doc_actual = data.get("Documento") or ""
        if path_img:
            photo = socios_foto.cargar_para_tk(path_img, 125)
            if photo is not None:
                self._foto_rel = path_img
                self._foto_doc = doc_actual
                self._foto_origen = socios_foto.foto_abs_path(path_img)
                self._aplicar_foto(path_img)
            else:
                self._foto_rel = None
                self._foto_doc = doc_actual
                self._foto_origen = None
                self.lbl_foto.configure(text="👤")
        else:
            self._foto_rel = None
            self._foto_doc = doc_actual
            self._foto_origen = None
            self.lbl_foto.configure(text="👤")

    def _set_entry(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value or "")

    # ── IMC ───────────────────────────────────────────────────────────────

    def _recalc_imc(self):
        imc, cls = _calc_imc(self.entry_altura.get(), self.entry_peso.get())
        self.lbl_imc_val.configure(text=str(imc) if imc is not None else "0")
        self.lbl_imc_cls.configure(text=cls)

    # ── Photo ────────────────────────────────────────────────────────────

    def _capture_photo(self):
        dial = tk.Toplevel(self)
        dial.title("Foto del Socio")
        dial.configure(bg=BG)
        dial.resizable(False, False)
        dial.transient(self)

        def _elige(fn):
            dial.destroy()
            self.after(50, lambda: (self.lift(), self.focus_force()))
            fn()

        tk.Label(dial, text="¿Cómo querés cargar la foto?",
                 bg=BG, font=FN, fg=FG).pack(pady=(15, 10))
        btn_frame = tk.Frame(dial, bg=BG)
        btn_frame.pack()
        tk.Button(btn_frame, text="Desde archivo", bg=BTN_SAVE, fg="#FFF",
                  font=FN_B, relief="flat",
                  command=lambda: _elige(self._seleccionar_foto_archivo),
                  ).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cámara", bg="#888", fg="#FFF",
                  font=FN_B, relief="flat",
                  command=lambda: _elige(self._capturar_foto_camara),
                  ).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Quitar foto", bg="#A33", fg="#FFF",
                  font=FN_B, relief="flat",
                  command=lambda: _elige(self._quitar_foto),
                  ).pack(side="left", padx=5)

        dial.update_idletasks()
        w = dial.winfo_reqwidth()
        h = dial.winfo_reqheight()
        sw = dial.winfo_screenwidth()
        sh = dial.winfo_screenheight()
        dial.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        dial.grab_set()
        dial.wait_window()

    def _seleccionar_foto_archivo(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Seleccionar foto",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp"),
                       ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        self._aplicar_foto_desde_archivo(path)

    def _capturar_foto_camara(self):
        if pygame is None:
            messagebox.showwarning(
                "Cámara", "No hay soporte de cámara instalado (pygame).\n"
                          "Usá la opción 'Desde archivo'.",
                parent=self,
            )
            return

        try:
            import pygame.camera
        except Exception as e:
            messagebox.showwarning(
                "Cámara", f"No hay soporte de cámara instalado.\n({e})",
                parent=self,
            )
            return

        cap = self._abrir_camara_pygame()
        if cap is None:
            messagebox.showwarning(
                "Cámara",
                "No se pudo abrir la cámara.\n\n"
                f"{self._cam_error}\n\n"
                "Verificá que haya una cámara conectada y que ninguna otra "
                "aplicación la esté usando.\nTambién podés usar 'Desde archivo'.",
                parent=self,
            )
            return

        try:
            self._ventana_camara(cap)
        finally:
            try:
                cap.stop()
            except Exception:
                pass

    # ── Cámara con pygame (SDL2 / Media Foundation, sin OpenCV) ──────────

    def _abrir_camara_pygame(self):
        """Abre la primera webcam disponible con el backend nativo del SO.

        Windows: Media Foundation ('_camera (msmf)')
        Linux:   Video4Linux2 ('_camera (v4l2)')
        Otros:   backend por defecto de pygame.
        """
        import platform as _platform

        self._cam_error = ""
        try:
            sys_name = _platform.system().lower()

            # Lista de backends a probar según el SO.
            if sys_name == "windows":
                backends = ["_camera (msmf)", None]
            elif sys_name == "linux":
                backends = ["_camera (v4l2)", None]
            else:
                backends = [None]

            backend = None
            for cand in backends:
                try:
                    import pygame.camera
                    pygame.camera.quit()
                    pygame.camera.init(cand)
                    # Forzar el nombre del backend para listar cámaras.
                    pygame.camera.list_cameras()
                    backend = cand
                    break
                except Exception as e:
                    self._cam_error = f"Backend {cand}: {e}"
                    continue
            if backend is None:
                return None

            import pygame.camera as pcam
            cams = pcam.list_cameras()
            if not cams:
                self._cam_error = "No se detectó ninguna cámara."
                return None
            cam = pcam.Camera(cams[0], (640, 480))
            cam.start()
            return cam
        except Exception as e:
            self._cam_error = str(e)
            return None

    def _ventana_camara(self, cap):
        """Preview en vivo con botón Capturar. Devuelve la foto o None."""
        import tempfile

        win = tk.Toplevel(self)
        win.title("Capturar Foto")
        win.resizable(False, False)
        win.configure(bg="#000")
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", lambda: self._cerrar_camara(win, state))

        lbl = tk.Label(win, bg="#000")
        lbl.pack(padx=4, pady=(4, 0))
        bar = tk.Frame(win, bg="#000")
        bar.pack(pady=5)
        btn = tk.Button(bar, text="Capturar", bg=BTN_SAVE, fg="#FFF", font=FN_B,
                        relief="flat", cursor="hand2")
        btn.pack(side="left", padx=5)
        tk.Button(bar, text="Cancelar", bg="#888", fg="#FFF", font=FN_B,
                  relief="flat", cursor="hand2",
                  command=lambda: self._cerrar_camara(win, state)
                  ).pack(side="left", padx=5)

        state = {"vivo": True}

        def _capturar():
            try:
                surf = cap.get_image()
            except Exception:
                return
            if surf is None:
                return
            state["vivo"] = False
            win.destroy()
            raw = pygame.image.tostring(surf, "RGB")
            img = Image.frombytes("RGB", surf.get_size(), raw)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                img.save(tmp_path)
                self._aplicar_foto_desde_archivo(tmp_path)
            finally:
                if os.path.isfile(tmp_path):
                    os.remove(tmp_path)

        btn.configure(command=_capturar)

        def _update():
            if not state["vivo"] or not win.winfo_exists():
                return
            try:
                if cap.query_image():
                    surf = cap.get_image()
                    if surf is not None:
                        raw = pygame.image.tostring(surf, "RGB")
                        frame = Image.frombytes("RGB", surf.get_size(), raw)
                        w, h = frame.size
                        target = 320
                        scale = target / max(w, h)
                        if scale < 1.0:
                            frame = frame.resize(
                                (int(w * scale), int(h * scale)),
                                Image.Resampling.LANCZOS)
                        else:
                            frame = frame.resize(
                                (min(w, 380), min(h, 380)),
                                Image.Resampling.LANCZOS)
                        tkimg = ImageTk.PhotoImage(frame)
                        lbl.configure(image=tkimg)
                        lbl.image = tkimg
                        win.update_idletasks()
                        if not state.get("centrada"):
                            state["centrada"] = True
                            ww = win.winfo_reqwidth()
                            wh = win.winfo_reqheight()
                            sw = win.winfo_screenwidth()
                            sh = win.winfo_screenheight()
                            win.geometry(f"+{(sw - ww) // 2}+{(sh - wh) // 2}")
            except Exception:
                pass
            win.after(40, _update)

        _update()
        win.grab_set()

    def _cerrar_camara(self, win, state):
        state["vivo"] = False
        try:
            win.destroy()
        except Exception:
            pass
        self.after(50, lambda: (self.lift(), self.focus_force()))

    def _aplicar_foto_desde_archivo(self, path):
        """Estandariza y aplica la foto tomada por la cámara o desde archivo."""
        doc = self.entry_doc.get().strip()
        path_rel = socios_foto.estandarizar_y_guardar(path, doc)
        if path_rel is None:
            messagebox.showerror(
                "Error", "No se pudo procesar la foto capturada.\n"
                         "Verificá que el Documento sea numérico.",
                parent=self,
            )
            return
        self._foto_rel = path_rel
        self._foto_doc = doc
        self._foto_origen = socios_foto.foto_abs_path(path_rel)
        self._aplicar_foto(path_rel)

    def _quitar_foto(self):
        self._foto_rel = ""
        self._foto_doc = None
        self.lbl_foto.configure(text="👤")

    def _aplicar_foto(self, path_rel):
        if not path_rel:
            self.lbl_foto.configure(text="👤")
            return
        photo = socios_foto.cargar_para_tk(path_rel, 125)
        if photo is None:
            self.lbl_foto.configure(text="👤")
            return
        self.lbl_foto.configure(image=photo, text="")
        self.lbl_foto.image = photo

    # ── Save ──────────────────────────────────────────────────────────────

    def _on_save(self):
        doc = self.entry_doc.get().strip()
        apellido = self.entry_apellido.get().strip()
        nombre = self.entry_nombre.get().strip()

        if not doc:
            messagebox.showwarning("Guardar", "El campo Documento es obligatorio.", parent=self)
            self.entry_doc.focus_set()
            return
        if not apellido:
            messagebox.showwarning("Guardar", "El campo Apellidos es obligatorio.", parent=self)
            self.entry_apellido.focus_set()
            return
        if not nombre:
            messagebox.showwarning("Guardar", "El campo Nombres es obligatorio.", parent=self)
            self.entry_nombre.focus_set()
            return

        # Get selected plan
        plan_idx = self.combo_plan.current()
        id_plan = self._plans[plan_idx][0] if plan_idx >= 0 else ""

        # Parse fecha nacimiento
        fnac_db = ""
        edad = ""
        if self.dt_fnac is not None:
            fnac_date = self.dt_fnac.get_date()
            if isinstance(fnac_date, datetime.date):
                fnac_db = fnac_date.strftime("%Y-%m-%d")
                today = datetime.date.today()
                edad = str(today.year - fnac_date.year -
                          ((today.month, today.day) < (fnac_date.month, fnac_date.day)))
        else:
            fnac_raw = self.entry_fnac.get().strip()
            if fnac_raw:
                try:
                    parts = fnac_raw.split("/")
                    fnac_date = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                    fnac_db = fnac_date.strftime("%Y-%m-%d")
                    today = datetime.date.today()
                    edad = str(today.year - fnac_date.year -
                              ((today.month, today.day) < (fnac_date.month, fnac_date.day)))
                except (ValueError, IndexError):
                    messagebox.showwarning("Guardar", "Fecha de nacimiento inválida.", parent=self)
                    return

        # Parse fecha alta
        alta_db = ""
        if self.dt_alta is not None:
            alta_date = self.dt_alta.get_date()
            if isinstance(alta_date, datetime.date):
                alta_db = alta_date.strftime("%Y-%m-%d")
        else:
            alta_raw = self.fecha_alta_var.get().strip()
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

        # Foto: estandarizar/guardar con el documento actual del form
        if socios_foto.digito_carpeta(doc) is None:
            data["pathImage"] = ""
        elif self._foto_rel and self._foto_doc == doc:
            # Documento no cambió: la foto ya está guardada con este nombre.
            data["pathImage"] = self._foto_rel
        elif self._foto_origen:
            # Documento cambió (o foto re-cierta): re-estandarizar desde la
            # fuente original una sola vez, con el documento final.
            path_rel = socios_foto.estandarizar_y_guardar(self._foto_origen, doc)
            data["pathImage"] = path_rel or ""
            if path_rel:
                self._foto_rel = path_rel
                self._foto_doc = doc
        else:
            data["pathImage"] = ""

        try:
            id_socio = _save_socio(data, self.socio_id)
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}", parent=self)
            return

        if self.socio_id:
            messagebox.showinfo(
                "Éxito",
                f"Socio actualizado exitosamente.\n\n"
                f"ID: {id_socio}\n"
                f"Nombre: {apellido}, {nombre}", parent=self)
        else:
            messagebox.showinfo(
                "Éxito",
                f"Socio registrado exitosamente.\n\n"
                f"ID: {id_socio}\n"
                f"Documento: {doc}\n"
                f"Nombre: {apellido}, {nombre}", parent=self)
        self.destroy()


def open_window(parent=None, socio_id=None):
    return RegistrarSocioWindow(parent, socio_id=socio_id)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
