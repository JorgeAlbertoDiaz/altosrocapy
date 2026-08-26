"""Consultar Estados Socios: panel administrativo de vencimientos/saldos/planes."""

import datetime
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Spanish day/month names (avoid locale encoding issues) ─────────────────
_DAYS_ES = {
    0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
    4: "viernes", 5: "sábado", 6: "domingo",
}
_MONTHS_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

WINDOW_WIDTH = 950
WINDOW_HEIGHT = 620

BG = "#E8E8E8"
FG_GREEN = "#008000"
FG_RED = "#FF0000"
FG_ORANGE = "#FF6600"
FG_DARKRED = "#8B0000"
SELECTION_BG = "#0078D7"

GRID_PAD_X = 10  # horizontal padding for all rows

# Name truncation limit (legacy system: 16 chars without comma)
NAME_MAX_CHARS = 16


def _parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _format_date_ddmmyyyy(raw):
    d = _parse_date(raw)
    return d.strftime("%d/%m/%Y") if d else ""


def _today_es():
    today = datetime.date.today()
    return f"{_DAYS_ES[today.weekday()]}, {today.day} de {_MONTHS_ES[today.month]} de {today.year}"


def _truncate_name(apellidos, nombres):
    """Truncate name to 16 chars (legacy style), keeping full surname."""
    ap = (apellidos or "").strip()
    no = (nombres or "").strip()
    full = f"{ap}, {no}"
    if len(full) > NAME_MAX_CHARS:
        # Keep surname + comma + truncate first name
        available = NAME_MAX_CHARS - len(ap) - 2  # 2 for ", "
        if available > 0:
            return f"{ap}, {no[:available]}"
        else:
            return ap[:NAME_MAX_CHARS]
    return full


def _get_latest_payments_map(conn):
    """Latest payment per socio in ONE query."""
    rows = conn.execute(
        """
        SELECT p.idSocio, p.FechaVencimineto, p.FechadePago, p.Importe, p.Saldo
        FROM tbPagos p
        JOIN (
            SELECT idSocio, MAX(FechadePago) AS max_fp
            FROM tbPagos
            WHERE Eliminado IS NULL OR Eliminado != '1'
            GROUP BY idSocio
        ) latest ON p.idSocio = latest.idSocio AND p.FechadePago = latest.max_fp
        """
    ).fetchall()
    return {r["idSocio"]: dict(r) for r in rows}


def _get_plan_names_map(conn):
    """idPlan -> Descripcion (full name)."""
    rows = conn.execute(
        "SELECT idPlan, Descripcion FROM tbPlan"
    ).fetchall()
    return {r["idPlan"]: r["Descripcion"] for r in rows}


def _get_plan_descriptions(conn):
    """Return list of Descripcion values for the combo box."""
    rows = conn.execute(
        "SELECT Descripcion FROM tbPlan WHERE idPlan != '------' ORDER BY Descripcion"
    ).fetchall()
    return [r["Descripcion"] for r in rows]


def _get_plan_id_by_desc(conn, desc):
    """Return idPlan for a given Descripcion."""
    row = conn.execute(
        "SELECT idPlan FROM tbPlan WHERE Descripcion = ?", (desc,)
    ).fetchone()
    return row["idPlan"] if row else None


def _has_unpaid_deudas(conn, id_socio):
    """Check if socio has any uncancelled debts."""
    row = conn.execute(
        "SELECT 1 FROM tb_RegistroDeudas "
        "WHERE idSocio = ? AND (Cancelada IS NULL OR Cancelada != '1') "
        "AND (Eliminado IS NULL OR Eliminado != '1') LIMIT 1",
        (id_socio,),
    ).fetchone()
    return row is not None


def populate_grid(tree, status_label, filter_mode, plan_desc=None, date=None):
    """Query DB and fill treeview. Returns row count."""
    tree.delete(*tree.get_children())
    conn = db.get_connection()
    try:
        hoy = datetime.date.today()
        hoy_str = hoy.strftime("%Y-%m-%d")
        hace90 = hoy - datetime.timedelta(days=90)
        hace90_str = hace90.strftime("%Y-%m-%d")

        # Base query: all valid socios
        base_sql = """
            SELECT s.idSocio, s.Apellidos, s.Nombres, s.Documento,
                   s.NroInscripcion, s.Estado, s.id_Plan, s.FechaBaja
            FROM tbSocios s
            WHERE s.Documento != '---------' AND (
                (s.Documento LIKE '%0%') OR (s.Documento LIKE '%1%')
                OR (s.Documento LIKE '%2%') OR (s.Documento LIKE '%3%')
                OR (s.Documento LIKE '%4%') OR (s.Documento LIKE '%5%')
                OR (s.Documento LIKE '%6%') OR (s.Documento LIKE '%7%')
                OR (s.Documento LIKE '%8%') OR (s.Documento LIKE '%9%')
            )
        """
        params = []

        # Filter by plan if needed
        if filter_mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN") and plan_desc:
            plan_id = _get_plan_id_by_desc(conn, plan_desc)
            if plan_id:
                base_sql += " AND s.id_Plan = ?"
                params.append(plan_id)

        socios = conn.execute(base_sql, params).fetchall()
        pagos = _get_latest_payments_map(conn)
        planes = _get_plan_names_map(conn)
        count = 0

        for s in socios:
            sid = s["idSocio"]
            pago = pagos.get(sid)
            if pago is None:
                continue

            # Determine vencimiento date
            venc_date = _parse_date(pago.get("FechaVencimineto"))
            venc_vigente = venc_date is not None and venc_date >= hoy

            # Check for uncancelled debts
            tiene_deudas = _has_unpaid_deudas(conn, sid)

            # Determine status based on business rules:
            # ACTIVOS: cuota no vencida + sin deudas
            # ACTIVOS C/SALDO: cuota no vencida + saldo pendiente o deudas
            # INACTIVOS: cuota vencida
            socio_activo = venc_vigente and not tiene_deudas
            socio_con_saldo = False
            if venc_vigente and not socio_activo:
                socio_con_saldo = True
            if venc_vigente and socio_activo:
                try:
                    saldo_val = float(pago.get("Saldo") or 0)
                except (ValueError, TypeError):
                    saldo_val = 0
                if saldo_val > 0:
                    socio_con_saldo = True

            # Apply filter
            if filter_mode == "ACTIVOS":
                if not socio_activo:
                    continue
            elif filter_mode == "INACTIVOS":
                if venc_vigente:
                    continue
                # Últimos 90 días: only show if FechaBaja is recent
                if s["FechaBaja"]:
                    fb = _parse_date(s["FechaBaja"])
                    if fb and fb < hace90:
                        continue
            elif filter_mode == "ACTIVOS_C_SALDO":
                if not venc_vigente or socio_activo:
                    continue
            elif filter_mode == "ACTIVOS_POR_PLAN":
                if not socio_activo:
                    continue
            elif filter_mode == "INACTIVOS_POR_PLAN":
                if venc_vigente:
                    continue
            elif filter_mode == "POR_DIA" and date:
                pago_date = _parse_date(pago.get("FechadePago"))
                sel_date = _parse_date(date)
                if pago_date != sel_date:
                    continue

            nombre = _truncate_name(s["Apellidos"], s["Nombres"])
            venc = _format_date_ddmmyyyy(pago.get("FechaVencimineto"))
            fpago = _format_date_ddmmyyyy(pago.get("FechadePago"))
            importe = str(pago.get("Importe") or "0")
            saldo = str(pago.get("Saldo") or "0")
            plan_name = planes.get(s["id_Plan"], "")
            estado_icon = "\u2705" if (socio_activo or socio_con_saldo) else ""

            # Determine row tag color
            if socio_con_saldo:
                row_tag = "orange"
            elif socio_activo:
                row_tag = "green"
            else:
                row_tag = ""

            tags = (row_tag,) if row_tag else ()

            tree.insert(
                "", "end",
                values=(sid, nombre, s["Documento"], s["NroInscripcion"],
                        venc, fpago, importe, saldo, plan_name, estado_icon),
                tags=tags,
            )
            count += 1

        status_label.configure(text=f"Socios: {count}")
        return count
    finally:
        conn.close()


class ConsultarEstadosSociosWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Consultar Estados de Socios")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(950, 620)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _e: self.destroy())

        self.filter_var = tk.StringVar(value="ACTIVOS")
        self.plan_var = tk.StringVar(value="")

        self._build_ui()
        self.populate_grid()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # row 2 = treeview, expands

        # ── Row 0: Search entry ────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=BG)
        search_frame.grid(row=0, column=0, sticky="ew",
                          padx=GRID_PAD_X, pady=(8, 4))

        self.entry_search = tk.Entry(
            search_frame, bg="#FFFFFF", fg="#000000",
            font=("Helvetica", 10),
            relief="solid", bd=1,
            highlightthickness=1, highlightbackground="#999999",
        )
        self.entry_search.pack(fill="x", ipady=3)

        # ── Row 1: Filters panel ──────────────────────────────────────────
        filters_frame = tk.LabelFrame(
            self, text=" Filtros ", bg=BG,
            font=("Helvetica", 9, "bold"),
            relief="groove", bd=1,
            labelanchor="nw",
        )
        filters_frame.grid(row=1, column=0, sticky="ew",
                           padx=GRID_PAD_X, pady=(0, 4))

        # Row 1 of filters
        self.radio_activos = tk.Radiobutton(
            filters_frame, text="ACTIVOS", variable=self.filter_var,
            value="ACTIVOS", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter_change,
        )
        self.radio_activos.grid(row=0, column=0, padx=(10, 8), pady=(6, 0), sticky="w")

        self.radio_inactivos = tk.Radiobutton(
            filters_frame, text="INACTIVOS", variable=self.filter_var,
            value="INACTIVOS", bg=BG, fg=FG_RED,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter_change,
        )
        self.radio_inactivos.grid(row=0, column=1, padx=8, pady=(6, 0), sticky="w")
        tk.Label(
            filters_frame, text="(Últimos 90 días)",
            bg=BG, fg=FG_DARKRED, font=("Helvetica", 7),
        ).grid(row=1, column=1, padx=(25, 0), sticky="w")

        self.radio_csaldo = tk.Radiobutton(
            filters_frame, text="ACTIVOS C/SALDO", variable=self.filter_var,
            value="ACTIVOS_C_SALDO", bg=BG, fg=FG_ORANGE,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_ORANGE,
            command=self._on_filter_change,
        )
        self.radio_csaldo.grid(row=0, column=2, padx=8, pady=(6, 0), sticky="w")

        self.radio_pordia = tk.Radiobutton(
            filters_frame, text="POR DÍA", variable=self.filter_var,
            value="POR_DIA", bg=BG, fg="#000000",
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG,
            command=self._on_filter_change,
        )
        self.radio_pordia.grid(row=0, column=3, padx=8, pady=(6, 0), sticky="w")

        self.entry_date = tk.Entry(
            filters_frame, bg="#FFFFFF", fg="#000000",
            font=("Helvetica", 9),
            relief="solid", bd=1,
            state="readonly", readonlybackground="#FFFFFF",
        )
        self.entry_date.grid(row=0, column=4, padx=(4, 10), pady=(6, 0), sticky="w")
        self.entry_date.configure(state="normal")
        self.entry_date.insert(0, _today_es())
        self.entry_date.configure(state="readonly")

        # Row 2 of filters
        self.radio_aplan = tk.Radiobutton(
            filters_frame, text="ACTIVOS POR PLAN", variable=self.filter_var,
            value="ACTIVOS_POR_PLAN", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter_change,
        )
        self.radio_aplan.grid(row=2, column=0, padx=(10, 8), pady=(4, 6), sticky="w")

        self.combo_plan = ttk.Combobox(
            filters_frame, textvariable=self.plan_var,
            width=18, state="readonly",
        )
        self.combo_plan.grid(row=2, column=1, padx=4, pady=(4, 6), sticky="w")
        self.combo_plan.bind("<<ComboboxSelected>>", lambda _e: self._on_filter_change())

        self.radio_iplan = tk.Radiobutton(
            filters_frame, text="INACTIVOS POR PLAN", variable=self.filter_var,
            value="INACTIVOS_POR_PLAN", bg=BG, fg=FG_RED,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter_change,
        )
        self.radio_iplan.grid(row=2, column=2, padx=8, pady=(4, 6), sticky="w")
        tk.Label(
            filters_frame, text="(Últimos 90 días)",
            bg=BG, fg=FG_DARKRED, font=("Helvetica", 7),
        ).grid(row=3, column=2, padx=(25, 0), sticky="w")

        self._load_plans()

        # ── Row 2: Treeview (EXPANDS) ─────────────────────────────────────
        tree_container = tk.Frame(self, bg=BG)
        tree_container.grid(row=2, column=0, sticky="nsew",
                            padx=GRID_PAD_X, pady=(0, 0))
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        self._build_treeview(tree_container)

        # ── Row 3: Bottom bar ─────────────────────────────────────────────
        bar = tk.Frame(self, bg=BG, height=45)
        bar.grid(row=3, column=0, sticky="ew", padx=GRID_PAD_X, pady=(0, 5))
        bar.grid_propagate(False)

        tk.Button(
            bar, text="Exportar a Excel", width=14, height=1,
            command=lambda: messagebox.showinfo("Exportar", "Próximamente"),
        ).place(x=10, y=7)

        tk.Button(
            bar, text="Exportar a PDF", width=14, height=1,
            command=lambda: messagebox.showinfo("Exportar", "Próximamente"),
        ).place(x=160, y=7)

        self.lbl_count = tk.Label(
            bar, text="Socios: 0", bg=BG,
            font=("Helvetica", 10, "bold"), fg="#000000",
        )
        self.lbl_count.place(x=650, y=10)

        tk.Button(
            bar, text="Salir", width=10, height=1,
            command=self.destroy,
        ).place(x=860, y=7)

    def _load_plans(self):
        conn = db.get_connection()
        try:
            plans = _get_plan_descriptions(conn)
        finally:
            conn.close()
        self.combo_plan["values"] = plans
        if plans:
            self.combo_plan.current(0)

    def _build_treeview(self, parent):
        columns = (
            "idSocio", "Nombre Completo", "Documento", "Nro",
            "Vencimiento", "FechaPago", "Importe", "Saldo", "Plan", "Estado",
        )
        # Tight widths to fit 10 columns in ~920px without horizontal scroll
        widths = (50, 175, 95, 50, 90, 90, 70, 60, 130, 50)

        style = ttk.Style(self)
        style.configure("Grid.Treeview",
                        background="#FFFFFF", foreground="#000000",
                        rowheight=22, fieldbackground="#FFFFFF",
                        font=("Helvetica", 9, "bold"))
        style.configure("Grid.Treeview.Heading",
                        background=BG, font=("Helvetica", 8, "bold"))
        style.map("Treeview",
                  background=[("selected", SELECTION_BG)],
                  foreground=[("selected", "#FFFFFF")])

        self.tree = ttk.Treeview(
            parent, columns=columns, show="headings",
            style="Grid.Treeview", selectmode="browse",
        )

        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col, font=("Helvetica", 8, "bold"))
            anchor = "center" if col in ("idSocio", "Nro", "Importe", "Saldo", "Estado") else "w"
            self.tree.column(col, width=w, minwidth=w, anchor=anchor)

        self.tree.tag_configure("green", foreground=FG_GREEN)
        self.tree.tag_configure("orange", foreground=FG_ORANGE)

        scrollbar_y = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

    # ── Logic ─────────────────────────────────────────────────────────────

    def _on_filter_change(self):
        self.populate_grid()

    def populate_grid(self):
        mode = self.filter_var.get()
        plan = self.plan_var.get() if mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN") else None
        date = None
        if mode == "POR_DIA":
            raw = self.entry_date.get()
            try:
                date = datetime.datetime.strptime(raw, "%A, %d de %B de %Y").date().strftime("%Y-%m-%d")
            except ValueError:
                date = None
        populate_grid(self.tree, self.lbl_count, mode, plan_desc=plan, date=date)


def open_window(parent=None):
    """Open the Consultar Estados Socios window."""
    return ConsultarEstadosSociosWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
