"""Registrar Cobros — cobro de cuotas, renovación y vencimiento.

Ventana de caja/recepción para cobrar cuotas mensuales.
NO administra deudas ni saldos manuales.
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

W, H = 1250, 600
PAD = 8

BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#333333"
FG_HEADER = "#003366"
FG_GREEN = "#008000"
FG_RED = "#FF0000"
FG_ORANGE = "#FF8C00"
FG_WARN = "#CC6600"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
BTN_GREEN = "#3B8A3B"
BTN_GREEN_ACTIVE = "#2D6B2D"
SEARCH_BG = "#3B6FA0"
SEARCH_FG = "#FFFFFF"
SEL_BG = "#0078D7"

# idTipoPago mapping
TIPOS_PAGO = ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "MERCADO PAGO"]
TIPO_ID_MAP = {"EFECTIVO": "1", "TRANSFERENCIA": "2", "TARJETA": "3", "MERCADO PAGO": "4"}
TIPO_ID_REV = {v: k for k, v in TIPO_ID_MAP.items()}


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
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return _fmt(raw)


def _safe_float(val, default=0.0):
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return default


def _add_months(d, months):
    """Add months to a date, clamping to end of month."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def _calc_new_vencimiento(venc_actual_date, hoy):
    """Calculate new vencimiento based on business rules.

    Case 1: Expired/new → hoy + 1 month - 1 day
    Case 2: Still valid → venc_actual + 1 month - 1 day
    """
    if venc_actual_date and venc_actual_date >= hoy:
        base = venc_actual_date  # Case 2: extend from current vencimiento
    else:
        base = hoy  # Case 1: start from today
    new_venc = _add_months(base, 1) - datetime.timedelta(days=1)
    return new_venc


# ── Data access ───────────────────────────────────────────────────────────

def _search_socios(query):
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


def _load_cobro_data(id_socio):
    """Load all data needed for the cobros screen."""
    conn = db.get_connection()
    try:
        s = conn.execute(
            "SELECT * FROM tbSocios WHERE idSocio = ?", (id_socio,)
        ).fetchone()
        if s is None:
            return None
        socio = dict(s)

        # Plan
        plan = conn.execute(
            "SELECT Nomenclatura, Descripcion, PrecioVigente "
            "FROM tbPlan WHERE idPlan = ?",
            (socio["id_Plan"],),
        ).fetchone()
        socio["_plan_nom"] = plan["Nomenclatura"] if plan else ""
        socio["_plan_desc"] = plan["Descripcion"] if plan else ""
        socio["_plan_precio"] = _safe_float(plan["PrecioVigente"]) if plan else 0

        # Latest payment (for vencimiento and last pago info)
        pago = conn.execute(
            "SELECT * FROM tbPagos WHERE idSocio = ? "
            "AND (Eliminado IS NULL OR Eliminado != '1') "
            "ORDER BY FechadePago DESC LIMIT 1",
            (id_socio,),
        ).fetchone()
        socio["_ultimo_pago"] = dict(pago) if pago else {}

        # Current vencimiento
        venc = conn.execute(
            "SELECT MAX(FechaVencimineto) AS v FROM tbPagos "
            "WHERE idSocio = ? AND (Eliminado IS NULL OR Eliminado != '1')",
            (id_socio,),
        ).fetchone()
        socio["_vencimiento"] = venc["v"] if venc else None

        # Pending debts (warning only)
        deudas = conn.execute(
            "SELECT SUM(ImporteDeuda) AS total FROM tb_RegistroDeudas "
            "WHERE idSocio = ? AND (Cancelada IS NULL OR Cancelada != '1') "
            "AND (Eliminado IS NULL OR Eliminado != '1')",
            (id_socio,),
        ).fetchone()
        socio["_deudas"] = _safe_float(deudas["total"]) if deudas and deudas["total"] else 0

        # Payment history
        pagos = conn.execute(
            "SELECT p.*, s.Apellidos, s.Nombres, s.Documento "
            "FROM tbPagos p "
            "JOIN tbSocios s ON s.idSocio = p.idSocio "
            "WHERE p.idSocio = ? AND (p.Eliminado IS NULL OR p.Eliminado != '1') "
            "ORDER BY p.FechadePago DESC LIMIT 50",
            (id_socio,),
        ).fetchall()
        socio["_historial"] = [dict(p) for p in pagos]

        return socio
    finally:
        conn.close()


def _register_cobro(conn, id_socio, id_plan, fecha_pago, venc_nuevo,
                     importe, descuento, motivo_desc, tipo_pago,
                     interes, observaciones):
    """Register a payment (cuota)."""
    conn.execute(
        "INSERT INTO tbPagos "
        "(idSocio, FechadePago, FechaVencimineto, Importe, Saldo, "
        " Descuento, MotivoDescuento, EsRenovacion, Observaciones, "
        " UsuarioCobrador, idTipoPago) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, '1', ?, '', ?)",
        (id_socio,
         fecha_pago.strftime("%Y-%m-%d"),
         venc_nuevo.strftime("%Y-%m-%d"),
         f"{importe:.2f}",
         f"{descuento:.2f}",
         motivo_desc or "",
         observaciones or "",
         TIPO_ID_MAP.get(tipo_pago, "1")),
    )
    conn.commit()


def _anular_ultimo_cobro(conn, id_socio, usuario=""):
    """Soft-delete the latest payment for a socio."""
    row = conn.execute(
        "SELECT idPago FROM tbPagos WHERE idSocio = ? "
        "AND (Eliminado IS NULL OR Eliminado != '1') "
        "ORDER BY FechadePago DESC LIMIT 1",
        (id_socio,),
    ).fetchone()
    if not row:
        return False
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
    conn.execute(
        "UPDATE tbPagos SET Eliminado = '1', EliminadoPor = ?, "
        "FechaEliminacion = ? WHERE idPago = ?",
        (usuario, ahora, row["idPago"]),
    )
    conn.commit()
    return True


# ── Modal: Cambio de Vencimiento ──────────────────────────────────────────

class CambioVencimientoDialog(tk.Toplevel):
    def __init__(self, parent, socio_nombre, venc_actual_date):
        super().__init__(parent)
        self.title("Cambio de Vencimiento")
        self.geometry("390x240")
        self.resizable(False, False)
        self.configure(bg="#3B6FA0")
        self.transient(parent)
        self.grab_set()
        self.result = None  # new date or None

        self.venc_actual = venc_actual_date
        hoy = datetime.date.today()

        # Title bar
        tk.Label(
            self, text="Cambio de Vencimiento", bg="#3B6FA0", fg="#FFF",
            font=("Helvetica", 12, "bold"),
        ).pack(fill="x", pady=(8, 4), padx=10, anchor="w")

        # Panel
        panel = tk.Frame(self, bg=BG, relief="groove", bd=1)
        panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Socio
        tk.Label(panel, text="Socio:", bg=BG, font=("Helvetica", 9, "bold"),
                 fg=FG_LABEL).place(x=10, y=12)
        tk.Label(panel, text=socio_nombre, bg=BG, font=("Helvetica", 10, "bold"),
                 fg=FG).place(x=100, y=12)

        # Vencimiento actual
        tk.Label(panel, text="Vencimiento Actual:", bg=BG,
                 font=("Helvetica", 9, "bold"), fg=FG_LABEL).place(x=10, y=42)
        venc_text = venc_actual_date.strftime("%d/%m/%Y") if venc_actual_date else "Sin vencimiento"
        tk.Label(panel, text=venc_text, bg=BG, font=("Helvetica", 10),
                 fg=FG).place(x=140, y=42)

        # Nuevo vencimiento — date entry
        tk.Label(panel, text="Nuevo Vencimiento:", bg=BG,
                 font=("Helvetica", 9, "bold"), fg=FG_LABEL).place(x=10, y=78)

        self.date_var = tk.StringVar(value=hoy.strftime("%d/%m/%Y"))
        self.entry_date = tk.Entry(
            panel, textvariable=self.date_var,
            bg="#FFF", fg=FG, font=("Helvetica", 11),
            relief="solid", bd=1, width=15,
        )
        self.entry_date.place(x=140, y=76)

        # Hint
        tk.Label(panel, text="(formato: dd/mm/aaaa)", bg=BG,
                 font=("Helvetica", 7), fg="#888").place(x=250, y=80)

        # Minimum date hint
        if venc_actual_date:
            tk.Label(panel, text=f"Mínimo: {venc_actual_date.strftime('%d/%m/%Y')}",
                     bg=BG, font=("Helvetica", 7), fg="#888").place(x=140, y=100)

        # Buttons
        tk.Button(
            panel, text="Aceptar", bg=BTN_GREEN, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_GREEN_ACTIVE,
            command=self._accept,
        ).place(x=100, y=140, width=90, height=30)

        tk.Button(
            panel, text="Cancelar", bg=BTN_GREEN, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_GREEN_ACTIVE,
            command=self.destroy,
        ).place(x=210, y=140, width=90, height=30)

        self.bind("<Return>", lambda _: self._accept())
        self.bind("<Escape>", lambda _: self.destroy())

    def _accept(self):
        try:
            parts = self.date_var.get().split("/")
            new_date = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Fecha inválida. Use formato dd/mm/aaaa.",
                                 parent=self)
            return

        if self.venc_actual and new_date < self.venc_actual:
            messagebox.showerror(
                "Error",
                f"La fecha no puede ser anterior al vencimiento actual "
                f"({self.venc_actual.strftime('%d/%m/%Y')}).",
                parent=self,
            )
            return

        self.result = new_date
        self.destroy()


# ── Main Window ───────────────────────────────────────────────────────────

class RegistrarCobrosWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Registrar Cobros")
        self.geometry(f"{W}x{H}")
        self.minsize(1100, 560)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self.current_socio = None
        self.new_venc_override = None  # manual override from CambioVencimiento

        self._build()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # === SEARCH BAR ===
        frm_search = tk.Frame(self, bg=BG, height=40)
        frm_search.pack(fill="x", padx=PAD, pady=(6, 4))
        frm_search.pack_propagate(False)

        self.search_var = tk.StringVar()
        self.entry_search = tk.Entry(
            frm_search, textvariable=self.search_var,
            bg=SEARCH_BG, fg=SEARCH_FG,
            font=("Helvetica", 11, "bold"),
            relief="flat", bd=0,
            insertbackground=SEARCH_FG,
        )
        self.entry_search.place(x=0, y=3, width=540, height=30)
        self.entry_search.bind("<Return>", lambda _: self._do_search())

        tk.Button(
            frm_search, text="\U0001F50D", font=("Helvetica", 14),
            bg="#888", fg="#FFF", relief="flat",
            activebackground="#666", activeforeground="#FFF",
            cursor="hand2", command=self._do_search,
        ).place(x=548, y=3, width=40, height=30)

        # === LEFT PANEL (55%) — Historial de Cobros ===
        left_w = int(W * 0.55)
        frm_left = tk.LabelFrame(
            self, text=" Historial de Cobros ", bg=BG,
            font=("Helvetica", 9, "bold"), relief="groove", bd=1,
            labelanchor="nw",
        )
        frm_left.place(x=PAD, y=48, width=left_w - PAD, height=H - 48 - 42)

        cols = ("nombre", "documento", "fecha_cobro", "vencimiento",
                "importe", "saldo", "descuento", "motivo", "obs")
        self.tree = ttk.Treeview(
            frm_left, columns=cols, show="headings", selectmode="browse",
        )
        hdrs = ["Nombre Completo", "Documento", "Fecha Cobro", "Vencimiento",
                "Importe Cobrado", "Saldo", "Descuento", "Motivo Dto", "Observaciones"]
        widths = [160, 80, 95, 95, 90, 70, 70, 90, 120]
        for c, h, w in zip(cols, hdrs, widths):
            self.tree.heading(c, text=h, font=("Helvetica", 8, "bold"))
            self.tree.column(c, width=w, minwidth=30, anchor="w")

        style = ttk.Style(self)
        style.configure("C.Treeview", rowheight=20, font=("Helvetica", 8),
                        background="#FFF", fieldbackground="#FFF")
        style.configure("C.Treeview.Heading", font=("Helvetica", 8, "bold"))
        style.map("C.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="C.Treeview")

        vsb = ttk.Scrollbar(frm_left, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frm_left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.place(x=4, y=4, relwidth=0.97, relheight=0.96)
        vsb.place(relx=0.975, y=4, relheight=0.96)
        hsb.place(x=4, rely=0.97, relwidth=0.97)

        # === RIGHT PANEL ===
        right_x = left_w + 4
        right_w = W - left_w - PAD - 4
        frm_right = tk.Frame(self, bg=BG)
        frm_right.place(x=right_x, y=48, width=right_w, height=H - 48 - 42)

        # --- Socio Info (top right) ---
        frm_info = tk.LabelFrame(
            frm_right, text=" Información del Socio ", bg=BG,
            font=("Helvetica", 9, "bold"), relief="groove", bd=1,
            labelanchor="nw",
        )
        frm_info.place(x=0, y=0, relwidth=1.0, height=120)

        self.lbl_nombre = tk.Label(frm_info, text="", bg=BG,
                                    font=("Helvetica", 13, "bold"), fg=FG)
        self.lbl_nombre.place(x=10, y=6)

        self.lbl_dni = tk.Label(frm_info, text="", bg=BG,
                                 font=("Helvetica", 11, "bold"), fg=FG_LABEL)
        self.lbl_dni.place(x=10, y=32)

        self.lbl_plan = tk.Label(frm_info, text="", bg=BG,
                                  font=("Helvetica", 10), fg=FG_LABEL)
        self.lbl_plan.place(x=10, y=56)

        self.lbl_precio = tk.Label(frm_info, text="", bg=BG,
                                    font=("Helvetica", 10, "bold"), fg=FG_GREEN)
        self.lbl_precio.place(x=10, y=76)

        self.lbl_ultimo_pago = tk.Label(frm_info, text="", bg=BG,
                                         font=("Helvetica", 9), fg=FG_LABEL)
        self.lbl_ultimo_pago.place(x=10, y=96)

        # --- Deuda warning ---
        self.lbl_deuda = tk.Label(frm_info, text="", bg=BG,
                                   font=("Helvetica", 9, "bold"), fg=FG_WARN)
        self.lbl_deuda.place(x=300, y=56)

        # --- Datos del Cobro (bottom right) ---
        frm_cobro = tk.LabelFrame(
            frm_right, text=" Datos del Cobro ", bg=BG,
            font=("Helvetica", 9, "bold"), relief="groove", bd=1,
            labelanchor="nw",
        )
        frm_cobro.place(x=0, y=126, relwidth=1.0, relheight=1.0)

        y = 10
        lh = 22  # label height

        # Fecha de Cobro
        tk.Label(frm_cobro, text="Fecha de Cobro:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.fecha_var = tk.StringVar(value=datetime.date.today().strftime("%d/%m/%Y"))
        self.entry_fecha = tk.Entry(
            frm_cobro, textvariable=self.fecha_var,
            bg="#FFF", fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1, width=12,
        )
        self.entry_fecha.place(x=120, y=y, width=100, height=lh)
        self.entry_fecha.bind("<FocusOut>", lambda _: self._recalc())
        y += 26

        # Importe Total
        tk.Label(frm_cobro, text="Importe Total:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.lbl_importe = tk.Label(frm_cobro, text="$0", bg=BG,
                                     font=("Helvetica", 9, "bold"), fg=FG)
        self.lbl_importe.place(x=120, y=y)
        y += 22

        # Descuento
        tk.Label(frm_cobro, text="Descuento:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.desc_var = tk.StringVar(value="0")
        self.entry_desc = tk.Entry(
            frm_cobro, textvariable=self.desc_var,
            bg="#FFF", fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1, width=10,
        )
        self.entry_desc.place(x=120, y=y, width=80, height=lh)
        self.entry_desc.bind("<FocusOut>", lambda _: self._recalc())
        self.entry_desc.bind("<KeyRelease>", lambda _: self._recalc())
        y += 22

        # Motivo Descuento
        tk.Label(frm_cobro, text="Motivo Dto:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.motivo_var = tk.StringVar()
        self.entry_motivo = tk.Entry(
            frm_cobro, textvariable=self.motivo_var,
            bg="#FFF", fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_motivo.place(x=120, y=y, width=200, height=lh)
        y += 22

        # Importe Final
        tk.Label(frm_cobro, text="Importe Final:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.lbl_final = tk.Label(frm_cobro, text="$0", bg=BG,
                                   font=("Helvetica", 9, "bold"), fg=FG)
        self.lbl_final.place(x=120, y=y)
        y += 24

        # Tipo de Pago
        tk.Label(frm_cobro, text="Tipo de Pago:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.tipo_var = tk.StringVar(value="EFECTIVO")
        self.combo_tipo = ttk.Combobox(
            frm_cobro, textvariable=self.tipo_var,
            values=TIPOS_PAGO, state="readonly", width=18,
        )
        self.combo_tipo.place(x=120, y=y)
        y += 26

        # Interés
        tk.Label(frm_cobro, text="Interés ($):", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.interes_var = tk.StringVar(value="0")
        self.entry_interes = tk.Entry(
            frm_cobro, textvariable=self.interes_var,
            bg="#FFF", fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1, width=10,
        )
        self.entry_interes.place(x=120, y=y, width=80, height=lh)
        self.entry_interes.bind("<KeyRelease>", lambda _: self._recalc())
        y += 22

        # Entrega
        tk.Label(frm_cobro, text="Entrega:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.entrega_var = tk.StringVar(value="0")
        self.entry_entrega = tk.Entry(
            frm_cobro, textvariable=self.entrega_var,
            bg="#FFF", fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1, width=10,
        )
        self.entry_entrega.place(x=120, y=y, width=80, height=lh)
        self.entry_entrega.bind("<KeyRelease>", lambda _: self._recalc())
        y += 22

        # Saldo
        tk.Label(frm_cobro, text="Saldo:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.lbl_saldo = tk.Label(frm_cobro, text="$0", bg=BG,
                                   font=("Helvetica", 9, "bold"), fg=FG)
        self.lbl_saldo.place(x=120, y=y)
        y += 24

        # Observaciones
        tk.Label(frm_cobro, text="Observaciones:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).place(x=8, y=y)
        self.obs_var = tk.StringVar()
        self.entry_obs = tk.Entry(
            frm_cobro, textvariable=self.obs_var,
            bg="#FFF", fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1,
        )
        self.entry_obs.place(x=120, y=y, width=200, height=lh)
        y += 28

        # --- Vencimientos ---
        frm_venc = tk.Frame(frm_cobro, bg=BG)
        frm_venc.place(x=8, y=y, relwidth=1.0, height=60)

        tk.Label(frm_venc, text="Vencimiento Actual:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).grid(row=0, column=0, sticky="w")
        self.lbl_venc_actual = tk.Label(frm_venc, text="", bg=BG,
                                         font=("Helvetica", 9), fg=FG)
        self.lbl_venc_actual.grid(row=0, column=1, sticky="w", padx=(5, 0))

        tk.Label(frm_venc, text="Vencimiento Nuevo:", bg=BG,
                 font=("Helvetica", 8, "bold"), fg=FG_LABEL).grid(row=1, column=0, sticky="w")
        self.lbl_venc_nuevo = tk.Label(frm_venc, text="", bg=BG,
                                        font=("Helvetica", 9, "bold"), fg=FG_GREEN)
        self.lbl_venc_nuevo.grid(row=1, column=1, sticky="w", padx=(5, 0))

        self.btn_cambiar_venc = tk.Button(
            frm_venc, text="Cambiar\nVencimiento", bg=BTN_BLUE, fg="#FFF",
            font=("Helvetica", 7, "bold"), relief="flat",
            activebackground=BTN_BLUE_ACTIVE, cursor="hand2",
            command=self._open_cambio_venc, state="disabled",
        )
        self.btn_cambiar_venc.grid(row=0, column=2, rowspan=2, padx=(15, 0), sticky="ns")

        y += 64

        # === BOTTOM BAR ===
        bar = tk.Frame(self, bg=BG, height=38)
        bar.place(x=0, y=H - 40, relwidth=1.0, height=40)

        self.btn_cobrar = tk.Button(
            bar, text="COBRAR", bg=BTN_BLUE, fg="#FFF",
            font=("Helvetica", 11, "bold"), relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_cobrar,
        )
        self.btn_cobrar.place(x=W - 320, y=4, width=120, height=32)

        self.btn_anular = tk.Button(
            bar, text="ANULAR COBROS", bg=BTN_BLUE, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_anular,
        )
        self.btn_anular.place(x=W - 190, y=4, width=130, height=32)

        tk.Button(
            bar, text="Salir", width=8, command=self.destroy,
        ).place(x=PAD, y=4)

    # ── Search ────────────────────────────────────────────────────────────

    def _do_search(self):
        query = self.search_var.get().strip()
        if not query:
            return
        results = _search_socios(query)
        if not results:
            messagebox.showinfo("Búsqueda", "No se encontraron socios.")
            return
        if len(results) == 1:
            self._load_socio(results[0]["idSocio"])
            return
        self._show_picker(results)

    def _show_picker(self, results):
        picker = tk.Toplevel(self)
        picker.title("Seleccionar Socio")
        picker.geometry("500x400")
        picker.configure(bg=BG)
        picker.transient(self)
        picker.grab_set()
        picker.bind("<Escape>", lambda _: picker.destroy())

        tk.Label(picker, text="Seleccione un socio:", bg=BG,
                 font=("Helvetica", 10, "bold"), fg=FG).pack(padx=10, pady=(10, 5), anchor="w")

        cols = ("id", "apellido", "nombre", "doc")
        tree = ttk.Treeview(picker, columns=cols, show="headings", selectmode="browse")
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
                r["Documento"] or ""))
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def _select():
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            picker.destroy()
            self._load_socio(str(vals[0]))

        tk.Button(picker, text="Seleccionar", bg=BTN_BLUE, fg="#FFF",
                  font=("Helvetica", 9, "bold"), relief="flat",
                  command=_select).pack(pady=8)
        tree.bind("<Double-Button-1>", lambda _: _select())

    # ── Load socio ────────────────────────────────────────────────────────

    def _load_socio(self, id_socio):
        data = _load_cobro_data(id_socio)
        if data is None:
            messagebox.showinfo("Error", "Socio no encontrado.")
            return
        self.current_socio = data
        self.new_venc_override = None
        self._populate(data)
        self._recalc()

    def _populate(self, s):
        nombre = f"{(s.get('Apellidos') or '').upper()}, {(s.get('Nombres') or '').upper()}"
        self.lbl_nombre.configure(text=nombre)
        self.lbl_dni.configure(text=f"DNI: {s.get('Documento', '')}")
        self.lbl_plan.configure(text=f"PLAN: {s.get('_plan_nom', '')} - {s.get('_plan_desc', '')}")

        precio = s.get("_plan_precio", 0)
        self.lbl_precio.configure(text=f"VALOR DEL PLAN: ${precio:,.0f}")

        pago = s.get("_ultimo_pago", {})
        ultimo = _fmt(pago.get("FechadePago"))
        self.lbl_ultimo_pago.configure(
            text=f"Último Pago: {ultimo}" if ultimo else "Último Pago: (ninguno)")

        # Deuda warning
        deudas = s.get("_deudas", 0)
        if deudas > 0:
            self.lbl_deuda.configure(
                text=f"⚠ ATENCIÓN: Deuda pendiente: ${deudas:,.0f}",
                fg=FG_WARN)
        else:
            self.lbl_deuda.configure(text="")

        # Vencimiento actual
        venc_raw = s.get("_vencimiento")
        venc_date = _parse_date(venc_raw)
        venc_text = venc_date.strftime("%d/%m/%Y") if venc_date else "Sin vencimiento"
        self.lbl_venc_actual.configure(text=venc_text)

        # Calculate new vencimiento
        hoy = datetime.date.today()
        new_venc = _calc_new_vencimiento(venc_date, hoy)
        self.lbl_venc_nuevo.configure(text=new_venc.strftime("%d/%m/%Y"))

        self.btn_cambiar_venc.configure(state="normal")

        # Payment history
        self.tree.delete(*self.tree.get_children())
        for p in s.get("_historial", []):
            nom = f"{(p.get('Apellidos') or '').upper()}, {(p.get('Nombres') or '').upper()}"
            doc = p.get("Documento", "")
            fcobro = _fmt(p.get("FechadePago"))
            venc = _fmt(p.get("FechaVencimineto"))
            importe = _safe_float(p.get("Importe"))
            saldo = _safe_float(p.get("Saldo"))
            desc = _safe_float(p.get("Descuento"))
            motivo = p.get("MotivoDescuento", "")
            obs = p.get("Observaciones", "")

            self.tree.insert("", "end", values=(
                nom, doc, fcobro, venc,
                f"${importe:,.0f}", f"${saldo:,.0f}",
                f"${desc:,.0f}" if desc else "",
                motivo, obs,
            ))

    # ── Recalculate ───────────────────────────────────────────────────────

    def _recalc(self, *_):
        precio = 0
        if self.current_socio:
            precio = self.current_socio.get("_plan_precio", 0)

        descuento = _safe_float(self.desc_var.get())
        interes = _safe_float(self.interes_var.get())
        entrega = _safe_float(self.entrega_var.get())

        importe_final = max(precio - descuento + interes, 0)
        saldo = entrega - importe_final

        self.lbl_importe.configure(text=f"${precio:,.0f}")
        self.lbl_final.configure(text=f"${importe_final:,.0f}")

        saldo_color = FG_GREEN if saldo >= 0 else FG_RED
        self.lbl_saldo.configure(text=f"${saldo:,.0f}", fg=saldo_color)

        # Recalc new vencimiento
        venc_date = None
        if self.current_socio:
            venc_date = _parse_date(self.current_socio.get("_vencimiento"))

        # Parse payment date
        hoy = datetime.date.today()
        try:
            parts = self.fecha_var.get().split("/")
            fecha_pago = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            fecha_pago = hoy

        if self.new_venc_override:
            new_venc = self.new_venc_override
        else:
            new_venc = _calc_new_vencimiento(venc_date, fecha_pago)

        self.lbl_venc_nuevo.configure(text=new_venc.strftime("%d/%m/%Y"))

    # ── Cambio Vencimiento ────────────────────────────────────────────────

    def _open_cambio_venc(self):
        if not self.current_socio:
            return
        s = self.current_socio
        nombre = f"{(s.get('Apellidos') or '').upper()}, {(s.get('Nombres') or '').upper()}"
        venc_date = _parse_date(s.get("_vencimiento"))

        dlg = CambioVencimientoDialog(self, nombre, venc_date)
        self.wait_window(dlg)

        if dlg.result:
            self.new_venc_override = dlg.result
            self.lbl_venc_nuevo.configure(text=dlg.result.strftime("%d/%m/%Y"))

    # ── Cobrar ────────────────────────────────────────────────────────────

    def _on_cobrar(self):
        if not self.current_socio:
            messagebox.showinfo("Cobrar", "No hay socio seleccionado.")
            return

        s = self.current_socio

        # Validate descuento motivo
        descuento = _safe_float(self.desc_var.get())
        if descuento > 0 and not self.motivo_var.get().strip():
            messagebox.showwarning(
                "Descuento",
                "Si aplica descuento, debe indicar el motivo.")
            return

        # Parse fecha
        try:
            parts = self.fecha_var.get().split("/")
            fecha_pago = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Fecha de cobro inválida.")
            return

        # Calculate vencimiento
        venc_date = _parse_date(s.get("_vencimiento"))
        venc_nuevo = self.new_venc_override or _calc_new_vencimiento(venc_date, fecha_pago)

        precio = s.get("_plan_precio", 0)
        interes = _safe_float(self.interes_var.get())
        importe_final = max(precio - descuento + interes, 0)

        nombre = f"{(s.get('Apellidos') or '').upper()}, {(s.get('Nombres') or '').upper()}"
        motivo = self.motivo_var.get().strip()
        obs = self.obs_var.get().strip()
        tipo = self.tipo_var.get()

        # Confirm
        msg = (
            f"Socio: {nombre}\n"
            f"Plan: {s.get('_plan_nom', '')} - {s.get('_plan_desc', '')}\n"
            f"Fecha Cobro: {fecha_pago.strftime('%d/%m/%Y')}\n"
            f"Importe Plan: ${precio:,.0f}\n"
        )
        if descuento > 0:
            msg += f"Descuento: -${descuento:,.0f} ({motivo})\n"
        if interes > 0:
            msg += f"Interés: +${interes:,.0f}\n"
        msg += f"Importe Final: ${importe_final:,.0f}\n"
        msg += f"Tipo: {tipo}\n"
        msg += f"Nuevo Vencimiento: {venc_nuevo.strftime('%d/%m/%Y')}\n\n"
        msg += "¿Confirmar cobro?"

        if not messagebox.askyesno("Confirmar Cobro", msg):
            return

        try:
            conn = db.get_connection()
            _register_cobro(
                conn, s["idSocio"], s["id_Plan"],
                fecha_pago, venc_nuevo,
                importe_final, descuento, motivo,
                tipo, interes, obs,
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar cobro: {e}")
            return
        finally:
            conn.close()

        self._load_socio(s["idSocio"])
        messagebox.showinfo("Cobro", "Cobro registrado exitosamente.")

    # ── Anular ────────────────────────────────────────────────────────────

    def _on_anular(self):
        if not self.current_socio:
            return
        s = self.current_socio
        nombre = f"{(s.get('Apellidos') or '').upper()}, {(s.get('Nombres') or '').upper()}"

        if not messagebox.askyesno(
            "Anular Cobro",
            f"¿Anular el último cobro de {nombre}?\n\n"
            "Esta acción queda registrada en auditoría.",
        ):
            return

        try:
            conn = db.get_connection()
            ok = _anular_ultimo_cobro(conn, s["idSocio"])
        except Exception as e:
            messagebox.showerror("Error", f"Error al anular: {e}")
            return
        finally:
            conn.close()

        if ok:
            self._load_socio(s["idSocio"])
            messagebox.showinfo("Anular", "Cobro anulado exitosamente.")
        else:
            messagebox.showinfo("Anular", "No hay cobros para anular.")


def open_window(parent=None):
    return RegistrarCobrosWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
