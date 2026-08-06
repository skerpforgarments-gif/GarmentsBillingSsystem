import flet as ft
from datetime import date
from core.state import state
from core.theme import AppColors, AppStyles
from database.db import select, insert, update, delete, get_next_doc_no
from core.pdf_gen import pdf_engine, print_pdf
from num2words import num2words


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


class ChequeEntryScreen(ft.Container):
    TABLE = "cheque_entries"

    def __init__(self):
        super().__init__(expand=True, padding=0)
        self.record_id = None
        self.all_ids = []
        self.idx = -1
        self._build()

    def _build(self):
        S = AppStyles.get_input_style()

        # Toolbar
        toolbar = ft.Container(
            bgcolor="#F0FFF4", padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border=ft.border.all(1, "#D0E8D0"), border_radius=8,
            content=ft.Row([
                ft.ElevatedButton("New", icon=ft.icons.NOTE_ADD, on_click=self._new,
                                  style=ft.ButtonStyle(bgcolor=AppColors.PRIMARY, color="white", shape=ft.RoundedRectangleBorder(radius=6))),
                ft.ElevatedButton("Save", icon=ft.icons.SAVE, on_click=self._save,
                                  style=ft.ButtonStyle(bgcolor="#22C55E", color="white", shape=ft.RoundedRectangleBorder(radius=6))),
                ft.OutlinedButton("Delete", icon=ft.icons.DELETE_FOREVER, on_click=self._delete,
                                  style=ft.ButtonStyle(color="#EF4444", side=ft.BorderSide(1, "#EF4444"), shape=ft.RoundedRectangleBorder(radius=6))),
                ft.VerticalDivider(width=1, color="#CBD5E1"),
                ft.IconButton(ft.icons.SKIP_PREVIOUS_ROUNDED, on_click=self._prev, tooltip="Previous", icon_color=AppColors.PRIMARY),
                ft.IconButton(ft.icons.SKIP_NEXT_ROUNDED, on_click=self._next, tooltip="Next", icon_color=AppColors.PRIMARY),
                ft.VerticalDivider(width=1, color="#CBD5E1"),
                ft.ElevatedButton("History", icon=ft.icons.HISTORY, on_click=self._history,
                                  style=ft.ButtonStyle(bgcolor="#3B82F6", color="white", shape=ft.RoundedRectangleBorder(radius=6))),
                ft.ElevatedButton("Print", icon=ft.icons.PRINT, on_click=self._print,
                                  style=ft.ButtonStyle(bgcolor="#8B5CF6", color="white", shape=ft.RoundedRectangleBorder(radius=6))),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        # Header
        self.entry_no = ft.TextField(label="Entry No", width=140, read_only=True, **S)
        self.entry_date = ft.TextField(label="Entry Date", width=160, value=date.today().strftime("%d-%m-%Y"), **S)
        self.ac_payee = ft.Checkbox(label="A/c Payee", value=True)
        self.print_with_date = ft.Checkbox(label="Print With Date", value=True)

        # Bank selection
        self.bank_dd = ft.Dropdown(label="Bank", width=300, on_change=self._on_bank_change, **S)
        self.bank_branch_text = ft.Text("", size=12, color=AppColors.TEXT_SUB)
        self.bank_ifsc_text = ft.Text("", size=12, color=AppColors.TEXT_SUB)
        self.bank_acc_text = ft.Text("", size=14, weight="bold")

        # Cheque details
        self.cheque_date = ft.TextField(label="Cheque Date", width=160, value=date.today().strftime("%d-%m-%Y"), **S)
        self.cheque_no = ft.TextField(label="Chq. No", width=160, **S)

        # Pay
        self.payee_name = ft.TextField(label="Pay", width=400, on_change=self._on_amount_change, **S)

        # Amount
        self.amount = ft.TextField(label="Amount (Rs.)", width=200, keyboard_type=ft.KeyboardType.NUMBER,
                                   on_change=self._on_amount_change, **S)
        self.amount_words = ft.Text("", size=13, italic=True, color="#166534", weight="bold")
        self.amount_display = ft.Text("0", size=28, weight="bold", color="#DC2626")

        # Narration
        self.narration = ft.TextField(label="Narration", multiline=True, min_lines=2, max_lines=3, expand=True, **S)

        # Company name for cheque footer
        company_name = state.current_company.get("name", "") if state.current_company else ""

        # Layout — designed to match the Winsoft Cheque Entry screen
        self.content = ft.Column([
            # Title bar
            ft.Container(bgcolor="#166534", padding=ft.padding.symmetric(horizontal=20, vertical=10),
                          border_radius=ft.border_radius.only(top_left=8, top_right=8),
                          content=ft.Text("Cheque Entry", size=18, weight="bold", color="white")),
            toolbar,

            # Entry No + Date row
            ft.Container(padding=ft.padding.symmetric(horizontal=16, vertical=8),
                content=ft.Column([
                    ft.Row([self.entry_no, ft.Container(expand=True), self.entry_date], spacing=10),
                    ft.Row([self.ac_payee, self.print_with_date, ft.Container(expand=True), self.cheque_date]),
                ], spacing=8)),

            ft.Divider(height=1),

            # Bank section
            ft.Container(padding=ft.padding.symmetric(horizontal=16, vertical=8),
                content=ft.Column([
                    ft.Text("THE", size=10, color=AppColors.TEXT_SUB),
                    ft.Row([
                        self.bank_dd,
                        ft.Column([self.bank_branch_text, self.bank_ifsc_text], spacing=2),
                    ], spacing=20),
                ], spacing=4)),

            ft.Divider(height=1),

            # Pay section
            ft.Container(padding=ft.padding.symmetric(horizontal=16, vertical=8),
                content=ft.Column([
                    ft.Row([ft.Text("Pay", size=12, italic=True, color="#166534"), self.payee_name], spacing=10),
                    ft.Row([ft.Text("Rupees", size=12, italic=True, color="#166534"), self.amount_words], spacing=10),
                    ft.Row([
                        self.amount,
                        ft.Container(expand=True),
                        self.amount_display,
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=8)),

            ft.Divider(height=1),

            # Account No + Cheque No
            ft.Container(padding=ft.padding.symmetric(horizontal=16, vertical=8),
                content=ft.Row([
                    ft.Container(
                        border=ft.border.all(1, "#CBD5E1"), border_radius=6, padding=10,
                        content=ft.Row([ft.Text("A/C No.", weight="bold", size=12), self.bank_acc_text], spacing=10),
                    ),
                    ft.Container(width=20),
                    ft.Row([ft.Text("Chq.No.", weight="bold"), self.cheque_no], spacing=10),
                    ft.Container(expand=True),
                    ft.Column([
                        ft.Text(f"For {company_name}", weight="bold", size=12, text_align=ft.TextAlign.RIGHT),
                        ft.Container(height=20),
                        ft.Text("AUTHORISED SIGNATORY", weight="bold", size=11, italic=True, text_align=ft.TextAlign.RIGHT),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)),

            # Narration
            ft.Container(padding=ft.padding.symmetric(horizontal=16, vertical=4), content=self.narration),

        ], spacing=0, expand=True)

    def _on_bank_change(self, e):
        bid = self.bank_dd.value
        if not bid: return
        banks = select("banks", {"id": bid})
        if banks:
            b = banks[0]
            self.bank_branch_text.value = f"{b.get('branch', '')} Branch"
            self.bank_ifsc_text.value = f"IFSC: {b.get('ifsc_code', '')}"
            self.bank_acc_text.value = b.get("account_no", "")
            if self.page: self.update()

    def _on_amount_change(self, e):
        try:
            amt = float(self.amount.value or 0)
            words = num2words(int(amt), lang='en_IN').upper()
            paise = int(round((amt - int(amt)) * 100))
            if paise > 0:
                words += f" AND {num2words(paise, lang='en_IN').upper()} PAISE"
            words += " ONLY"
            self.amount_words.value = words
            self.amount_display.value = f"{amt:,.0f}"
        except:
            self.amount_words.value = ""
            self.amount_display.value = "0"
        if self.page:
            try: self.update()
            except: pass

    # ── LIFECYCLE ─────────────────────────────────────────────
    def did_mount(self):
        self._load_metadata()
        self._load_list()
        if not self.all_ids:
            self._new(None)
        else:
            self._load_record(self.all_ids[-1])

    def _load_metadata(self):
        if not state.company_id: return
        banks = select("banks", {"company_id": state.company_id})
        self.bank_dd.options = [ft.dropdown.Option(key=str(b["id"]), text=b["name"]) for b in banks]

    def _load_list(self):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: x.get("created_at", ""))
        self.all_ids = [str(r["id"]) for r in recs]

    # ── CRUD ──────────────────────────────────────────────────
    def _new(self, e):
        self.record_id = None
        self.entry_no.value = get_next_doc_no(self.TABLE, "CHQ", state.company_id, "entry_no")
        self.entry_date.value = date.today().strftime("%d-%m-%Y")
        self.cheque_date.value = date.today().strftime("%d-%m-%Y")
        self.bank_dd.value = None
        self.bank_branch_text.value = ""
        self.bank_ifsc_text.value = ""
        self.bank_acc_text.value = ""
        self.ac_payee.value = True
        self.print_with_date.value = True
        self.payee_name.value = ""
        self.amount.value = ""
        self.amount_words.value = ""
        self.amount_display.value = "0"
        self.cheque_no.value = ""
        self.narration.value = ""
        if self.page: self.update()

    def _save(self, e):
        if not state.company_id: return
        if not self.payee_name.value:
            _snack(self.page, "Payee name is required!", "red")
            return
        data = {
            "company_id": state.company_id,
            "entry_no": self.entry_no.value,
            "entry_date": self.entry_date.value,
            "bank_id": self.bank_dd.value or None,
            "bank_name": next((o.text for o in self.bank_dd.options if o.key == self.bank_dd.value), ""),
            "bank_branch": self.bank_branch_text.value.replace(" Branch", ""),
            "bank_ifsc": self.bank_ifsc_text.value.replace("IFSC: ", ""),
            "bank_account_no": self.bank_acc_text.value,
            "payee_name": self.payee_name.value,
            "amount": float(self.amount.value or 0),
            "cheque_no": self.cheque_no.value,
            "cheque_date": self.cheque_date.value,
            "ac_payee": self.ac_payee.value,
            "print_with_date": self.print_with_date.value,
            "narration": self.narration.value,
        }
        try:
            if self.record_id:
                update(self.TABLE, data, {"id": self.record_id})
            else:
                res = insert(self.TABLE, data)
                self.record_id = res[0]["id"]
            self._load_list()
            _snack(self.page, "Cheque Entry Saved!")
        except Exception as ex:
            _snack(self.page, f"Error: {ex}", "red")

    def _delete(self, e):
        if not self.record_id: return
        try:
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
        self.entry_no.value = r.get("entry_no", "")
        self.entry_date.value = r.get("entry_date", "")
        self.bank_dd.value = str(r["bank_id"]) if r.get("bank_id") else None
        self.bank_branch_text.value = f"{r.get('bank_branch', '')} Branch"
        self.bank_ifsc_text.value = f"IFSC: {r.get('bank_ifsc', '')}"
        self.bank_acc_text.value = r.get("bank_account_no", "")
        self.payee_name.value = r.get("payee_name", "")
        self.amount.value = str(r.get("amount", ""))
        self.cheque_no.value = r.get("cheque_no", "")
        self.cheque_date.value = r.get("cheque_date", "")
        self.ac_payee.value = r.get("ac_payee", True)
        self.print_with_date.value = r.get("print_with_date", True)
        self.narration.value = r.get("narration", "")
        # Trigger amount words recalc
        self._on_amount_change(None)
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

    def _print(self, e):
        try:
            bank_data = {}
            if self.bank_dd.value:
                b_recs = select("banks", {"id": self.bank_dd.value})
                if b_recs: bank_data = b_recs[0]

            comp_data = state.current_company or {}
            if not comp_data.get("address") and state.company_id:
                c_recs = select("companies", {"id": state.company_id})
                if c_recs: comp_data = c_recs[0]

            path = pdf_engine.generate_cheque(
                self.payee_name.value,
                float(self.amount.value or 0),
                self.cheque_date.value,
                ref_no=self.cheque_no.value,
                company_data=comp_data,
                bank_data=bank_data,
            )
            print_pdf(path)
            _snack(self.page, "Cheque PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _history(self, e):
        recs = select(self.TABLE, {"company_id": state.company_id})
        recs.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)

        banks = select("banks", {"company_id": state.company_id})
        bank_map = {str(b["id"]): b["name"] for b in banks}

        lv = ft.ListView(expand=1, spacing=10, padding=10)
        if not recs:
            lv.controls.append(ft.Container(content=ft.Text("No Cheque Entries found", color=AppColors.TEXT_MUTED), padding=20))

        for r in recs:
            r_id = str(r["id"])
            doc_no = f"Entry #{r.get('entry_no', '-')}"
            chq_no = r.get("cheque_no") or "-"
            entry_date = r.get("entry_date", "-")
            created_at = _format_ts(r.get("created_at"))
            payee = r.get("payee_name") or "-"
            bank_name = bank_map.get(str(r.get("bank_id")), "Bank")
            amount = float(r.get("amount") or 0)

            lv.controls.append(
                ft.Container(
                    padding=12,
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    border=ft.border.all(1, "#E2E8F0"),
                    shadow=ft.BoxShadow(blur_radius=4, color="#0A000000"),
                    content=ft.Row([
                        ft.Column([
                            ft.Row([
                                ft.Text(doc_no, weight="bold", size=14, color=AppColors.TEXT_HEADER),
                                ft.Text(f"(Chq No: {chq_no})", size=12, color=AppColors.TEXT_MUTED, weight="w500"),
                            ], spacing=8),
                            ft.Row([
                                ft.Icon(ft.icons.CALENDAR_TODAY, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(entry_date, size=11, color=ft.colors.BLUE_GREY_600),
                                ft.VerticalDivider(width=10),
                                ft.Icon(ft.icons.ACCESS_TIME, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(created_at, size=11, color=ft.colors.BLUE_GREY_600),
                            ], spacing=5),
                            ft.Text(f"Pay: {payee} | Bank: {bank_name}", size=13, weight="w500", color=AppColors.PRIMARY),
                        ], expand=True, spacing=4),
                        ft.Column([
                            ft.Text(f"₹ {amount:,.2f}", size=16, weight="bold", color=ft.colors.GREEN_700),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                        ft.Row([
                            ft.IconButton(ft.icons.EDIT_OUTLINED, tooltip="Edit Cheque", icon_color=AppColors.PRIMARY,
                                          on_click=lambda e, rid=r_id: self._load_from_history(rid, dlg)),
                            ft.IconButton(ft.icons.PRINT, tooltip="Print Cheque", icon_color=ft.colors.BLUE_700,
                                          on_click=lambda e, rec=r: self._print_history(rec)),
                            ft.IconButton(ft.icons.DELETE_OUTLINE, tooltip="Delete Cheque", icon_color="red",
                                          on_click=lambda e, rec=r: self._delete_from_history(rec, dlg))
                        ], spacing=4)
                    ])
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Recent Cheque Entries"),
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
            bank_data = {}
            if record.get("bank_id"):
                b_recs = select("banks", {"id": record["bank_id"]})
                if b_recs: bank_data = b_recs[0]

            comp_data = state.current_company or {}
            if not comp_data.get("address") and state.company_id:
                c_recs = select("companies", {"id": state.company_id})
                if c_recs: comp_data = c_recs[0]

            path = pdf_engine.generate_cheque(
                record.get("payee_name", ""),
                float(record.get("amount") or 0),
                record.get("cheque_date", ""),
                ref_no=record.get("cheque_no", ""),
                company_data=comp_data,
                bank_data=bank_data,
            )
            print_pdf(path)
            _snack(self.page, "Cheque PDF Generated")
        except Exception as ex:
            _snack(self.page, f"Print Error: {ex}", "red")

    def _delete_from_history(self, record, dlg):
        def confirm_del(e):
            try:
                rec_id = str(record["id"])
                delete(self.TABLE, {"id": rec_id})
                _close_dialog(self.page, confirm_dlg)
                _close_dialog(self.page, dlg)
                self._load_list()
                self._new(None)
                _snack(self.page, f"Cheque Entry #{record.get('entry_no')} deleted successfully", "green")
            except Exception as ex:
                _snack(self.page, f"Delete Error: {ex}", "red")

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete Cheque Entry #{record.get('entry_no')}? This cannot be undone."),
            actions=[
                ft.TextButton("Yes, Delete", on_click=confirm_del, style=ft.ButtonStyle(color="red")),
                ft.TextButton("Cancel", on_click=lambda e: _close_dialog(self.page, confirm_dlg))
            ]
        )
        self.page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        self.page.update()
