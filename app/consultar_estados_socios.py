"""Consultar Estados Socios: panel administrativo de vencimientos/saldos/planes."""

import datetime
import locale
import sqlite3
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Locale for Spanish date names ──────────────────────────────────────────
_LOCALE_SET = False
for _loc in ("es_AR.UTF-8", "es_ES.UTF-8", "Spanish_Spain", "Spanish"):
    try:
        locale.setlocale(locale.LC_TIME, _loc)
        _LOCALE_SET = True
        break
    except locale.Error:
        continue

WINDOW_WIDTH = 950
WINDOW_HEIGHT = 620

BG = "#E8E8E8"
FG_GREEN = "#008000"
FG_RED = "#FF0000"
FG_ORANGE = "#FF6600"
FG_DARKRED = "#8B0000"
SELECTION_BG = "#0078D7"


def _has_digits(value: str) -> bool:
    return any(c.isdigit() for c in value)


def _parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _format_date_ddmmyyyy(raw):
    d = _parse_date(raw)
    if d is None:
        return ""
    return d.strftime("%d/%m/%Y")


def _today_es():
    today = datetime.date.today()
    try:
        day_name = today.strftime("%A")
        month_name = today.strftime("%B")
        return f"{day_name}, {today.day} de {month_name} de {today.year}"
    except Exception:
        return today.strftime("%Y-%m-%d")


def _get_latest_payments(conn, id_socio):
    """Return latest payment row dict for a socio (most recent FechadePago)."""
    row = conn.execute(
        "SELECT FechaVencimineto, FechadePago, Importe, Saldo "
        "FROM tbPagos WHERE idSocio = ? AND (Eliminado IS NULL OR Eliminado != '1') "
        "ORDER BY FechadePago DESC LIMIT 1",
        (id_socio,),
    ).fetchone()
    return dict(row) if row else None


def _get_latest_payments_map(conn):
    """Latest payment per socio in ONE query (avoids N+1 full scans)."""
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
    """idPlan -> Nomenclatura in one query."""
    rows = conn.execute(
        "SELECT idPlan, Nomenclatura FROM tbPlan"
    ).fetchall()
    return {r["idPlan"]: r["Nomenclatura"] for r in rows}


def _get_plan_name(conn, id_plan):
    if not id_plan:
        return ""
    row = conn.execute(
        "SELECT Nomenclatura FROM tbPlan WHERE idPlan = ?", (id_plan,)
    ).fetchone()
    return row["Nomenclatura"] if row else ""


def _get_plan_names(conn):
    rows = conn.execute(
        "SELECT Nomenclatura FROM tbPlan WHERE idPlan != '------' ORDER BY Nomenclatura"
    ).fetchall()
    return [r["Nomenclatura"] for r in rows]


def populate_grid(tree, status_label, filter_mode, plan=None, date=None):
    """Query DB and fill treeview. Returns row count."""
    tree.delete(*tree.get_children())
    conn = db.get_connection()
    try:
        hoy = datetime.date.today()
        hace90 = hoy - datetime.timedelta(days=90)
        hace90_str = hace90.strftime("%Y-%m-%d")

        # Build base: get socios with latest payment
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

        if filter_mode == "ACTIVOS":
            base_sql += " AND s.Estado = '1' AND (s.FechaBaja IS NULL OR s.FechaBaja = '')"
        elif filter_mode == "INACTIVOS":
            base_sql += " AND (s.Estado != '1' OR (s.FechaBaja IS NOT NULL AND s.FechaBaja != ''))"
            base_sql += " AND s.FechaBaja >= ?"
            params.append(hace90_str)
        elif filter_mode == "ACTIVOS_C_SALDO":
            base_sql += " AND s.Estado = '1' AND (s.FechaBaja IS NULL OR s.FechaBaja = '')"
        elif filter_mode == "ACTIVOS_POR_PLAN":
            base_sql += " AND s.Estado = '1' AND (s.FechaBaja IS NULL OR s.FechaBaja = '')"
            if plan:
                base_sql += " AND s.id_Plan = (SELECT idPlan FROM tbPlan WHERE Nomenclatura = ?)"
                params.append(plan)
        elif filter_mode == "INACTIVOS_POR_PLAN":
            base_sql += " AND (s.Estado != '1' OR (s.FechaBaja IS NOT NULL AND s.FechaBaja != ''))"
            if plan:
                base_sql += " AND s.id_Plan = (SELECT idPlan FROM tbPlan WHERE Nomenclatura = ?)"
                params.append(plan)
        elif filter_mode == "POR_DIA" and date:
            date_str = date[:10]
            base_sql += " AND s.Estado = '1' AND (s.FechaBaja IS NULL OR s.FechaBaja = '')"

        socios = conn.execute(base_sql, params).fetchall()
        pagos = _get_latest_payments_map(conn)
        planes = _get_plan_names_map(conn)
        count = 0

        for s in socios:
            sid = s["idSocio"]
            activo = (s["Estado"] == "1") and (not s["FechaBaja"] or s["FechaBaja"].strip() == "")

            # Latest payment (pre-fetched in a single grouped query)
            pago = pagos.get(sid)
            if pago is None:
                continue

            # ACTIVOS C/SALDO: filter by Saldo > 0
            if filter_mode == "ACTIVOS_C_SALDO":
                try:
                    saldo_val = float(pago["Saldo"] or 0)
                except (ValueError, TypeError):
                    saldo_val = 0
                if saldo_val <= 0:
                    continue

            # POR_DIA: filter by payment date matching selected date
            if filter_mode == "POR_DIA" and pago:
                pago_date = _parse_date(pago.get("FechadePago"))
                sel_date = _parse_date(date)
                if pago_date != sel_date:
                    continue

            nombre = f"{(s['Apellidos'] or '').strip()}, {(s['Nombres'] or '').strip()}"
            venc = _format_date_ddmmyyyy(pago.get("FechaVencimineto"))
            fpago = _format_date_ddmmyyyy(pago.get("FechadePago"))
            importe = str(pago.get("Importe") or "0")
            saldo = str(pago.get("Saldo") or "0")
            plan_name = planes.get(s["id_Plan"], "")
            estado_icon = "\u2705" if activo else ""

            tree.insert(
                "", "end",
                values=(sid, nombre, s["Documento"], s["NroInscripcion"],
                        venc, fpago, importe, saldo, plan_name, estado_icon),
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
        # Search entry
        self.entry_search = tk.Entry(
            self, bg="#FFFFFF", fg="#000000",
            font=("Helvetica", 10),
            relief="solid", bd=1,
            highlightthickness=1, highlightbackground="#999999",
        )
        self.entry_search.place(x=(WINDOW_WIDTH - 920) // 2, y=10, width=920, height=30)

        # Filters panel
        filters_frame = tk.LabelFrame(
            self, text="Filtros", bg=BG,
            font=("Helvetica", 9, "bold"),
            relief="groove", bd=1,
            labelanchor="nw",
        )
        filters_frame.place(x=(WINDOW_WIDTH - 920) // 2, y=45, width=920, height=90)

        # Row 1
        row1_y = 20
        x_pos = 15

        # ACTIVOS radio
        self.radio_activos = tk.Radiobutton(
            filters_frame, text="ACTIVOS", variable=self.filter_var,
            value="ACTIVOS", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter_change,
        )
        self.radio_activos.place(x=x_pos, y=row1_y)
        x_pos += 95

        # INACTIVOS radio + sublabel
        self.radio_inactivos = tk.Radiobutton(
            filters_frame, text="INACTIVOS", variable=self.filter_var,
            value="INACTIVOS", bg=BG, fg=FG_RED,
            font=("Helvetica", 9), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter_change,
        )
        self.radio_inactivos.place(x=x_pos, y=row1_y)
        tk.Label(
            filters_frame, text="(Últimos 90 días)",
            bg=BG, fg=FG_DARKRED, font=("Helvetica", 7),
        ).place(x=x_pos + 4, y=row1_y + 18)
        x_pos += 130

        # ACTIVOS C/SALDO
        self.radio_csaldo = tk.Radiobutton(
            filters_frame, text="ACTIVOS C/SALDO", variable=self.filter_var,
            value="ACTIVOS_C_SALDO", bg=BG, fg=FG_ORANGE,
            font=("Helvetica", 9), selectcolor=BG,
            activebackground=BG, activeforeground=FG_ORANGE,
            command=self._on_filter_change,
        )
        self.radio_csaldo.place(x=x_pos, y=row1_y)
        x_pos += 155

        # POR DÍA
        self.radio_pordia = tk.Radiobutton(
            filters_frame, text="POR DÍA", variable=self.filter_var,
            value="POR_DIA", bg=BG, fg="#000000",
            font=("Helvetica", 9), selectcolor=BG,
            activebackground=BG,
            command=self._on_filter_change,
        )
        self.radio_pordia.place(x=x_pos, y=row1_y)
        x_pos += 70

        self.entry_date = tk.Entry(
            filters_frame, bg="#FFFFFF", fg="#000000",
            font=("Helvetica", 9),
            relief="solid", bd=1,
            state="readonly", readonlybackground="#FFFFFF",
        )
        self.entry_date.place(x=x_pos, y=row1_y, width=200, height=25)
        self.entry_date.configure(state="normal")
        self.entry_date.insert(0, _today_es())
        self.entry_date.configure(state="readonly")

        # Row 2
        row2_y = 55
        x_pos = 15

        # ACTIVOS POR PLAN
        self.radio_aplan = tk.Radiobutton(
            filters_frame, text="ACTIVOS POR PLAN", variable=self.filter_var,
            value="ACTIVOS_POR_PLAN", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter_change,
        )
        self.radio_aplan.place(x=x_pos, y=row2_y)

        self.combo_plan = ttk.Combobox(
            filters_frame, textvariable=self.plan_var,
            width=18, state="readonly",
        )
        self.combo_plan.place(x=x_pos + 140, y=row2_y, width=160, height=24)
        self.combo_plan.bind("<<ComboboxSelected>>", lambda _e: self._on_filter_change())

        x_pos += 320

        # INACTIVOS POR PLAN
        self.radio_iplan = tk.Radiobutton(
            filters_frame, text="INACTIVOS POR PLAN", variable=self.filter_var,
            value="INACTIVOS_POR_PLAN", bg=BG, fg=FG_RED,
            font=("Helvetica", 9), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter_change,
        )
        self.radio_iplan.place(x=x_pos, y=row2_y)
        tk.Label(
            filters_frame, text="(Últimos 90 días)",
            bg=BG, fg=FG_DARKRED, font=("Helvetica", 7),
        ).place(x=x_pos + 4, y=row2_y + 18)

        # Load plans into combobox
        self._load_plans()

        # Treeview
        self._build_treeview()

        # Bottom bar
        self._build_bottom_bar()

    def _load_plans(self):
        conn = db.get_connection()
        try:
            plans = _get_plan_names(conn)
        finally:
            conn.close()
        self.combo_plan["values"] = plans
        if plans:
            self.combo_plan.current(0)

    def _build_treeview(self):
        columns = (
            "idSocio", "Nombre Completo", "Documento", "Nro",
            "Vencimiento", "FechaPago", "Importe", "Saldo", "Plan", "Estado",
        )
        widths = (70, 220, 120, 70, 120, 120, 90, 70, 150, 70)

        style = ttk.Style(self)
        style.configure("Grid.Treeview", background="#FFFFFF", foreground="#000000",
                        rowheight=24, fieldbackground="#FFFFFF")
        style.configure("Grid.Treeview.Heading", background=BG, font=("Helvetica", 8))
        style.map("Treeview",
                  background=[("selected", SELECTION_BG)],
                  foreground=[("selected", "#FFFFFF")])

        self.tree = ttk.Treeview(
            self, columns=columns, show="headings",
            style="Grid.Treeview", selectmode="browse",
        )

        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            anchor = "center" if col in ("idSocio", "Nro", "Importe") else "w"
            self.tree.column(col, width=w, minwidth=w, anchor=anchor)

        self.tree.tag_configure("green", foreground=FG_GREEN)

        # Place with scrollbars
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.place(x=(WINDOW_WIDTH - 920) // 2, y=145, width=920, height=360)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

    def _build_bottom_bar(self):
        bar = tk.Frame(self, bg=BG, height=45)
        bar.place(x=0, y=515, width=WINDOW_WIDTH, height=45)
        bar.pack_propagate(False)

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

    # ── Logic ─────────────────────────────────────────────────────────────

    def _on_filter_change(self):
        self.populate_grid()

    def populate_grid(self):
        mode = self.filter_var.get()
        plan = self.plan_var.get() if mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN") else None
        date = None
        if mode == "POR_DIA":
            raw = self.entry_date.get()
            # Convert "lunes, 11 de agosto de 2026" back to date
            try:
                date = datetime.datetime.strptime(raw, "%A, %d de %B de %Y").date().strftime("%Y-%m-%d")
            except ValueError:
                date = None
        count = populate_grid(self.tree, self.lbl_count, mode, plan=plan, date=date)
        # Apply green tag to idSocio, Importe, Saldo, Plan columns (indices 0,6,7,8)
        for item in self.tree.get_children():
            self.tree.item(item, tags=("green",))


def open_window(parent=None):
    """Open the Consultar Estados Socios window."""
    return ConsultarEstadosSociosWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
