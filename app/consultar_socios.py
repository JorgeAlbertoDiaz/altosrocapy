"""Consultar Socios — perfil completo del socio.

Se abre desde:
  - Dashboard (vacío, usuario busca primero)
  - Acceso Socios (precarga el socio actual)
"""

import datetime
import math
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 1000, 610
PAD = 10

BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#333333"
FG_HEADER = "#003366"
FG_GREEN = "#008000"
FG_RED = "#FF0000"
FG_ORANGE = "#FF6600"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
PHOTO_BG = "#FFFFFF"
PHOTO_FG = "#AAAAAA"
GRID_HDR = "#D0D0D0"
SEL_BG = "#0078D7"

_MONTHS_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


# ── Helpers ───────────────────────────────────────────────────────────────

def _parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _fmt(raw):
    d = _parse_date(raw)
    return d.strftime("%d/%m/%Y") if d else ""


def _fmt_datetime(raw):
    if not raw:
        return ""
    try:
        dt = datetime.datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y - %H:%M")
    except (ValueError, TypeError):
        return _fmt(raw)


def _today_es():
    t = datetime.date.today()
    return f"{t.day:02d}/{t.month:02d}/{t.year}"


def _safe_float(val, default=0.0):
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0):
    try:
        return int(float(val or 0))
    except (ValueError, TypeError):
        return default


def _draw_silhouette(canvas, w, h):
    """Draw a white person silhouette on dark background."""
    canvas.delete("all")
    cx, cy = w // 2, h // 2
    r_head = min(w, h) // 8
    canvas.create_oval(
        cx - r_head, cy - h // 3 - r_head,
        cx + r_head, cy - h // 3 + r_head,
        fill=PHOTO_FG, outline="",
    )
    body_top = cy - h // 3 + r_head + 2
    body_bot = cy + h // 3
    body_w = r_head * 2.2
    canvas.create_polygon(
        cx - body_w, body_bot,
        cx - r_head, body_top,
        cx + r_head, body_top,
        cx + body_w, body_bot,
        fill=PHOTO_FG, outline="",
    )


# ── Data access ───────────────────────────────────────────────────────────

def _search_socios(query):
    """Search by DNI, Apellido, or Nombre. Returns list of dicts."""
    q = query.strip()
    if not q:
        return []
    conn = db.get_connection()
    try:
        like = f"%{q}%"
        rows = conn.execute(
            "SELECT idSocio, Apellidos, Nombres, Documento, id_Plan "
            "FROM tbSocios "
            "WHERE Documento != '---------' AND ("
            "  Documento LIKE ? OR Apellidos LIKE ? OR Nombres LIKE ? "
            "  OR (Apellidos || ' ' || Nombres LIKE ?)"
            ") ORDER BY Apellidos, Nombres LIMIT 50",
            (like, like, like, like),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _load_socio_full(id_socio):
    """Load complete socio profile. Returns dict or None."""
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tbSocios WHERE idSocio = ?", (id_socio,)
        ).fetchone()
        if row is None:
            return None
        socio = dict(row)

        # Plan
        plan = conn.execute(
            "SELECT Nomenclatura, Descripcion FROM tbPlan WHERE idPlan = ?",
            (socio["id_Plan"],),
        ).fetchone()
        socio["_plan_nomenclatura"] = plan["Nomenclatura"] if plan else ""
        socio["_plan_descripcion"] = plan["Descripcion"] if plan else ""

        # Latest payment info
        pago = conn.execute(
            "SELECT * FROM tbPagos WHERE idSocio = ? "
            "AND (Eliminado IS NULL OR Eliminado != '1') "
            "ORDER BY FechadePago DESC LIMIT 1",
            (id_socio,),
        ).fetchone()
        socio["_ultimo_pago"] = dict(pago) if pago else {}

        # Vencimiento (maxFechaVencimineto)
        venc = conn.execute(
            "SELECT MAX(FechaVencimineto) AS v FROM tbPagos "
            "WHERE idSocio = ? AND (Eliminado IS NULL OR Eliminado != '1')",
            (id_socio,),
        ).fetchone()
        socio["_vencimiento"] = venc["v"] if venc else None

        # Total paid
        total = conn.execute(
            "SELECT SUM(Importe) AS total FROM tbPagos "
            "WHERE idSocio = ? AND (Eliminado IS NULL OR Eliminado != '1')",
            (id_socio,),
        ).fetchone()
        socio["_pago_total"] = total["total"] if total else 0

        # Current saldo
        saldo = conn.execute(
            "SELECT Saldo FROM tbPagos WHERE idSocio = ? "
            "AND (Eliminado IS NULL OR Eliminado != '1') "
            "ORDER BY FechadePago DESC LIMIT 1",
            (id_socio,),
        ).fetchone()
        socio["_saldo"] = saldo["Saldo"] if saldo else "0"

        # Unpaid debts
        deudas = conn.execute(
            "SELECT SUM(ImporteDeuda) AS total FROM tb_RegistroDeudas "
            "WHERE idSocio = ? AND (Cancelada IS NULL OR Cancelada != '1') "
            "AND (Eliminado IS NULL OR Eliminado != '1')",
            (id_socio,),
        ).fetchone()
        socio["_deudas_total"] = deudas["total"] if deudas and deudas["total"] else 0

        # Access history
        accesos = conn.execute(
            "SELECT FechaAcceso, Estado, EstadoSaldo, EstadoAcceso "
            "FROM tbSociosAcceso WHERE idSocio = ? "
            "ORDER BY FechaAcceso DESC LIMIT 50",
            (id_socio,),
        ).fetchall()
        socio["_accesos"] = [dict(a) for a in accesos]

        return socio
    finally:
        conn.close()


def _register_pago(conn, id_socio, id_plan, importe):
    """Register a monthly payment (cuota)."""
    hoy = datetime.date.today()
    venc = hoy + datetime.timedelta(days=30)
    row = conn.execute("SELECT MAX(CAST(idPago AS INTEGER)) AS m FROM tbPagos").fetchone()
    max_id = int(row["m"] or 0) if row and row["m"] else 0
    new_id = str(max_id + 1)
    conn.execute(
        "INSERT INTO tbPagos "
        "(idPago, idSocio, FechadePago, FechaVencimineto, Importe, Saldo, "
        " EsRenovacion, Descuento, Observaciones, idTipoPago) "
        "VALUES (?, ?, ?, ?, ?, 0, '1', 0, '', '1')",
        (new_id, id_socio, hoy.strftime("%Y-%m-%d"), venc.strftime("%Y-%m-%d"), importe),
    )
    conn.commit()


def _register_acceso(conn, id_socio, id_plan):
    """Register a manual access."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
    # Determine states
    # Estado = vencimiento vigente? (1=yes, 0=no)
    venc = conn.execute(
        "SELECT MAX(FechaVencimineto) AS v FROM tbPagos "
        "WHERE idSocio = ? AND (Eliminado IS NULL OR Eliminado != '1')",
        (id_socio,),
    ).fetchone()
    vigente = 0
    if venc and venc["v"]:
        vd = _parse_date(venc["v"])
        if vd and vd >= datetime.date.today():
            vigente = 1

    # EstadoSaldo = saldo pendiente? (1=ok, 0=debt)
    saldo_row = conn.execute(
        "SELECT Saldo FROM tbPagos WHERE idSocio = ? "
        "AND (Eliminado IS NULL OR Eliminado != '1') "
        "ORDER BY FechadePago DESC LIMIT 1",
        (id_socio,),
    ).fetchone()
    saldo_ok = 1
    if saldo_row:
        try:
            if float(saldo_row["Saldo"] or 0) > 0:
                saldo_ok = 0
        except (ValueError, TypeError):
            pass

    # EstadoAcceso = 1 if manual (from this module)
    # Generate next idIngreso
    row = conn.execute(
        "SELECT MAX(CAST(idIngreso AS INTEGER)) AS m FROM tbSociosAcceso "
        "WHERE idIngreso GLOB '[0-9]*'"
    ).fetchone()
    max_ing = int(row["m"] or 0) if row and row["m"] else 0
    new_ing = str(max_ing + 1)

    conn.execute(
        "INSERT INTO tbSociosAcceso "
        "(idIngreso, idSocio, idPlan, FechaAcceso, Estado, EstadoSaldo, EstadoAcceso) "
        "VALUES (?, ?, ?, ?, ?, ?, 0)",
        (new_ing, id_socio, id_plan, now, str(vigente), str(saldo_ok)),
    )
    conn.commit()


# ── Window ────────────────────────────────────────────────────────────────

class ConsultarSociosWindow(tk.Toplevel):
    def __init__(self, parent=None, socio_id=None):
        """socio_id: if provided, preload that socio immediately."""
        super().__init__(parent)
        self.title("Consultar Socios")
        self.geometry(f"{W}x{H}")
        self.minsize(950, 520)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self.current_socio = None

        self._build()

        if socio_id:
            self._load_and_show(socio_id)

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build(self):
        # === SEARCH BAR ===
        frm = tk.Frame(self, bg=BG, height=42)
        frm.pack(fill="x", padx=PAD, pady=(8, 4))
        frm.pack_propagate(False)

        self.search_var = tk.StringVar()
        self.entry_search = tk.Entry(
            frm, textvariable=self.search_var,
            bg="#FFF", fg=FG, font=("Helvetica", 11),
            relief="solid", bd=1,
            highlightthickness=1, highlightbackground="#888",
        )
        self.entry_search.place(x=0, y=3, width=520, height=32)
        self.entry_search.bind("<Return>", lambda _: self._do_search())

        btn_search = tk.Button(
            frm, text="\U0001F50D", font=("Helvetica", 14),
            bg=BTN_BLUE, fg="#FFF", relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._do_search,
        )
        btn_search.place(x=528, y=3, width=40, height=32)

        # === LEFT COLUMN (60%) ===
        left = tk.Frame(self, bg=BG)
        left.place(x=PAD, y=52, width=590, height=H - 52 - 48)
        left.grid_columnconfigure(0, weight=1)

        # --- Panel SOCIO ---
        frm_socio = tk.LabelFrame(
            left, text=" SOCIO ", bg=BG,
            font=("Helvetica", 9, "bold"), relief="groove", bd=1,
            labelanchor="nw",
        )
        frm_socio.place(x=0, y=0, width=588, height=310)

        # Photo (top right of SOCIO panel)
        self.photo_canvas = tk.Canvas(
            frm_socio, bg="#000", width=125, height=125,
            highlightthickness=1, highlightbackground="#888",
        )
        self.photo_canvas.place(x=455, y=10)
        _draw_silhouette(self.photo_canvas, 125, 125)

        # Info labels (left side of SOCIO panel)
        self.lbls = {}
        fields = [
            ("Apellidos y Nombres", "nombre"),
            ("Documento", "documento"),
            ("Fecha Nacimiento", "nacimiento"),
            ("Domicilio", "domicilio"),
            ("Provincia", "provincia"),
            ("Email", "email"),
            ("Obra Social", "obra_social"),
            ("Teléfono", "telefono"),
            ("Peso", "peso"),
            ("Altura", "altura"),
            ("IMC", "imc"),
            ("Ocupación", "ocupacion"),
            ("Alergias", "alergias"),
            ("Medicación", "medicacion"),
            ("Información importante", "info_medica"),
        ]

        y = 12
        for label_text, key in fields:
            tk.Label(
                frm_socio, text=f"{label_text}:", bg=BG,
                font=("Helvetica", 8, "bold"), fg=FG_LABEL, anchor="w",
            ).place(x=10, y=y, width=130, height=17)
            lbl = tk.Label(
                frm_socio, text="", bg=BG,
                font=("Helvetica", 8), fg=FG, anchor="w",
            )
            lbl.place(x=145, y=y, width=300, height=17)
            self.lbls[key] = lbl
            y += 19

        # --- Panel INFORMACION ---
        frm_info = tk.LabelFrame(
            left, text=" INFORMACION ", bg=BG,
            font=("Helvetica", 9, "bold"), relief="groove", bd=1,
            labelanchor="nw",
        )
        frm_info.place(x=0, y=316, width=588, height=186)

        self.lbls_info = {}
        info_fields = [
            ("Socio desde", "socio_desde"),
            ("Último pago", "ultimo_pago"),
            ("Vencimiento", "vencimiento"),
            ("Pago total", "pago_total"),
            ("Saldo", "saldo"),
            ("Tipo plan", "tipo_plan"),
        ]

        y = 14
        for label_text, key in info_fields:
            tk.Label(
                frm_info, text=f"{label_text}:", bg=BG,
                font=("Helvetica", 8, "bold"), fg=FG_LABEL, anchor="w",
            ).place(x=10, y=y, width=110, height=17)
            lbl = tk.Label(
                frm_info, text="", bg=BG,
                font=("Helvetica", 8), fg=FG, anchor="w",
            )
            lbl.place(x=125, y=y, width=200, height=17)
            self.lbls_info[key] = lbl
            y += 19

        # PAGAR button
        self.btn_pagar = tk.Button(
            frm_info, text="Pagar", bg=BTN_BLUE, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_pagar,
        )
        self.btn_pagar.place(x=10, y=130, width=100, height=32)

        # === RIGHT COLUMN (40%) ===
        right = tk.Frame(self, bg=BG)
        right.place(x=610, y=52, width=W - 610 - PAD, height=H - 52 - 48)

        # --- Panel INGRESOS ---
        # NOTE: a manual Canvas instead of ttk.Treeview — Treeview cannot
        # paint individual cells nor multiline headings, and Tk renders
        # emoji monochrome, so colored dots need real drawing primitives.
        frm_ing = tk.LabelFrame(
            right, text=" INGRESOS ", bg=BG,
            font=("Helvetica", 9, "bold"), relief="groove", bd=1,
            labelanchor="nw",
        )
        frm_ing.place(x=0, y=0, relwidth=1.0, height=380)

        DOT_GREEN = "#00A651"
        DOT_RED = "#E53935"
        DOT_ORANGE = "#FB8C00"
        DOT_YELLOW = "#F5C400"

        hdr = tk.Frame(frm_ing, bg=GRID_HDR)
        hdr.place(x=4, y=4, width=372, height=32)
        headers = [
            ("Fecha de Acceso", 10, "w"),
            ("Estado\nVencimiento", 205, "center"),
            ("Estado\nSaldo", 283, "center"),
            ("Estado\nAcceso", 352, "center"),
        ]
        for text, x, anchor in headers:
            tk.Label(
                hdr, text=text, bg=GRID_HDR, fg=FG_HEADER,
                font=("Helvetica", 7, "bold"), justify="center",
            ).place(x=x, y=2, anchor="n" if anchor == "center" else "nw")

        self.canvas_ing = tk.Canvas(
            frm_ing, bg="#FFF",
            highlightthickness=1, highlightbackground="#888",
        )
        vsb = ttk.Scrollbar(frm_ing, orient="vertical",
                            command=self.canvas_ing.yview)
        self.canvas_ing.configure(yscrollcommand=vsb.set)
        self.canvas_ing.place(x=4, y=38, width=372, height=334)
        vsb.place(x=376, y=38, height=334)
        self.canvas_ing.bind(
            "<MouseWheel>",
            lambda e: self.canvas_ing.yview_scroll(-e.delta // 120, "units"))

        self._dot_colors = {
            "green": DOT_GREEN, "red": DOT_RED,
            "orange": DOT_ORANGE, "yellow": DOT_YELLOW,
        }
        self._ingresos_rows = []

        # REGISTRAR INGRESO button
        self.btn_ingreso = tk.Button(
            right, text="Registrar Ingreso", bg=BTN_BLUE, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_registrar_ingreso,
        )
        self.btn_ingreso.place(x=0, y=388, width=160, height=28)

        # === BOTTOM BAR ===
        tk.Button(
            self, text="Salir", width=10, height=1,
            command=self.destroy,
        ).place(x=W - PAD - 90, y=H - 42, width=90, height=32)

    # ── Search ────────────────────────────────────────────────────────────

    def _do_search(self):
        query = self.search_var.get().strip()
        if not query:
            return

        results = _search_socios(query)
        if not results:
            messagebox.showinfo("Búsqueda", "No se encontraron socios.", parent=self)
            return

        if len(results) == 1:
            self._load_and_show(results[0]["idSocio"])
            return

        # Multiple results — show selection dialog
        self._show_picker(results)

    def _show_picker(self, results):
        """Show a popup to pick from multiple search results."""
        picker = tk.Toplevel(self)
        picker.title("Seleccionar Socio")
        picker.geometry("500x400")
        picker.configure(bg=BG)
        picker.transient(self)
        picker.grab_set()
        picker.bind("<Escape>", lambda _: picker.destroy())

        tk.Label(
            picker, text="Seleccione un socio:", bg=BG,
            font=("Helvetica", 10, "bold"), fg=FG,
        ).pack(padx=10, pady=(10, 5), anchor="w")

        cols = ("id", "apellido", "nombre", "doc")
        tree = ttk.Treeview(
            picker, columns=cols, show="headings", selectmode="browse",
        )
        tree.heading("id", text="ID")
        tree.heading("apellido", text="Apellido")
        tree.heading("nombre", text="Nombre")
        tree.heading("doc", text="Documento")
        tree.column("id", width=50, anchor="center")
        tree.column("apellido", width=150)
        tree.column("nombre", width=150)
        tree.column("doc", width=100, anchor="center")

        for r in results:
            tree.insert("", "end", values=(
                r["idSocio"], r["Apellidos"] or "", r["Nombres"] or "",
                r["Documento"] or "",
            ))

        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def _select():
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            picker.destroy()
            self._load_and_show(str(vals[0]))
            self.after(50, lambda: (self.lift(), self.focus_force()))

        tk.Button(
            picker, text="Seleccionar", bg=BTN_BLUE, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_BLUE_ACTIVE,
            command=_select,
        ).pack(pady=8)

        tree.bind("<Double-Button-1>", lambda _: _select())

    # ── Load socio ────────────────────────────────────────────────────────

    def _load_and_show(self, id_socio):
        socio = _load_socio_full(id_socio)
        if socio is None:
            messagebox.showinfo("Error", "Socio no encontrado.", parent=self)
            return
        self.current_socio = socio
        self._populate(socio)

    def _populate(self, s):
        """Fill all panels with socio data."""
        nombre = f"{(s.get('Apellidos') or '').upper()}, {(s.get('Nombres') or '').upper()}"

        self.lbls["nombre"].configure(text=nombre)
        self.lbls["documento"].configure(text=s.get("Documento", ""))
        self.lbls["nacimiento"].configure(text=_fmt(s.get("FecNac")))
        self.lbls["domicilio"].configure(text=s.get("Domicilio") or "S/D")
        self.lbls["provincia"].configure(text=s.get("Provincia") or "S/D")
        self.lbls["email"].configure(text=s.get("Email") or "S/D")
        self.lbls["obra_social"].configure(text=s.get("ObraSocial") or "")
        self.lbls["telefono"].configure(text=s.get("Telefono") or "")

        peso = _safe_float(s.get("Peso"))
        altura = _safe_float(s.get("Altura"))
        self.lbls["peso"].configure(text=f"{peso:.0f} Kg" if peso else "")
        self.lbls["altura"].configure(text=f"{altura:.2f}" if altura else "")

        # IMC = peso / altura^2
        if peso > 0 and altura > 0:
            imc = peso / (altura ** 2)
            color = FG_GREEN if 18.5 <= imc <= 24.9 else (
                FG_RED if imc > 30 or imc < 16 else FG_ORANGE
            )
            self.lbls["imc"].configure(text=f"{imc:.1f}", fg=color)
        else:
            self.lbls["imc"].configure(text="", fg=FG)

        self.lbls["ocupacion"].configure(text=s.get("Ocupacion") or "")
        self.lbls["alergias"].configure(text=s.get("AlergicoA") or "")
        self.lbls["medicacion"].configure(text=s.get("Medicacion") or "")
        self.lbls["info_medica"].configure(text=s.get("InformacionMedica") or "")

        # Photo
        _draw_silhouette(self.photo_canvas, 125, 125)
        path = s.get("pathImage", "")
        if path and os.path.isfile(path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(path).resize((125, 125))
                self._photo_tk = ImageTk.PhotoImage(img)
                self.photo_canvas.delete("all")
                self.photo_canvas.create_image(0, 0, anchor="nw", image=self._photo_tk)
            except Exception:
                pass

        # Information panel
        self.lbls_info["socio_desde"].configure(text=_fmt(s.get("FechaAlta")))

        pago = s.get("_ultimo_pago", {})
        self.lbls_info["ultimo_pago"].configure(text=_fmt(pago.get("FechadePago")))

        venc_raw = s.get("_vencimiento")
        venc_text = _fmt(venc_raw) if venc_raw else ""
        venc_date = _parse_date(venc_raw) if venc_raw else None
        venc_color = FG
        if venc_date:
            if venc_date < datetime.date.today():
                venc_color = FG_RED
            else:
                venc_color = FG_GREEN
        self.lbls_info["vencimiento"].configure(text=venc_text, fg=venc_color)

        total_pagado = _safe_float(s.get("_pago_total"))
        self.lbls_info["pago_total"].configure(text=f"${total_pagado:,.0f}")

        saldo_val = _safe_float(s.get("_saldo"))
        deudas_val = _safe_float(s.get("_deudas_total"))
        saldo_total = saldo_val + deudas_val
        saldo_color = FG_GREEN if saldo_total == 0 else FG_RED
        self.lbls_info["saldo"].configure(
            text=f"${saldo_total:,.0f}" if saldo_total else "$0",
            fg=saldo_color,
        )

        plan_nom = s.get("_plan_nomenclatura", "")
        plan_desc = s.get("_plan_descripcion", "")
        self.lbls_info["tipo_plan"].configure(
            text=f"{plan_nom} - {plan_desc}" if plan_nom else ""
        )

        # Access history grid — one colored dot per state column:
        #   vencimiento: verde vigente / rojo vencido
        #   saldo:       verde sin deuda / naranja con deuda
        #   acceso:      amarillo si no registra acceso, verde si registra
        self._ingresos_rows = []
        for acc in s.get("_accesos", []):
            fecha = _fmt_datetime(acc.get("FechaAcceso"))

            est_venc = str(acc.get("Estado")) == "1"
            c_venc = "green" if est_venc else "red"

            saldo_ok = str(acc.get("EstadoSaldo")) == "1"
            c_saldo = "green" if saldo_ok else "orange"

            registra = str(acc.get("EstadoAcceso")) in ("0", "1")
            c_acc = "green" if registra else "yellow"

            self._ingresos_rows.append((fecha, c_venc, c_saldo, c_acc))
        self._render_ingresos()

    def _render_ingresos(self):
        """Draw the ingresos rows (fecha + colored dots) on the canvas."""
        c = self.canvas_ing
        c.delete("all")
        step = 26
        dot_x = {"venc": 205, "saldo": 283, "acc": 352}
        for i, (fecha, cv, cs, ca) in enumerate(self._ingresos_rows):
            y = i * step + step // 2 + 6
            c.create_text(
                10, y, anchor="w", text=fecha, font=("Helvetica", 8), fill=FG,
            )
            for x, color_key in (
                (dot_x["venc"], cv), (dot_x["saldo"], cs), (dot_x["acc"], ca),
            ):
                color = self._dot_colors[color_key]
                c.create_oval(x - 7, y - 7, x + 7, y + 7,
                              fill=color, outline="")
        total_h = max(len(self._ingresos_rows) * step + 12, 1)
        c.configure(scrollregion=(0, 0, 372, total_h))

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_pagar(self):
        """Open Registrar Cobros for current socio."""
        if not self.current_socio:
            messagebox.showinfo("Pagar", "No hay socio seleccionado.", parent=self)
            return

        s = self.current_socio
        try:
            from app import registrar_cobros
        except ImportError:
            import registrar_cobros
        win = registrar_cobros.open_window(self, socio_id=s["idSocio"])
        self.wait_window(win)
        if self.current_socio:
            self._load_and_show(self.current_socio["idSocio"])

    def _on_registrar_ingreso(self):
        """Register manual access."""
        if not self.current_socio:
            messagebox.showinfo("Registrar Ingreso", "No hay socio seleccionado.", parent=self)
            return

        s = self.current_socio
        nombre = f"{(s.get('Apellidos') or '').upper()}, {(s.get('Nombres') or '').upper()}"

        if not messagebox.askyesno(
            "Confirmar Ingreso",
            f"Registrar acceso manual para:\n{nombre}\n\n¿Continuar?",
            parent=self,
        ):
            return

        try:
            conn = db.get_connection()
            _register_acceso(conn, s["idSocio"], s["id_Plan"])
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar ingreso: {e}", parent=self)
            return
        finally:
            conn.close()

        # Reload
        self._load_and_show(s["idSocio"])
        messagebox.showinfo("Ingreso", "Acceso registrado exitosamente.", parent=self)


def open_window(parent=None, socio_id=None):
    return ConsultarSociosWindow(parent, socio_id=socio_id)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
