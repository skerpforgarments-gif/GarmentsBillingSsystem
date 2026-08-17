import flet as ft
from datetime import date
from core.state import state
from core.theme import AppColors, AppStyles
from database.db import select, insert, update, delete, get_next_doc_no
from core.pdf_gen import pdf_engine, print_pdf


# ═══════════════════════════════════════════════════════════════
# SHARED: TOOLBAR BUILDER
# ═══════════════════════════════════════════════════════════════
def build_toolbar(on_new, on_save, on_delete, on_prev, on_next, on_print, on_clear, on_history=None):
    return ft.Container(
        bgcolor="#F0F4FF",
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.all(1, "#D0D8E8"),
        border_radius=8,
        content=ft.Row([
            ft.ElevatedButton("New", icon=ft.icons.NOTE_ADD, on_click=on_new,
                              style=ft.ButtonStyle(bgcolor=AppColors.PRIMARY, color="white", shape=ft.RoundedRectangleBorder(radius=6))),
            ft.ElevatedButton("Save", icon=ft.icons.SAVE, on_click=on_save,
                              style=ft.ButtonStyle(bgcolor="#22C55E", color="white", shape=ft.RoundedRectangleBorder(radius=6))),
            ft.OutlinedButton("Delete", icon=ft.icons.DELETE_FOREVER, on_click=on_delete,
                              style=ft.ButtonStyle(color="#EF4444", side=ft.BorderSide(1, "#EF4444"), shape=ft.RoundedRectangleBorder(radius=6))),
            ft.VerticalDivider(width=1, color="#CBD5E1"),
            ft.IconButton(ft.icons.SKIP_PREVIOUS_ROUNDED, on_click=on_prev, tooltip="Previous", icon_color=AppColors.PRIMARY),
            ft.IconButton(ft.icons.SKIP_NEXT_ROUNDED, on_click=on_next, tooltip="Next", icon_color=AppColors.PRIMARY),
            ft.VerticalDivider(width=1, color="#CBD5E1"),
            ft.ElevatedButton("History", icon=ft.icons.HISTORY, on_click=on_history,
                              style=ft.ButtonStyle(bgcolor="#3B82F6", color="white", shape=ft.RoundedRectangleBorder(radius=6))),
            ft.ElevatedButton("Print", icon=ft.icons.PRINT, on_click=on_print,
                              style=ft.ButtonStyle(bgcolor="#8B5CF6", color="white", shape=ft.RoundedRectangleBorder(radius=6))),
            ft.OutlinedButton("Clear", icon=ft.icons.CLEAR_ALL, on_click=on_clear),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )


def _snack(page, msg, color="green"):
    if page:
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
        page.snack_bar.open = True
        page.update()


def _close_dialog(page, dlg):
    if dlg:
        dlg.open = False
    if page:
        page.update()


def _format_ts(ts):
    if not ts: return "-"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except:
        return str(ts)[:16]


def _get_fy():
    """Current financial year string like 2026"""
    return str(date.today().year)


# ═══════════════════════════════════════════════════════════════
#  1. YARN PURCHASE ORDER SCREEN
# ═══════════════════════════════════════════════════════════════
class YarnPOScreen(ft.Container):
    TABLE = "yarn_purchase_orders"
    ITEMS_TABLE = "yarn_po_items"
    PREFIX = "PO"
    DOC_COL = "po_no"

    def __init__(self):
        super().__init__(expand=True, padding=0)
        self.record_id = None
        self.all_ids = []
        self.idx = -1
        self.rows = []
        self._build()

    # ── BUILD ──────────────────────────────────────────────────
    def _build(self):
        S = AppStyles.get_input_style()

        # Header
        self.doc_no = ft.TextField(label="Po.No", width=140, read_only=True, **S)
        self.year_dd = ft.Dropdown(label="Year", width=100, value=_get_fy(),
                                   options=[ft.dropdown.Option(str(y)) for y in range(2024, 2031)], **S)
        self.doc_date = ft.TextField(label="Date", width=140, value=date.today().strftime("%d-%m-%Y"), **S)

        # Supplier
        self.supplier_dd = ft.Dropdown(label="Supplier", width=320, on_change=self._on_supplier, **S)
        self.attn = ft.TextField(label="Attn", width=300, **S)
        self.ref = ft.TextField(label="Ref", width=300, **S)
        self.delivery = ft.TextField(label="Delivery", expand=True, **S)
        self.remarks = ft.TextField(label="Remarks", multiline=True, min_lines=2, max_lines=4, expand=True, **S)

        # Grid
        hdr_style = {"size": 11, "weight": "bold", "color": AppColors.TEXT_HEADER}
        grid_header = ft.Container(
            bgcolor="#FEF9C3", padding=ft.padding.symmetric(horizontal=4, vertical=6),
            border=ft.border.all(1, "#E2E8F0"),
            content=ft.Row([
                ft.Text("S.No", width=40, **hdr_style), ft.Text("Item", width=200, **hdr_style),
                ft.Text("Bags", width=70, **hdr_style), ft.Text("Qty In Kgs", width=100, **hdr_style),
                ft.Text("Rate", width=100, **hdr_style), ft.Text("Tax Type", width=100, **hdr_style),
                ft.Text("GST %", width=70, **hdr_style), ft.Text("Amount", width=110, **hdr_style),
                ft.Text("Tax Amt", width=100, **hdr_style), ft.Text("Total Amt", width=110, **hdr_style),
                ft.Text("", width=40),
            ], spacing=4)
        )
        self.grid_body = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)

        # Footer totals
        self.tot_qty = ft.Text("0.000", weight="bold", width=100, text_align=ft.TextAlign.RIGHT)
        self.tot_amt = ft.Text("0.00", weight="bold", width=110, text_align=ft.TextAlign.RIGHT)
        self.tot_tax = ft.Text("0.00", weight="bold", width=100, text_align=ft.TextAlign.RIGHT)
        self.tot_grand = ft.Text("0.00", weight="bold", width=110, text_align=ft.TextAlign.RIGHT)

        footer = ft.Container(
            bgcolor="#F0FDF4", padding=ft.padding.symmetric(horizontal=4, vertical=8),
            border=ft.border.all(1, "#E2E8F0"),
            content=ft.Row([
                ft.Text("", width=40), ft.Text("", width=200), ft.Text("", width=70),
                self.tot_qty, ft.Text("", width=100), ft.Text("", width=100), ft.Text("", width=70),
                self.tot_amt, self.tot_tax, self.tot_grand, ft.Text("", width=40),
            ], spacing=4)
        )

        add_row_btn = ft.TextButton("+ Add Row", on_click=lambda _: self._add_row(), icon=ft.icons.ADD)

        toolbar = build_toolbar(self._new, self._save, self._delete, self._prev, self._next, self._print, self._clear, self._history)

        self.content = ft.Column([
            # Title
            ft.Container(bgcolor=AppColors.PRIMARY, padding=ft.padding.symmetric(horizontal=20, vertical=10),
                          border_radius=ft.border_radius.only(top_left=8, top_right=8),
                          content=ft.Text("Purchase Order (Yarn)", size=18, weight="bold", color="white")),
            toolbar,
            # Header
            ft.Container(padding=10, content=ft.Column([
                ft.Row([self.doc_no, self.year_dd, ft.Container(expand=True), self.doc_date], spacing=10),
                ft.Row([self.supplier_dd, self.attn], spacing=10),
                ft.Row([ft.Container(width=320), self.ref], spacing=10),
                ft.Row([ft.Container(width=320), self.delivery], spacing=10),
            ], spacing=6)),
            ft.Divider(height=1),
            # Grid
            grid_header,
            ft.Container(self.grid_body, expand=True, border=ft.border.only(left=ft.border.BorderSide(1, "#E2E8F0"), right=ft.border.BorderSide(1, "#E2E8F0"))),
            footer,
            ft.Row([add_row_btn], alignment=ft.MainAxisAlignment.END),
            # Remarks
            ft.Container(padding=ft.padding.symmetric(horizontal=10, vertical=4), content=self.remarks),
        ], spacing=0, expand=True)

    # ── GRID ROWS ─────────────────────────────────────────────
    def _add_row(self, data=None):
        S = AppStyles.get_input_style()
        sno = len(self.rows) + 1
        d = data or {}
        ctrls = {
            "item":     ft.TextField(value=d.get("item_name", ""), width=200, **S),
            "bags":     ft.TextField(value=str(d.get("bags", "")), width=70, on_change=lambda e: self._calc_row(ctrls), **S),
            "qty":      ft.TextField(value=str(d.get("qty_kgs", "")), width=100, on_change=lambda e: self._calc_row(ctrls), **S),
            "rate":     ft.TextField(value=str(d.get("rate", "")), width=100, on_change=lambda e: self._calc_row(ctrls), **S),
            "tax_type": ft.TextField(value=d.get("tax_type", "Gst 5%"), width=100, **S),
            "gst":      ft.TextField(value=str(d.get("gst_percent", "5")), width=70, on_change=lambda e: self._calc_row(ctrls), **S),
            "amount":   ft.TextField(value=str(d.get("amount", "")), width=110, read_only=True, **S),
            "tax_amt":  ft.TextField(value=str(d.get("tax_amount", "")), width=100, read_only=True, **S),
            "total":    ft.TextField(value=str(d.get("total_amount", "")), width=110, read_only=True, **S),
        }
        sno_text = ft.Text(str(sno), width=40, text_align=ft.TextAlign.CENTER, size=12)
        del_btn = ft.IconButton(ft.icons.CLOSE, icon_size=16, icon_color="#EF4444",
                                on_click=lambda _, c=ctrls: self._del_row(c), width=40)

        row_widget = ft.Container(
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
            bgcolor="#FFFFF0" if sno % 2 == 0 else "white",
            content=ft.Row([
                sno_text, ctrls["item"], ctrls["bags"], ctrls["qty"], ctrls["rate"],
                ctrls["tax_type"], ctrls["gst"], ctrls["amount"], ctrls["tax_amt"], ctrls["total"], del_btn
            ], spacing=4)
        )
        ctrls["_widget"] = row_widget
        ctrls["_sno"] = sno_text
        self.rows.append(ctrls)
        self.grid_body.controls.append(row_widget)
        if self.page: self.grid_body.update()

    def _del_row(self, ctrls):
        if ctrls in self.rows:
            self.rows.remove(ctrls)
            self.grid_body.controls.remove(ctrls["_widget"])
            self._renumber()
            self._calc_totals()
            if self.page: self.grid_body.update()

    def _renumber(self):
        for i, r in enumerate(self.rows, 1):
            r["_sno"].value = str(i)

    def _calc_row(self, ctrls):
        try:
            qty = float(ctrls["qty"].value or 0)
            rate = float(ctrls["rate"].value or 0)
            gst = float(ctrls["gst"].value or 0)
            amt = qty * rate
            tax = amt * gst / 100
            ctrls["amount"].value = f"{amt:.2f}"
            ctrls["tax_amt"].value = f"{tax:.2f}"
            ctrls["total"].value = f"{(amt + tax):.2f}"
            if self.page: self.update()
        except: pass
        self._calc_totals()

    def _calc_totals(self):
        tq = ta = tt = tg = 0
        for r in self.rows:
            try: tq += float(r["qty"].value or 0)
            except: pass
            try: ta += float(r["amount"].value or 0)
            except: pass
            try: tt += float(r["tax_amt"].value or 0)
            except: pass
            try: tg += float(r["total"].value or 0)
            except: pass
        self.tot_qty.value = f"{tq:.3f}"
        self.tot_amt.value = f"{ta:.2f}"
        self.tot_tax.value = f"{tt:.2f}"
        self.tot_grand.value = f"{tg:.2f}"
        if self.page:
            try: self.update()
            except: pass

    # ── SUPPLIER ──────────────────────────────────────────────
    def _on_supplier(self, e):
        sid = self.supplier_dd.value
        if not sid: return
        p = select("parties", {"id": sid})
        if p:
            p = p[0]
            self.attn.value = p.get("contact_person", "")
            self.delivery.value = f"{p.get('delivery_address_line1', '')}, {p.get('delivery_city', '')}".strip(", ")
            if self.page: self.update()

    # ── LIFECYCLE ─────────────────────────────────────────────
    def did_mount(self):
        self._load_metadata()
        self._load_list()
        self._new(None)
        self._history(None)

    def _load_metadata(self):
        if not state.company_id: return
        parties = select("parties", {"company_id": state.company_id, "party_type": ["Supplier", "Both"]})
        self.supplier_dd.options = [ft.dropdown.Option(key=str(p["id"]), text=p["name"]) for p in parties]

    def _load_list(self):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: x.get("created_at", ""))
        self.all_ids = [str(r["id"]) for r in recs]

    # ── CRUD ──────────────────────────────────────────────────
    def _new(self, e):
        self.record_id = None
        self.doc_no.value = get_next_doc_no(self.TABLE, self.PREFIX, state.company_id, self.DOC_COL)
        self.doc_date.value = date.today().strftime("%d-%m-%Y")
        self.year_dd.value = _get_fy()
        self.supplier_dd.value = None
        self.attn.value = ""
        self.ref.value = ""
        self.delivery.value = ""
        self.remarks.value = ""
        self.rows.clear()
        self.grid_body.controls.clear()
        self._add_row()
        self._calc_totals()
        if self.page: self.update()

    def _save(self, e):
        if not state.company_id: return
        header = {
            "company_id": state.company_id,
            "po_no": self.doc_no.value,
            "year": self.year_dd.value,
            "po_date": self.doc_date.value,
            "supplier_id": self.supplier_dd.value or None,
            "supplier_name": next((o.text for o in self.supplier_dd.options if o.key == self.supplier_dd.value), ""),
            "attn": self.attn.value,
            "ref": self.ref.value,
            "delivery": self.delivery.value,
            "remarks": self.remarks.value,
            "total_qty_kgs": float(self.tot_qty.value or 0),
            "total_amount": float(self.tot_amt.value or 0),
            "total_tax": float(self.tot_tax.value or 0),
            "grand_total": float(self.tot_grand.value or 0),
        }
        try:
            if self.record_id:
                update(self.TABLE, header, {"id": self.record_id})
                delete(self.ITEMS_TABLE, {"po_id": self.record_id})
                rec_id = self.record_id
            else:
                res = insert(self.TABLE, header)
                rec_id = res[0]["id"]
                self.record_id = rec_id

            for i, r in enumerate(self.rows, 1):
                if not r["item"].value: continue
                insert(self.ITEMS_TABLE, {
                    "company_id": state.company_id, "po_id": rec_id, "s_no": i,
                    "item_name": r["item"].value, "bags": int(r["bags"].value or 0),
                    "qty_kgs": float(r["qty"].value or 0), "rate": float(r["rate"].value or 0),
                    "tax_type": r["tax_type"].value, "gst_percent": float(r["gst"].value or 0),
                    "amount": float(r["amount"].value or 0), "tax_amount": float(r["tax_amt"].value or 0),
                    "total_amount": float(r["total"].value or 0),
                })
            self._load_list()
            _snack(self.page, "Purchase Order Saved!")
        except Exception as ex:
            _snack(self.page, f"Error: {ex}", "red")

    def _delete(self, e):
        if not self.record_id: return
        try:
            delete(self.ITEMS_TABLE, {"po_id": self.record_id})
            delete(self.TABLE, {"id": self.record_id})
            self._load_list()
            self._new(None)
            _snack(self.page, "Deleted")
        except Exception as ex:
            _snack(self.page, f"Error: {ex}", "red")

    def _load_record(self, rec_id):
        recs = select(self.TABLE, {"id": rec_id})
        if not recs: return
        r = recs[0]
        self.record_id = str(r["id"])
        self.doc_no.value = r.get("po_no", "")
        self.year_dd.value = r.get("year", _get_fy())
        self.doc_date.value = r.get("po_date", "")
        self.supplier_dd.value = str(r["supplier_id"]) if r.get("supplier_id") else None
        self.attn.value = r.get("attn", "")
        self.ref.value = r.get("ref", "")
        self.delivery.value = r.get("delivery", "")
        self.remarks.value = r.get("remarks", "")

        # Load items
        self.rows.clear()
        self.grid_body.controls.clear()
        items = select(self.ITEMS_TABLE, {"po_id": self.record_id})
        items.sort(key=lambda x: x.get("s_no", 0))
        for it in items:
            self._add_row(it)
        if not items:
            self._add_row()
        self._calc_totals()
        self.idx = self.all_ids.index(self.record_id) if self.record_id in self.all_ids else -1
        if self.page: self.update()

    def _prev(self, e):
        if self.idx > 0:
            self.idx -= 1
            self._load_record(self.all_ids[self.idx])

    def _next(self, e):
        if self.idx < len(self.all_ids) - 1:
            self.idx += 1
            self._load_record(self.all_ids[self.idx])

    def _clear(self, e):
        self._new(None)

    def _print(self, e):
        items = []
        for r in self.rows:
            if r["item"].value:
                items.append({
                    "item_name": r["item"].value, "bags": r["bags"].value, "qty_kgs": r["qty"].value,
                    "rate": r["rate"].value, "tax_percent": r["gst"].value,
                })
        header = {
            "po_no": self.doc_no.value, "po_date": self.doc_date.value,
            "supplier_name": next((o.text for o in self.supplier_dd.options if o.key == self.supplier_dd.value), ""),
            "supplier_address": "", "delivery": self.delivery.value, "remarks": self.remarks.value,
        }
        try:
            comp = state.current_company or {}
            path = pdf_engine.generate_yarn_po(header, items, comp)
            print_pdf(path)
            _snack(self.page, "PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _history(self, e):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)

        lv = ft.ListView(expand=1, spacing=10, padding=10)
        if not recs:
            lv.controls.append(ft.Container(content=ft.Text("No Purchase Orders found", color=AppColors.TEXT_MUTED), padding=20))

        for r in recs:
            r_id = str(r["id"])
            doc_no = r.get("po_no", "-")
            doc_date = r.get("po_date", "-")
            created_at = _format_ts(r.get("created_at"))
            supplier = r.get("supplier_name") or "-"
            tot_qty = float(r.get("total_qty_kgs") or 0)
            grand_total = float(r.get("grand_total") or 0)

            lv.controls.append(
                ft.Container(
                    padding=12,
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    border=ft.border.all(1, "#E2E8F0"),
                    shadow=ft.BoxShadow(blur_radius=4, color="#0A000000"),
                    content=ft.Row([
                        ft.Column([
                            ft.Text(doc_no, weight="bold", size=14, color=AppColors.TEXT_HEADER),
                            ft.Row([
                                ft.Icon(ft.icons.CALENDAR_TODAY, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(doc_date, size=11, color=ft.colors.BLUE_GREY_600),
                                ft.VerticalDivider(width=10),
                                ft.Icon(ft.icons.ACCESS_TIME, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(created_at, size=11, color=ft.colors.BLUE_GREY_600),
                            ], spacing=5),
                            ft.Text(supplier, size=13, weight="w500", color=AppColors.PRIMARY),
                        ], expand=True, spacing=4),
                        ft.Column([
                            ft.Text(f"{tot_qty:,.3f} Kgs", size=12, weight="bold"),
                            ft.Text(f"₹ {grand_total:,.2f}", size=15, weight="bold", color=ft.colors.GREEN_700),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                        ft.Row([
                            ft.IconButton(ft.icons.EDIT_OUTLINED, tooltip="Edit PO", icon_color=AppColors.PRIMARY,
                                          on_click=lambda e, rid=r_id: self._load_from_history(rid, dlg)),
                            ft.IconButton(ft.icons.PRINT, tooltip="Print PO", icon_color=ft.colors.BLUE_700,
                                          on_click=lambda e, rec=r: self._print_history(rec)),
                            ft.IconButton(ft.icons.DELETE_OUTLINE, tooltip="Delete PO", icon_color="red",
                                          on_click=lambda e, rec=r: self._delete_from_history(rec, dlg))
                        ], spacing=4)
                    ])
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Recent Yarn Purchase Orders"),
            content=ft.Container(width=650, height=450, content=lv),
            actions=[ft.TextButton("Close", on_click=lambda e: _close_dialog(self.page, dlg))]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _load_from_history(self, rec_id, dlg):
        _close_dialog(self.page, dlg)
        self._load_record(rec_id)

    def _print_history(self, record):
        try:
            items_data = select(self.ITEMS_TABLE, {"po_id": record["id"]})
            items = [{
                "item_name": it.get("item_name", ""),
                "bags": it.get("bags", 0),
                "qty_kgs": it.get("qty_kgs", 0),
                "rate": it.get("rate", 0),
                "tax_percent": it.get("gst_percent", 0),
            } for it in items_data]
            header = {
                "po_no": record.get("po_no", ""),
                "po_date": record.get("po_date", ""),
                "supplier_name": record.get("supplier_name", ""),
                "supplier_address": "",
                "delivery": record.get("delivery", ""),
                "remarks": record.get("remarks", ""),
            }
            comp = state.current_company or {}
            path = pdf_engine.generate_yarn_po(header, items, comp)
            print_pdf(path)
            _snack(self.page, "PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _delete_from_history(self, record, dlg):
        def confirm_del(e):
            try:
                rec_id = str(record["id"])
                delete(self.ITEMS_TABLE, {"po_id": rec_id})
                delete(self.TABLE, {"id": rec_id})
                _close_dialog(self.page, confirm_dlg)
                _close_dialog(self.page, dlg)
                self._load_list()
                self._new(None)
                _snack(self.page, f"PO {record.get('po_no')} deleted successfully", "green")
            except Exception as ex:
                _snack(self.page, f"Delete Error: {ex}", "red")

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete PO {record.get('po_no')}? This cannot be undone."),
            actions=[
                ft.TextButton("Yes, Delete", on_click=confirm_del, style=ft.ButtonStyle(color="red")),
                ft.TextButton("Cancel", on_click=lambda e: _close_dialog(self.page, confirm_dlg))
            ]
        )
        self.page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        self.page.update()


# ═══════════════════════════════════════════════════════════════
#  2. KNITTING PROGRAM SCREEN
# ═══════════════════════════════════════════════════════════════
class KnittingProgramScreen(ft.Container):
    TABLE = "knitting_programs"
    ITEMS_TABLE = "knitting_program_items"
    PREFIX = "KP"
    DOC_COL = "prog_no"

    def __init__(self):
        super().__init__(expand=True, padding=0)
        self.record_id = None
        self.all_ids = []
        self.idx = -1
        self.rows = []
        self._build()

    def _build(self):
        S = AppStyles.get_input_style()
        self.doc_no = ft.TextField(label="Prg.Nr", width=140, read_only=True, **S)
        self.year_dd = ft.Dropdown(label="Year", width=100, value=_get_fy(),
                                   options=[ft.dropdown.Option(str(y)) for y in range(2024, 2031)], **S)
        self.doc_date = ft.TextField(label="Date", width=140, value=date.today().strftime("%d-%m-%Y"), **S)
        self.party_dd = ft.Dropdown(label="Party", width=320, on_change=self._on_party, **S)
        self.attn = ft.TextField(label="Attn", width=300, **S)
        self.ref = ft.TextField(label="Ref", width=300, **S)
        self.delivery = ft.TextField(label="Delivery", expand=True, **S)
        self.remarks = ft.TextField(label="Remarks", multiline=True, min_lines=2, max_lines=4, expand=True, **S)

        hdr_style = {"size": 11, "weight": "bold", "color": AppColors.TEXT_HEADER}
        grid_header = ft.Container(
            bgcolor="#FEF9C3", padding=ft.padding.symmetric(horizontal=4, vertical=6),
            border=ft.border.all(1, "#E2E8F0"),
            content=ft.Row([
                ft.Text("S.No", width=40, **hdr_style), ft.Text("Item", width=200, **hdr_style),
                ft.Text("Yarn Description", width=200, **hdr_style),
                ft.Text("GSM / LL", width=90, **hdr_style), ft.Text("GG", width=70, **hdr_style),
                ft.Text("Dia", width=70, **hdr_style), ft.Text("Weight", width=100, **hdr_style),
                ft.Text("Roll/Pcs", width=90, **hdr_style), ft.Text("", width=40),
            ], spacing=4)
        )
        self.grid_body = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)

        toolbar = build_toolbar(self._new, self._save, self._delete, self._prev, self._next, self._print, self._clear, self._history)

        self.content = ft.Column([
            ft.Container(bgcolor="#DC2626", padding=ft.padding.symmetric(horizontal=20, vertical=10),
                          border_radius=ft.border_radius.only(top_left=8, top_right=8),
                          content=ft.Text("Knitting Program", size=18, weight="bold", color="white", italic=True)),
            toolbar,
            ft.Container(padding=10, content=ft.Column([
                ft.Row([self.doc_no, self.year_dd, ft.Container(expand=True), self.doc_date], spacing=10),
                ft.Row([self.party_dd, self.attn], spacing=10),
                ft.Row([ft.Container(width=320), self.ref], spacing=10),
                ft.Row([ft.Container(width=320), self.delivery], spacing=10),
            ], spacing=6)),
            ft.Divider(height=1),
            grid_header,
            ft.Container(self.grid_body, expand=True, border=ft.border.only(left=ft.border.BorderSide(1, "#E2E8F0"), right=ft.border.BorderSide(1, "#E2E8F0"))),
            ft.Row([ft.TextButton("+ Add Row", on_click=lambda _: self._add_row(), icon=ft.icons.ADD)], alignment=ft.MainAxisAlignment.END),
            ft.Container(padding=ft.padding.symmetric(horizontal=10, vertical=4), content=self.remarks),
        ], spacing=0, expand=True)

    def _add_row(self, data=None):
        S = AppStyles.get_input_style()
        sno = len(self.rows) + 1
        d = data or {}
        ctrls = {
            "item":     ft.TextField(value=d.get("item_name", ""), width=200, **S),
            "yarn":     ft.TextField(value=d.get("yarn_description", ""), width=200, **S),
            "gsm":      ft.TextField(value=str(d.get("gsm_ll", "")), width=90, **S),
            "gg":       ft.TextField(value=str(d.get("gg", "")), width=70, **S),
            "dia":      ft.TextField(value=str(d.get("dia", "")), width=70, **S),
            "weight":   ft.TextField(value=str(d.get("weight", "")), width=100, **S),
            "rolls":    ft.TextField(value=str(d.get("roll_pcs", "")), width=90, **S),
        }
        sno_text = ft.Text(str(sno), width=40, text_align=ft.TextAlign.CENTER, size=12)
        del_btn = ft.IconButton(ft.icons.CLOSE, icon_size=16, icon_color="#EF4444",
                                on_click=lambda _, c=ctrls: self._del_row(c), width=40)
        row_widget = ft.Container(
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
            bgcolor="#FFFFF0" if sno % 2 == 0 else "white",
            content=ft.Row([sno_text, ctrls["item"], ctrls["yarn"], ctrls["gsm"], ctrls["gg"],
                            ctrls["dia"], ctrls["weight"], ctrls["rolls"], del_btn], spacing=4)
        )
        ctrls["_widget"] = row_widget
        ctrls["_sno"] = sno_text
        self.rows.append(ctrls)
        self.grid_body.controls.append(row_widget)
        if self.page: self.grid_body.update()

    def _del_row(self, ctrls):
        if ctrls in self.rows:
            self.rows.remove(ctrls)
            self.grid_body.controls.remove(ctrls["_widget"])
            for i, r in enumerate(self.rows, 1): r["_sno"].value = str(i)
            if self.page: self.grid_body.update()

    def _on_party(self, e):
        pid = self.party_dd.value
        if not pid: return
        p = select("parties", {"id": pid})
        if p:
            p = p[0]
            self.attn.value = p.get("contact_person", "")
            self.delivery.value = f"{p.get('delivery_address_line1', '')}, {p.get('delivery_city', '')}".strip(", ")
            if self.page: self.update()

    def did_mount(self):
        self._load_metadata()
        self._load_list()
        self._new(None)
        self._history(None)

    def _load_metadata(self):
        if not state.company_id: return
        parties = select("parties", {"company_id": state.company_id})
        self.party_dd.options = [ft.dropdown.Option(key=str(p["id"]), text=p["name"]) for p in parties]

    def _load_list(self):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: x.get("created_at", ""))
        self.all_ids = [str(r["id"]) for r in recs]

    def _new(self, e):
        self.record_id = None
        self.doc_no.value = get_next_doc_no(self.TABLE, self.PREFIX, state.company_id, self.DOC_COL)
        self.doc_date.value = date.today().strftime("%d-%m-%Y")
        self.year_dd.value = _get_fy()
        self.party_dd.value = None
        self.attn.value = self.ref.value = self.delivery.value = self.remarks.value = ""
        self.rows.clear(); self.grid_body.controls.clear()
        self._add_row()
        if self.page: self.update()

    def _save(self, e):
        if not state.company_id: return
        header = {
            "company_id": state.company_id, "prog_no": self.doc_no.value, "year": self.year_dd.value,
            "prog_date": self.doc_date.value, "party_id": self.party_dd.value or None,
            "party_name": next((o.text for o in self.party_dd.options if o.key == self.party_dd.value), ""),
            "attn": self.attn.value, "ref": self.ref.value, "delivery": self.delivery.value, "remarks": self.remarks.value,
        }
        try:
            if self.record_id:
                update(self.TABLE, header, {"id": self.record_id})
                delete(self.ITEMS_TABLE, {"program_id": self.record_id})
                rec_id = self.record_id
            else:
                res = insert(self.TABLE, header)
                rec_id = res[0]["id"]
                self.record_id = rec_id

            for i, r in enumerate(self.rows, 1):
                if not r["item"].value: continue
                insert(self.ITEMS_TABLE, {
                    "company_id": state.company_id, "program_id": rec_id, "s_no": i,
                    "item_name": r["item"].value, "yarn_description": r["yarn"].value,
                    "gsm_ll": r["gsm"].value, "gg": r["gg"].value, "dia": r["dia"].value,
                    "weight": float(r["weight"].value or 0), "roll_pcs": int(r["rolls"].value or 0),
                })
            self._load_list()
            _snack(self.page, "Knitting Program Saved!")
        except Exception as ex:
            _snack(self.page, f"Error: {ex}", "red")

    def _delete(self, e):
        if not self.record_id: return
        try:
            delete(self.ITEMS_TABLE, {"program_id": self.record_id})
            delete(self.TABLE, {"id": self.record_id})
            self._load_list(); self._new(None)
            _snack(self.page, "Deleted")
        except Exception as ex:
            _snack(self.page, f"Error: {ex}", "red")

    def _load_record(self, rec_id):
        recs = select(self.TABLE, {"id": rec_id})
        if not recs: return
        r = recs[0]
        self.record_id = str(r["id"])
        self.doc_no.value = r.get("prog_no", "")
        self.year_dd.value = r.get("year", _get_fy())
        self.doc_date.value = r.get("prog_date", "")
        self.party_dd.value = str(r["party_id"]) if r.get("party_id") else None
        self.attn.value = r.get("attn", "")
        self.ref.value = r.get("ref", "")
        self.delivery.value = r.get("delivery", "")
        self.remarks.value = r.get("remarks", "")
        self.rows.clear(); self.grid_body.controls.clear()
        items = select(self.ITEMS_TABLE, {"program_id": self.record_id})
        items.sort(key=lambda x: x.get("s_no", 0))
        for it in items: self._add_row(it)
        if not items: self._add_row()
        self.idx = self.all_ids.index(self.record_id) if self.record_id in self.all_ids else -1
        if self.page: self.update()

    def _prev(self, e):
        if self.idx > 0: self.idx -= 1; self._load_record(self.all_ids[self.idx])
    def _next(self, e):
        if self.idx < len(self.all_ids) - 1: self.idx += 1; self._load_record(self.all_ids[self.idx])
    def _clear(self, e):
        self._new(None)

    def _print(self, e):
        items = [{"item_name": r["item"].value, "yarn_desc": r["yarn"].value, "gsm": r["gsm"].value,
                  "gg": r["gg"].value, "dia": r["dia"].value, "weight": r["weight"].value, "rolls": r["rolls"].value}
                 for r in self.rows if r["item"].value]
        header = {"prog_no": self.doc_no.value, "prog_date": self.doc_date.value,
                  "party_name": next((o.text for o in self.party_dd.options if o.key == self.party_dd.value), ""),
                  "remarks": self.remarks.value}
        try:
            path = pdf_engine.generate_knitting_program(header, items, state.current_company or {})
            print_pdf(path); _snack(self.page, "PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _history(self, e):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)

        lv = ft.ListView(expand=1, spacing=10, padding=10)
        if not recs:
            lv.controls.append(ft.Container(content=ft.Text("No Knitting Programs found", color=AppColors.TEXT_MUTED), padding=20))

        for r in recs:
            r_id = str(r["id"])
            doc_no = r.get("prog_no", "-")
            doc_date = r.get("prog_date", "-")
            created_at = _format_ts(r.get("created_at"))
            party = r.get("party_name") or "-"
            remarks = r.get("remarks") or ""

            lv.controls.append(
                ft.Container(
                    padding=12,
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    border=ft.border.all(1, "#E2E8F0"),
                    shadow=ft.BoxShadow(blur_radius=4, color="#0A000000"),
                    content=ft.Row([
                        ft.Column([
                            ft.Text(doc_no, weight="bold", size=14, color=AppColors.TEXT_HEADER),
                            ft.Row([
                                ft.Icon(ft.icons.CALENDAR_TODAY, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(doc_date, size=11, color=ft.colors.BLUE_GREY_600),
                                ft.VerticalDivider(width=10),
                                ft.Icon(ft.icons.ACCESS_TIME, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(created_at, size=11, color=ft.colors.BLUE_GREY_600),
                            ], spacing=5),
                            ft.Text(party, size=13, weight="w500", color=AppColors.PRIMARY),
                        ], expand=True, spacing=4),
                        ft.Column([
                            ft.Text(f"Ref: {r.get('ref') or '-'}", size=11, color=AppColors.TEXT_MUTED),
                            ft.Text(f"{remarks[:30]}..." if len(remarks) > 30 else remarks, size=11, color=AppColors.TEXT_SUB),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                        ft.Row([
                            ft.IconButton(ft.icons.EDIT_OUTLINED, tooltip="Edit Program", icon_color=AppColors.PRIMARY,
                                          on_click=lambda e, rid=r_id: self._load_from_history(rid, dlg)),
                            ft.IconButton(ft.icons.PRINT, tooltip="Print Program", icon_color=ft.colors.BLUE_700,
                                          on_click=lambda e, rec=r: self._print_history(rec)),
                            ft.IconButton(ft.icons.DELETE_OUTLINE, tooltip="Delete Program", icon_color="red",
                                          on_click=lambda e, rec=r: self._delete_from_history(rec, dlg))
                        ], spacing=4)
                    ])
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Recent Knitting Programs"),
            content=ft.Container(width=650, height=450, content=lv),
            actions=[ft.TextButton("Close", on_click=lambda e: _close_dialog(self.page, dlg))]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _load_from_history(self, rec_id, dlg):
        _close_dialog(self.page, dlg)
        self._load_record(rec_id)

    def _print_history(self, record):
        try:
            items_data = select(self.ITEMS_TABLE, {"program_id": record["id"]})
            items = [{
                "item_name": it.get("item_name", ""),
                "yarn_desc": it.get("yarn_description", ""),
                "gsm": it.get("gsm_ll", ""),
                "gg": it.get("gg", ""),
                "dia": it.get("dia", ""),
                "weight": it.get("weight", 0),
                "rolls": it.get("roll_pcs", 0),
            } for it in items_data]
            header = {
                "prog_no": record.get("prog_no", ""),
                "prog_date": record.get("prog_date", ""),
                "party_name": record.get("party_name", ""),
                "remarks": record.get("remarks", ""),
            }
            path = pdf_engine.generate_knitting_program(header, items, state.current_company or {})
            print_pdf(path)
            _snack(self.page, "PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _delete_from_history(self, record, dlg):
        def confirm_del(e):
            try:
                rec_id = str(record["id"])
                delete(self.ITEMS_TABLE, {"program_id": rec_id})
                delete(self.TABLE, {"id": rec_id})
                _close_dialog(self.page, confirm_dlg)
                _close_dialog(self.page, dlg)
                self._load_list()
                self._new(None)
                _snack(self.page, f"Program {record.get('prog_no')} deleted successfully", "green")
            except Exception as ex:
                _snack(self.page, f"Delete Error: {ex}", "red")

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete Knitting Program {record.get('prog_no')}? This cannot be undone."),
            actions=[
                ft.TextButton("Yes, Delete", on_click=confirm_del, style=ft.ButtonStyle(color="red")),
                ft.TextButton("Cancel", on_click=lambda e: _close_dialog(self.page, confirm_dlg))
            ]
        )
        self.page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        self.page.update()


# ═══════════════════════════════════════════════════════════════
#  3. DYEING PROGRAM SCREEN
# ═══════════════════════════════════════════════════════════════
class DyeingProgramScreen(ft.Container):
    TABLE = "dyeing_programs"
    ITEMS_TABLE = "dyeing_program_items"
    PREFIX = "DP"
    DOC_COL = "prog_no"

    def __init__(self):
        super().__init__(expand=True, padding=0)
        self.record_id = None
        self.all_ids = []
        self.idx = -1
        self.rows = []
        self._build()

    def _build(self):
        S = AppStyles.get_input_style()
        self.doc_no = ft.TextField(label="Prg.Nr", width=140, read_only=True, **S)
        self.year_dd = ft.Dropdown(label="Year", width=100, value=_get_fy(),
                                   options=[ft.dropdown.Option(str(y)) for y in range(2024, 2031)], **S)
        self.doc_date = ft.TextField(label="Date", width=140, value=date.today().strftime("%d-%m-%Y"), **S)
        self.party_dd = ft.Dropdown(label="Party", width=320, on_change=self._on_party, **S)
        self.attn = ft.TextField(label="Attn", width=300, **S)
        self.ref = ft.TextField(label="Ref", width=300, **S)
        self.delivery = ft.TextField(label="Delivery", expand=True, **S)
        self.remarks = ft.TextField(label="Remarks", multiline=True, min_lines=2, max_lines=4, expand=True, **S)

        hdr_style = {"size": 11, "weight": "bold", "color": AppColors.TEXT_HEADER}
        grid_header = ft.Container(
            bgcolor="#FEF9C3", padding=ft.padding.symmetric(horizontal=4, vertical=6),
            border=ft.border.all(1, "#E2E8F0"),
            content=ft.Row([
                ft.Text("S.No", width=40, **hdr_style), ft.Text("Item", width=200, **hdr_style),
                ft.Text("Colour", width=160, **hdr_style), ft.Text("Process", width=160, **hdr_style),
                ft.Text("Dia", width=80, **hdr_style), ft.Text("Weight (Kgs)", width=110, **hdr_style),
                ft.Text("Batch", width=110, **hdr_style), ft.Text("", width=40),
            ], spacing=4)
        )
        self.grid_body = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)

        toolbar = build_toolbar(self._new, self._save, self._delete, self._prev, self._next, self._print, self._clear, self._history)

        self.content = ft.Column([
            ft.Container(bgcolor="#7C3AED", padding=ft.padding.symmetric(horizontal=20, vertical=10),
                          border_radius=ft.border_radius.only(top_left=8, top_right=8),
                          content=ft.Text("Dyeing Program", size=18, weight="bold", color="white", italic=True)),
            toolbar,
            ft.Container(padding=10, content=ft.Column([
                ft.Row([self.doc_no, self.year_dd, ft.Container(expand=True), self.doc_date], spacing=10),
                ft.Row([self.party_dd, self.attn], spacing=10),
                ft.Row([ft.Container(width=320), self.ref], spacing=10),
                ft.Row([ft.Container(width=320), self.delivery], spacing=10),
            ], spacing=6)),
            ft.Divider(height=1),
            grid_header,
            ft.Container(self.grid_body, expand=True, border=ft.border.only(left=ft.border.BorderSide(1, "#E2E8F0"), right=ft.border.BorderSide(1, "#E2E8F0"))),
            ft.Row([ft.TextButton("+ Add Row", on_click=lambda _: self._add_row(), icon=ft.icons.ADD)], alignment=ft.MainAxisAlignment.END),
            ft.Container(padding=ft.padding.symmetric(horizontal=10, vertical=4), content=self.remarks),
        ], spacing=0, expand=True)

    def _add_row(self, data=None):
        S = AppStyles.get_input_style()
        sno = len(self.rows) + 1
        d = data or {}
        ctrls = {
            "item":    ft.TextField(value=d.get("item_name", ""), width=200, **S),
            "colour":  ft.TextField(value=d.get("colour", ""), width=160, **S),
            "process": ft.TextField(value=d.get("process", ""), width=160, **S),
            "dia":     ft.TextField(value=d.get("dia", ""), width=80, **S),
            "weight":  ft.TextField(value=str(d.get("weight_kgs", "") or d.get("weight", "")), width=110, **S),
            "batch":   ft.TextField(value=d.get("batch", ""), width=110, **S),
        }
        sno_text = ft.Text(str(sno), width=40, text_align=ft.TextAlign.CENTER, size=12)
        del_btn = ft.IconButton(ft.icons.CLOSE, icon_size=16, icon_color="#EF4444",
                                on_click=lambda _, c=ctrls: self._del_row(c), width=40)
        row_widget = ft.Container(
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
            bgcolor="#FFFFF0" if sno % 2 == 0 else "white",
            content=ft.Row([sno_text, ctrls["item"], ctrls["colour"], ctrls["process"],
                            ctrls["dia"], ctrls["weight"], ctrls["batch"], del_btn], spacing=4)
        )
        ctrls["_widget"] = row_widget
        ctrls["_sno"] = sno_text
        self.rows.append(ctrls)
        self.grid_body.controls.append(row_widget)
        if self.page: self.grid_body.update()

    def _del_row(self, ctrls):
        if ctrls in self.rows:
            self.rows.remove(ctrls)
            self.grid_body.controls.remove(ctrls["_widget"])
            for i, r in enumerate(self.rows, 1): r["_sno"].value = str(i)
            if self.page: self.grid_body.update()

    def _on_party(self, e):
        pid = self.party_dd.value
        if not pid: return
        p = select("parties", {"id": pid})
        if p:
            p = p[0]
            self.attn.value = p.get("contact_person", "")
            self.delivery.value = f"{p.get('delivery_address_line1', '')}, {p.get('delivery_city', '')}".strip(", ")
            if self.page: self.update()

    def did_mount(self):
        self._load_metadata()
        self._load_list()
        self._new(None)
        self._history(None)

    def _load_metadata(self):
        if not state.company_id: return
        parties = select("parties", {"company_id": state.company_id})
        self.party_dd.options = [ft.dropdown.Option(key=str(p["id"]), text=p["name"]) for p in parties]

    def _load_list(self):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: x.get("created_at", ""))
        self.all_ids = [str(r["id"]) for r in recs]

    def _new(self, e):
        self.record_id = None
        self.doc_no.value = get_next_doc_no(self.TABLE, self.PREFIX, state.company_id, self.DOC_COL)
        self.doc_date.value = date.today().strftime("%d-%m-%Y")
        self.year_dd.value = _get_fy()
        self.party_dd.value = None
        self.attn.value = self.ref.value = self.delivery.value = self.remarks.value = ""
        self.rows.clear(); self.grid_body.controls.clear()
        self._add_row()
        if self.page: self.update()

    def _save(self, e):
        if not state.company_id: return
        header = {
            "company_id": state.company_id, "prog_no": self.doc_no.value, "year": self.year_dd.value,
            "prog_date": self.doc_date.value, "party_id": self.party_dd.value or None,
            "party_name": next((o.text for o in self.party_dd.options if o.key == self.party_dd.value), ""),
            "attn": self.attn.value, "ref": self.ref.value, "delivery": self.delivery.value, "remarks": self.remarks.value,
        }
        try:
            if self.record_id:
                update(self.TABLE, header, {"id": self.record_id})
                delete(self.ITEMS_TABLE, {"program_id": self.record_id})
                rec_id = self.record_id
            else:
                res = insert(self.TABLE, header)
                rec_id = res[0]["id"]
                self.record_id = rec_id

            for i, r in enumerate(self.rows, 1):
                if not r["item"].value: continue
                insert(self.ITEMS_TABLE, {
                    "company_id": state.company_id, "program_id": rec_id, "s_no": i,
                    "item_name": r["item"].value, "colour": r["colour"].value,
                    "process": r["process"].value, "dia": r["dia"].value,
                    "weight_kgs": float(r["weight"].value or 0), "batch": r["batch"].value,
                })
            self._load_list()
            _snack(self.page, "Dyeing Program Saved!")
        except Exception as ex:
            _snack(self.page, f"Error: {ex}", "red")

    def _delete(self, e):
        if not self.record_id: return
        try:
            delete(self.ITEMS_TABLE, {"program_id": self.record_id})
            delete(self.TABLE, {"id": self.record_id})
            self._load_list(); self._new(None)
            _snack(self.page, "Deleted")
        except Exception as ex:
            _snack(self.page, f"Error: {ex}", "red")

    def _load_record(self, rec_id):
        recs = select(self.TABLE, {"id": rec_id})
        if not recs: return
        r = recs[0]
        self.record_id = str(r["id"])
        self.doc_no.value = r.get("prog_no", "")
        self.year_dd.value = r.get("year", _get_fy())
        self.doc_date.value = r.get("prog_date", "")
        self.party_dd.value = str(r["party_id"]) if r.get("party_id") else None
        self.attn.value = r.get("attn", "")
        self.ref.value = r.get("ref", "")
        self.delivery.value = r.get("delivery", "")
        self.remarks.value = r.get("remarks", "")
        self.rows.clear(); self.grid_body.controls.clear()
        items = select(self.ITEMS_TABLE, {"program_id": self.record_id})
        items.sort(key=lambda x: x.get("s_no", 0))
        for it in items: self._add_row(it)
        if not items: self._add_row()
        self.idx = self.all_ids.index(self.record_id) if self.record_id in self.all_ids else -1
        if self.page: self.update()

    def _prev(self, e):
        if self.idx > 0: self.idx -= 1; self._load_record(self.all_ids[self.idx])
    def _next(self, e):
        if self.idx < len(self.all_ids) - 1: self.idx += 1; self._load_record(self.all_ids[self.idx])
    def _clear(self, e):
        self._new(None)

    def _print(self, e):
        items = [{"item_name": r["item"].value, "colour": r["colour"].value, "process": r["process"].value,
                  "dia": r["dia"].value, "weight": r["weight"].value, "batch": r["batch"].value}
                 for r in self.rows if r["item"].value]
        header = {"prog_no": self.doc_no.value, "prog_date": self.doc_date.value,
                  "party_name": next((o.text for o in self.party_dd.options if o.key == self.party_dd.value), ""),
                  "remarks": self.remarks.value}
        try:
            path = pdf_engine.generate_dyeing_program(header, items, state.current_company or {})
            print_pdf(path); _snack(self.page, "PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _history(self, e):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)

        lv = ft.ListView(expand=1, spacing=10, padding=10)
        if not recs:
            lv.controls.append(ft.Container(content=ft.Text("No Dyeing Programs found", color=AppColors.TEXT_MUTED), padding=20))

        for r in recs:
            r_id = str(r["id"])
            doc_no = r.get("prog_no", "-")
            doc_date = r.get("prog_date", "-")
            created_at = _format_ts(r.get("created_at"))
            party = r.get("party_name") or "-"
            remarks = r.get("remarks") or ""

            lv.controls.append(
                ft.Container(
                    padding=12,
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    border=ft.border.all(1, "#E2E8F0"),
                    shadow=ft.BoxShadow(blur_radius=4, color="#0A000000"),
                    content=ft.Row([
                        ft.Column([
                            ft.Text(doc_no, weight="bold", size=14, color=AppColors.TEXT_HEADER),
                            ft.Row([
                                ft.Icon(ft.icons.CALENDAR_TODAY, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(doc_date, size=11, color=ft.colors.BLUE_GREY_600),
                                ft.VerticalDivider(width=10),
                                ft.Icon(ft.icons.ACCESS_TIME, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(created_at, size=11, color=ft.colors.BLUE_GREY_600),
                            ], spacing=5),
                            ft.Text(party, size=13, weight="w500", color=AppColors.PRIMARY),
                        ], expand=True, spacing=4),
                        ft.Column([
                            ft.Text(f"Ref: {r.get('ref') or '-'}", size=11, color=AppColors.TEXT_MUTED),
                            ft.Text(f"{remarks[:30]}..." if len(remarks) > 30 else remarks, size=11, color=AppColors.TEXT_SUB),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                        ft.Row([
                            ft.IconButton(ft.icons.EDIT_OUTLINED, tooltip="Edit Program", icon_color=AppColors.PRIMARY,
                                          on_click=lambda e, rid=r_id: self._load_from_history(rid, dlg)),
                            ft.IconButton(ft.icons.PRINT, tooltip="Print Program", icon_color=ft.colors.BLUE_700,
                                          on_click=lambda e, rec=r: self._print_history(rec)),
                            ft.IconButton(ft.icons.DELETE_OUTLINE, tooltip="Delete Program", icon_color="red",
                                          on_click=lambda e, rec=r: self._delete_from_history(rec, dlg))
                        ], spacing=4)
                    ])
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Recent Dyeing Programs"),
            content=ft.Container(width=650, height=450, content=lv),
            actions=[ft.TextButton("Close", on_click=lambda e: _close_dialog(self.page, dlg))]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _load_from_history(self, rec_id, dlg):
        _close_dialog(self.page, dlg)
        self._load_record(rec_id)

    def _print_history(self, record):
        try:
            items_data = select(self.ITEMS_TABLE, {"program_id": record["id"]})
            items = [{
                "item_name": it.get("item_name", ""),
                "colour": it.get("colour", ""),
                "process": it.get("process", ""),
                "weight": it.get("weight_kgs", 0),
                "batch": it.get("batch", ""),
            } for it in items_data]
            header = {
                "prog_no": record.get("prog_no", ""),
                "prog_date": record.get("prog_date", ""),
                "party_name": record.get("party_name", ""),
                "remarks": record.get("remarks", ""),
            }
            path = pdf_engine.generate_dyeing_program(header, items, state.current_company or {})
            print_pdf(path)
            _snack(self.page, "PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _delete_from_history(self, record, dlg):
        def confirm_del(e):
            try:
                rec_id = str(record["id"])
                delete(self.ITEMS_TABLE, {"program_id": rec_id})
                delete(self.TABLE, {"id": rec_id})
                _close_dialog(self.page, confirm_dlg)
                _close_dialog(self.page, dlg)
                self._load_list()
                self._new(None)
                _snack(self.page, f"Program {record.get('prog_no')} deleted successfully", "green")
            except Exception as ex:
                _snack(self.page, f"Delete Error: {ex}", "red")

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete Dyeing Program {record.get('prog_no')}? This cannot be undone."),
            actions=[
                ft.TextButton("Yes, Delete", on_click=confirm_del, style=ft.ButtonStyle(color="red")),
                ft.TextButton("Cancel", on_click=lambda e: _close_dialog(self.page, confirm_dlg))
            ]
        )
        self.page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        self.page.update()
