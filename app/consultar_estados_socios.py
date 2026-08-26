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
_MONTH_NUM = {v: k for k, v in _MONTHS_ES.items()}
_DAY_NUM = {v: k for k, v in _DAYS_ES.items()}

WINDOW_WIDTH = 950
WINDOW_HEIGHT = 620

BG = "#E8E8E8"
FG = "#000000"
FG_GREEN = "#008000"
FG_RED = "#FF0000"
FG_ORANGE = "#FF6600"
FG_DARKRED = "#8B0000"
SELECTION_BG = "#0078D7"

GRID_PAD_X = 10

NAME_MAX_CHARS = 16

# ── Default plan for POR PLAN filter ──────────────────────────────────────
DEFAULT_PLAN_DESC = "MUSC APAR"


# ── Helper functions ──────────────────────────────────────────────────────

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


def _parse_date_es(text):
    """Parse 'miércoles, 26 de agosto de 2026' without locale dependency."""
    try:
        # Strip day-of-week: "miércoles, 26 de agosto de 2026" -> "26 de agosto de 2026"
        after_comma = text.split(", ", 1)[1] if ", " in text else text
        parts = after_comma.split()
        day = int(parts[0])
        month_name = parts[2]
        year = int(parts[4])
        month = _MONTH_NUM[month_name]
        return datetime.date(year, month, day)
    except (ValueError, KeyError, IndexError):
        return None


def _truncate_name(apellidos, nombres):
    ap = (apellidos or "").strip()
    no = (nombres or "").strip()
    full = f"{ap}, {no}"
    if len(full) > NAME_MAX_CHARS:
        available = NAME_MAX_CHARS - len(ap) - 2
        if available > 0:
            return f"{ap}, {no[:available]}"
        else:
            return ap[:NAME_MAX_CHARS]
    return full


def _get_latest_payments_map(conn):
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
    rows = conn.execute("SELECT idPlan, Descripcion FROM tbPlan").fetchall()
    return {r["idPlan"]: r["Descripcion"] for r in rows}


def _get_plan_descriptions(conn):
    rows = conn.execute(
        "SELECT Descripcion FROM tbPlan WHERE idPlan != '------' ORDER BY Descripcion"
    ).fetchall()
    return [r["Descripcion"] for r in rows]


def _get_plan_id_by_desc(conn, desc):
    row = conn.execute(
        "SELECT idPlan FROM tbPlan WHERE Descripcion = ?", (desc,)
    ).fetchone()
    return row["idPlan"] if row else None


def _has_unpaid_deudas(conn, id_socio):
    row = conn.execute(
        "SELECT 1 FROM tb_RegistroDeudas "
        "WHERE idSocio = ? AND (Cancelada IS NULL OR Cancelada != '1') "
        "AND (Eliminado IS NULL OR Eliminado != '1') LIMIT 1",
        (id_socio,),
    ).fetchone()
    return row is not None


def populate_grid(tree, status_label, filter_mode, plan_desc=None, date=None):
    tree.delete(*tree.get_children())
    conn = db.get_connection()
    try:
        hoy = datetime.date.today()
        hace90 = hoy - datetime.timedelta(days=90)

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

            venc_date = _parse_date(pago.get("FechaVencimineto"))
            venc_vigente = venc_date is not None and venc_date >= hoy
            tiene_deudas = _has_unpaid_deudas(conn, sid)

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
        self.plan_var = tk.StringVar(value=DEFAULT_PLAN_DESC)

        self._build_ui()
        self._update_widget_states()
        self.populate_grid()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Row 0: Search ──────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=BG)
        search_frame.place(x=GRID_PAD_X, y=8, width=WINDOW_WIDTH - 2 * GRID_PAD_X, height=30)

        self.entry_search = tk.Entry(
            search_frame, bg="#FFFFFF", fg=FG,
            font=("Helvetica", 10),
            relief="solid", bd=1,
            highlightthickness=1, highlightbackground="#999999",
        )
        self.entry_search.pack(fill="both", expand=True, ipady=3)

        # ── Row 1: Filters ─────────────────────────────────────────────────
        filters_frame = tk.LabelFrame(
            self, text=" Filtros ", bg=BG,
            font=("Helvetica", 9, "bold"),
            relief="groove", bd=1,
            labelanchor="nw",
        )
        filters_frame.place(x=GRID_PAD_X, y=46, width=WINDOW_WIDTH - 2 * GRID_PAD_X, height=72)

        # Row 0 of filters: radios + date entry
        self.radio_activos = tk.Radiobutton(
            filters_frame, text="ACTIVOS", variable=self.filter_var,
            value="ACTIVOS", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter_change,
        )
        self.radio_activos.place(x=10, y=4)

        self.radio_inactivos = tk.Radiobutton(
            filters_frame, text="INACTIVOS", variable=self.filter_var,
            value="INACTIVOS", bg=BG, fg=FG_RED,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter_change,
        )
        self.radio_inactivos.place(x=130, y=4)
        self.lbl_inactivos_hint = tk.Label(
            filters_frame, text="(Últimos 90 días)",
            bg=BG, fg=FG_DARKRED, font=("Helvetica", 7),
        )
        self.lbl_inactivos_hint.place(x=148, y=20)

        self.radio_csaldo = tk.Radiobutton(
            filters_frame, text="ACTIVOS C/SALDO", variable=self.filter_var,
            value="ACTIVOS_C_SALDO", bg=BG, fg=FG_ORANGE,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_ORANGE,
            command=self._on_filter_change,
        )
        self.radio_csaldo.place(x=290, y=4)

        self.radio_pordia = tk.Radiobutton(
            filters_frame, text="POR DÍA", variable=self.filter_var,
            value="POR_DIA", bg=BG, fg=FG,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG,
            command=self._on_filter_change,
        )
        self.radio_pordia.place(x=470, y=4)

        self.entry_date = tk.Entry(
            filters_frame, bg="#FFFFFF", fg=FG,
            font=("Helvetica", 9),
            relief="solid", bd=1,
            state="disabled",
        )
        self.entry_date.place(x=560, y=4, width=310, height=22)
        # Pre-fill the date value (hidden while disabled)
        self.entry_date.configure(state="normal")
        self.entry_date.delete(0, "end")
        self.entry_date.insert(0, _today_es())
        self.entry_date.configure(state="disabled")

        # Row 1 of filters: plan radios + combo
        self.radio_aplan = tk.Radiobutton(
            filters_frame, text="ACTIVOS POR PLAN", variable=self.filter_var,
            value="ACTIVOS_POR_PLAN", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter_change,
        )
        self.radio_aplan.place(x=10, y=38)

        self.combo_plan = ttk.Combobox(
            filters_frame, textvariable=self.plan_var,
            width=18, state="disabled",
        )
        self.combo_plan.place(x=190, y=40)
        self.combo_plan.bind("<<ComboboxSelected>>", lambda _e: self._on_filter_change())

        self.radio_iplan = tk.Radiobutton(
            filters_frame, text="INACTIVOS POR PLAN", variable=self.filter_var,
            value="INACTIVOS_POR_PLAN", bg=BG, fg=FG_RED,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter_change,
        )
        self.radio_iplan.place(x=400, y=38)
        self.lbl_iplan_hint = tk.Label(
            filters_frame, text="(Últimos 90 días)",
            bg=BG, fg=FG_DARKRED, font=("Helvetica", 7),
        )
        self.lbl_iplan_hint.place(x=418, y=54)

        self._load_plans()

        # ── Row 2: Treeview (FIXED position, expands to fill) ─────────────
        # Calculate positions: search(8..38) + filters(46..118) + bar(575..620)
        # Tree occupies: y=122, height = 620 - 122 - 45 - 8 = 445px
        tree_y = 124
        bar_height = 42
        tree_height = WINDOW_HEIGHT - tree_y - bar_height - 8

        tree_container = tk.Frame(self, bg=BG)
        tree_container.place(x=GRID_PAD_X, y=tree_y,
                             width=WINDOW_WIDTH - 2 * GRID_PAD_X,
                             height=tree_height)

        self._build_treeview(tree_container)

        # ── Row 3: Bottom bar ─────────────────────────────────────────────
        bar = tk.Frame(self, bg=BG, height=bar_height)
        bar.place(x=GRID_PAD_X, y=WINDOW_HEIGHT - bar_height - 4,
                  width=WINDOW_WIDTH - 2 * GRID_PAD_X, height=bar_height)
        bar.grid_propagate(False)

        tk.Button(
            bar, text="Exportar a Excel", width=14, height=1,
            command=lambda: messagebox.showinfo("Exportar", "Próximamente"),
        ).place(x=10, y=6)

        tk.Button(
            bar, text="Exportar a PDF", width=14, height=1,
            command=lambda: messagebox.showinfo("Exportar", "Próximamente"),
        ).place(x=160, y=6)

        self.lbl_count = tk.Label(
            bar, text="Socios: 0", bg=BG,
            font=("Helvetica", 10, "bold"), fg=FG,
        )
        self.lbl_count.place(x=650, y=8)

        tk.Button(
            bar, text="Salir", width=10, height=1,
            command=self.destroy,
        ).place(x=860, y=6)

    def _load_plans(self):
        conn = db.get_connection()
        try:
            plans = _get_plan_descriptions(conn)
        finally:
            conn.close()
        self.combo_plan["values"] = plans
        # Set default to MUSC APAR if available
        if DEFAULT_PLAN_DESC in plans:
            self.plan_var.set(DEFAULT_PLAN_DESC)
        elif plans:
            self.plan_var.set(plans[0])

    def _build_treeview(self, parent):
        columns = (
            "idSocio", "Nombre Completo", "Documento", "Nro",
            "Vencimiento", "FechaPago", "Importe", "Saldo", "Plan", "Estado",
        )
        # Widths calibrated for 920px total (950 - 2*15 padding)
        widths = (50, 180, 100, 50, 90, 90, 70, 60, 130, 50)

        style = ttk.Style(self)
        style.configure("Grid.Treeview",
                        background="#FFFFFF", foreground=FG,
                        rowheight=22, fieldbackground="#FFFFFF",
                        font=("Helvetica", 9, "bold"))
        style.configure("Grid.Treeview.Heading",
                        background=BG, font=("Helvetica", 8, "bold"))
        style.map("Grid.Treeview",
                  background=[("selected", SELECTION_BG)],
                  foreground=[("selected", "#FFFFFF")])

        self.tree = ttk.Treeview(
            parent, columns=columns, show="headings",
            style="Grid.Treeview", selectmode="browse",
        )

        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col, font=("Helvetica", 8, "bold"))
            anchor = "center" if col in ("idSocio", "Nro", "Importe", "Saldo", "Estado") else "w"
            self.tree.column(col, width=w, minwidth=30, anchor=anchor)

        self.tree.tag_configure("green", foreground=FG_GREEN)
        self.tree.tag_configure("orange", foreground=FG_ORANGE)

        scrollbar_y = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.place(x=0, y=0, relwidth=1, relheight=1)
        scrollbar_y.place(relx=1, y=0, relheight=1, anchor="ne")
        scrollbar_x.place(relx=0, rely=1, relwidth=1, anchor="sw")

    # ── Filter state management ────────────────────────────────────────────

    def _on_filter_change(self):
        self._update_widget_states()
        self.populate_grid()

    def _update_widget_states(self):
        """Enable/disable widgets based on selected filter."""
        mode = self.filter_var.get()

        # Combo: only active when POR_PLAN selected
        if mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN"):
            self.combo_plan.configure(state="readonly")
        else:
            self.combo_plan.configure(state="disabled")

        # Date entry: only active when POR_DIA selected
        if mode == "POR_DIA":
            self.entry_date.configure(state="normal")
            self.entry_date.configure(fg=FG)
        else:
            self.entry_date.configure(state="disabled")
            self.entry_date.configure(fg="#999999")

    def populate_grid(self):
        mode = self.filter_var.get()
        plan = self.plan_var.get() if mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN") else None
        date = None
        if mode == "POR_DIA":
            raw = self.entry_date.get()
            parsed = _parse_date_es(raw)
            if parsed:
                date = parsed.strftime("%Y-%m-%d")
        populate_grid(self.tree, self.lbl_count, mode, plan_desc=plan, date=date)


def open_window(parent=None):
    return ConsultarEstadosSociosWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
