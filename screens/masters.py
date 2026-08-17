import flet as ft
import json
from core.theme import AppColors, AppStyles


from core.state import state
from database.db import select, insert, delete, update
from components.table import TableBuilder
from components.form import FormBuilder
from components.item_master_form import ItemMasterForm
from components.price_list_form import PriceListForm
from components.size_matrix import sort_sizes


# =========================================================
# INLINE PARTY MASTER FORM
# =========================================================
class PartyMasterForm(ft.Stack):
    def __init__(self, on_submit=None):
        super().__init__()
        self.expand = True
        self.on_submit = on_submit
        
        # Internal Modal Layer
        self.modal_layer = ft.Container(
            content=ft.Text("Modal"),
            visible=False,
            bgcolor="#80000000", # Semi-transparent overlay
            left=0, right=0, top=0, bottom=0,
            alignment=ft.alignment.center,
        )
        
        # Unified Styling
        self.style_args = AppStyles.get_input_style()

        # --- Basic Info ---
        self.name = ft.TextField(label="Party Name *", width=280, **self.style_args)
        self.party_type = ft.Dropdown(
            label="Party Type", width=180, value="Both", **self.style_args,
            options=[ft.dropdown.Option("Customer"), ft.dropdown.Option("Supplier"), ft.dropdown.Option("Both")]
        )
        # Billing Address
        self.billing_addr1 = ft.TextField(label="Billing Address Line 1", width=280, **self.style_args)
        self.billing_addr2 = ft.TextField(label="Billing Address Line 2", width=280, **self.style_args)
        self.billing_addr3 = ft.TextField(label="Billing Address Line 3", width=280, **self.style_args)
        self.city = ft.TextField(label="City", width=160, **self.style_args)
        self.district = ft.TextField(label="District", width=160, **self.style_args)
        self.state_field = ft.TextField(label="State", width=160, **self.style_args)
        self.pincode = ft.TextField(label="Pincode", width=120, **self.style_args)
        # Delivery Address
        self.delivery_addr1 = ft.TextField(label="Delivery Address Line 1", width=280, **self.style_args)
        self.delivery_addr2 = ft.TextField(label="Delivery Address Line 2", width=280, **self.style_args)
        self.delivery_addr3 = ft.TextField(label="Delivery Address Line 3", width=280, **self.style_args)
        self.delivery_city = ft.TextField(label="Delivery City", width=160, **self.style_args)
        self.delivery_district = ft.TextField(label="Delivery District", width=160, **self.style_args)
        self.delivery_state = ft.TextField(label="Delivery State", width=160, **self.style_args)
        self.delivery_pincode = ft.TextField(label="Delivery Pincode", width=120, **self.style_args)
        self.code = ft.TextField(label="Code", width=100, **self.style_args)
        self.phone = ft.TextField(label="Phone", width=160, **self.style_args)
        self.mobile = ft.TextField(label="Mobile", width=160, **self.style_args)
        self.fax = ft.TextField(label="Fax", width=120, **self.style_args)
        self.email = ft.TextField(label="Email", width=220, **self.style_args)

        # --- Tax Info ---
        self.gstin = ft.TextField(label="GSTIN", width=200, **self.style_args)
        self.cst_no = ft.TextField(label="CST No", width=160, **self.style_args)
        self.pan_no = ft.TextField(label="PAN No", width=160, **self.style_args)

        # --- Linked Masters ---
        self.agent_id = ft.Dropdown(label="Select Agent", width=200, **self.style_args)
        self.transporter_id = ft.Dropdown(label="Select Transporter", width=200, **self.style_args)
        self.courier_name = ft.TextField(label="Courier Name", width=200, **self.style_args)
        self.reference = ft.TextField(label="Reference", width=160, **self.style_args)

        # --- Documents & Order ---
        self.documents_thro = ft.Dropdown(
            label="Documents Thro'", width=160, value="Direct", **self.style_args,
            options=[ft.dropdown.Option("Direct"), ft.dropdown.Option("Bank")]
        )
        self.order_thro = ft.Dropdown(
            label="Order Thro'", width=160, value="DIRECT", **self.style_args,
            options=[ft.dropdown.Option("DIRECT"), ft.dropdown.Option("AGENT")]
        )

        # --- Financial Terms ---
        self.opening_balance = ft.TextField(label="Opening Balance", width=150, value="0",
                                             keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.opn_bal_type = ft.Dropdown(
            label="Type", width=120, value="DEBIT", **self.style_args,
            options=[ft.dropdown.Option("DEBIT"), ft.dropdown.Option("CREDIT")]
        )
        self.for_allowed = ft.Dropdown(
            label="F.O.R Allowed", width=140, value="Yes", **self.style_args,
            options=[ft.dropdown.Option("Yes"), ft.dropdown.Option("No")]
        )
        self.credit_days = ft.TextField(label="Credit Days", width=120, value="0",
                                         keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.credit_limit = ft.TextField(label="Credit Limit Rs", width=150, value="0",
                                          keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.price_type = ft.Dropdown(
            label="Price Type", width=140, value="Wholesale", **self.style_args,
            options=[
                ft.dropdown.Option("Wholesale"),
                ft.dropdown.Option("Retail"),
                ft.dropdown.Option("MRP")
            ]
        )
        self.price_list_id = ft.Dropdown(label="Select Price List", width=200, **self.style_args)

        # --- Tax Settings ---
        self.tax_type = ft.Dropdown(
            label="Tax Slab", width=220, on_change=self.on_tax_change, **self.style_args
        )
        self.tax_details = ft.Text("", size=11, italic=True, color=AppColors.TEXT_SUB)
        self.gst_percent = ft.TextField(label="Total Rate %", width=100, value="0", read_only=True,
                                          keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.cgst_percent = ft.TextField(label="CGST %", width=80, value="0", read_only=True,
                                          keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.sgst_percent = ft.TextField(label="SGST %", width=80, value="0", read_only=True,
                                          keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.igst_percent = ft.TextField(label="IGST %", width=80, value="0", read_only=True,
                                          keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.tcs_percent = ft.TextField(label="TCS %", width=80, value="0", read_only=True,
                                         keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        self.cess_percent = ft.TextField(label="CESS %", width=80, value="0", read_only=True,
                                          keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)
        
        self.tcs_applicable = ft.Checkbox(label="TCS Appl.", value=False, check_color=AppColors.PRIMARY)
        self.all_taxes = []

        # --- Discounts ---
        self.discount_percent = ft.TextField(label="Discount %", width=120, value="0",
                                         keyboard_type=ft.KeyboardType.NUMBER, **self.style_args)

        # --- Bank Details ---
        self.bank_name = ft.TextField(label="Bank Name", width=220, **self.style_args)
        self.bank_acc = ft.TextField(label="Account No", width=220, **self.style_args)
        self.bank_ifsc = ft.TextField(label="IFSC Code", width=140, **self.style_args)

        # --- Status ---
        self.remarks = ft.TextField(label="Remarks", width=300, **self.style_args)
        
        self.status_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Approved", label="Approved"),
                ft.Radio(value="Blocked", label="Blocked")
            ], spacing=20),
            value="Approved"
        )

        # --- Action Buttons ---
        save_btn = ft.ElevatedButton(
            "Save Party", 
            icon=ft.icons.SAVE, 
            on_click=self._submit,
            style=AppStyles.primary_button_style(),
            height=45
        )
        clear_btn = ft.TextButton(
            "Clear", 
            icon=ft.icons.REFRESH, 
            on_click=self.clear,
            style=AppStyles.secondary_button_style()
        )

        # --- Layout ---
        def section(title, controls):
            return ft.Container(
                content=ft.Column([
                    ft.Text(title.upper(), weight="bold", size=10, color=AppColors.PRIMARY, style=ft.TextStyle(letter_spacing=1.0)),
                    ft.Divider(height=1, color="#F1F5F9"),
                    *controls
                ], spacing=15),
                border_radius=AppStyles.RADIUS,
                bgcolor="#FFFFFF",
                padding=20,
                border=ft.border.all(1, "#F1F5F9"),
                margin=ft.margin.only(bottom=20)
            )

        # --- Main Layout Container ---
        self.form_container = ft.Container(
            padding=8,
            left=0, right=0, top=0, bottom=0,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=0,
                controls=[
                    section("Basic Information", [
                        ft.Row([self.name, self.party_type, self.code], spacing=10, wrap=True),
                        ft.Row([self.phone, self.mobile, self.fax, self.email], spacing=10, wrap=True),
                    ]),
                    section("Billing Address", [
                        ft.Row([self.billing_addr1, self.billing_addr2], spacing=10, wrap=True),
                        ft.Row([self.billing_addr3], spacing=10, wrap=True),
                        ft.Row([self.city, self.district, self.state_field, self.pincode], spacing=10, wrap=True),
                    ]),
                    section("Delivery Address", [
                        ft.Row([self.delivery_addr1, self.delivery_addr2], spacing=10, wrap=True),
                        ft.Row([self.delivery_addr3], spacing=10, wrap=True),
                        ft.Row([self.delivery_city, self.delivery_district, self.delivery_state, self.delivery_pincode], spacing=10, wrap=True),
                    ]),
                    section("Tax Information", [
                        ft.Row([self.gstin, self.cst_no, self.pan_no], spacing=10, wrap=True),
                    ]),
                    section("Logistics", [
                        ft.Row([self.agent_id, self.transporter_id, self.courier_name], spacing=10, wrap=True),
                        ft.Row([self.documents_thro, self.order_thro, self.reference], spacing=10, wrap=True),
                    ]),
                    section("Financial Terms", [
                        ft.Row([self.opening_balance, self.opn_bal_type, self.for_allowed], spacing=10, wrap=True),
                        ft.Row([self.credit_days, self.credit_limit, self.price_list_id, self.price_type], spacing=10, wrap=True),
                    ]),
                    section("Tax Settings", [
                        ft.Column([
                            ft.Row([self.tax_type, self.tax_details], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Row([
                                self.cgst_percent, self.sgst_percent, self.igst_percent, 
                                self.tcs_percent, self.cess_percent, self.gst_percent,
                                self.tcs_applicable
                            ], spacing=10, wrap=True),
                        ], spacing=10)
                    ]),
                    section("Discount", [
                        ft.Row([self.discount_percent], spacing=10, wrap=True),
                    ]),
                    section("Bank Details", [
                        ft.Row([self.bank_name, self.bank_acc, self.bank_ifsc], spacing=10, wrap=True),
                    ]),
                    section("Status & Remarks", [
                        ft.Row([self.remarks, self.status_radio], spacing=25, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ]),
                    ft.Row([save_btn, clear_btn], spacing=12, wrap=True),
                ]
            )
        )

        self.controls = [
            self.form_container,
            self.modal_layer
        ]

    def get_values(self):
        return {
            "name": self.name.value or "",
            "billing_address_line1": self.billing_addr1.value or "",
            "billing_address_line2": self.billing_addr2.value or "",
            "billing_address_line3": self.billing_addr3.value or "",
            "billing_city": self.city.value or "",
            "billing_district": self.district.value or "",
            "billing_state": self.state_field.value or "",
            "billing_pincode": self.pincode.value or "",
            "delivery_address_line1": self.delivery_addr1.value or "",
            "delivery_address_line2": self.delivery_addr2.value or "",
            "delivery_address_line3": self.delivery_addr3.value or "",
            "delivery_city": self.delivery_city.value or "",
            "delivery_district": self.delivery_district.value or "",
            "delivery_state": self.delivery_state.value or "",
            "delivery_pincode": self.delivery_pincode.value or "",
            "code": self.code.value or "",
            "phone": self.phone.value or "",
            "mobile": self.mobile.value or "",
            "fax": self.fax.value or "",
            "email": self.email.value or "",
            "gstin": self.gstin.value or "",
            "cst_no": self.cst_no.value or "",
            "pan_no": self.pan_no.value or "",
            "courier_name": self.courier_name.value or "",
            "reference": self.reference.value or "",
            "agent_id": self.agent_id.value,
            "transporter_id": self.transporter_id.value,
            "price_list_id": self.price_list_id.value,
            "documents_thro": self.documents_thro.value or "Direct",
            "order_thro": self.order_thro.value or "DIRECT",
            "opening_balance": float(self.opening_balance.value or 0),
            "opn_bal_type": self.opn_bal_type.value or "DEBIT",
            "for_allowed": self.for_allowed.value == "Yes",
            "credit_days": int(self.credit_days.value or 0),
            "credit_limit": float(self.credit_limit.value or 0),
            "price_type": self.price_type.value or "Wholesale",
            "tax_type": self.tax_type.value or "GST",
            "igst_percent": self.igst_percent.value or "0",
            "cgst_percent": self.cgst_percent.value or "0",
            "sgst_percent": self.sgst_percent.value or "0",
            "tcs_percent": self.tcs_percent.value or "0",
            "cess_percent": self.cess_percent.value or "0",
            "gst_percent": self.gst_percent.value or "0",
            "rate_percent": self.gst_percent.value or "0",
            "tcs_applicable": self.tcs_applicable.value,
            "discount_percent": float(self.discount_percent.value or 0),
            "bank_name": self.bank_name.value or "",
            "bank_account_no": self.bank_acc.value or "",
            "bank_ifsc": self.bank_ifsc.value or "",
            "remarks": self.remarks.value or "",
            "is_approved": self.status_radio.value == "Approved",
            "is_blocked": self.status_radio.value == "Blocked",
            "party_type": self.party_type.value or "Both",
        }

    def load_metadata(self, agents, transporters, price_lists, taxes=None):
        self.agent_id.options = [ft.dropdown.Option(key=str(a["id"]), text=a["name"]) for a in agents]
        self.transporter_id.options = [ft.dropdown.Option(key=str(t["id"]), text=t["name"]) for t in transporters]
        self.price_list_id.options = [ft.dropdown.Option(key=str(p["id"]), text=p["list_name"]) for p in price_lists]
        self.all_taxes = taxes or []
        if taxes:
            self.tax_type.options = [ft.dropdown.Option(t["name"]) for t in taxes]
        try:
            self.update()
        except:
            pass

    def on_gst_pct_change(self, e):
        try:
            val = float(self.gst_percent.value or 0)
            t_type = self.tax_type.value or "GST"
            if "GST" in t_type.upper() and "IGST" not in t_type.upper():
                # Standard Split only for GST
                self.cgst_percent.value = str(val / 2)
                self.sgst_percent.value = str(val / 2)
                self.update()
        except: pass

    def on_tax_change(self, e):
        tax_name = self.tax_type.value
        tax = next((t for t in self.all_taxes if t["name"] == tax_name), None)
        if tax:
            self.cgst_percent.value = str(tax.get("cgst_percent", 0))
            self.sgst_percent.value = str(tax.get("sgst_percent", 0))
            self.igst_percent.value = str(tax.get("igst_percent", 0))
            self.tcs_percent.value = str(tax.get("tcs_percent", 0))
            self.cess_percent.value = str(tax.get("cess_percent", 0))
            self.gst_percent.value = str(tax.get("rate_percent", 0))
            self.tax_details.value = f"Type: {tax.get('tax_type')} | Total: {tax.get('rate_percent')}%"
            self.update()

    def set_values(self, data: dict):
        self.name.value = data.get("name", "")
        self.billing_addr1.value = data.get("billing_address_line1", "")
        self.billing_addr2.value = data.get("billing_address_line2", "")
        self.billing_addr3.value = data.get("billing_address_line3", "")
        self.city.value = data.get("billing_city", "")
        self.district.value = data.get("billing_district", "")
        self.state_field.value = data.get("billing_state", "")
        self.pincode.value = data.get("billing_pincode", "")
        self.delivery_addr1.value = data.get("delivery_address_line1", "")
        self.delivery_addr2.value = data.get("delivery_address_line2", "")
        self.delivery_addr3.value = data.get("delivery_address_line3", "")
        self.delivery_city.value = data.get("delivery_city", "")
        self.delivery_district.value = data.get("delivery_district", "")
        self.delivery_state.value = data.get("delivery_state", "")
        self.delivery_pincode.value = data.get("delivery_pincode", "")
        self.code.value = data.get("code", "")
        self.phone.value = data.get("phone", "")
        self.mobile.value = data.get("mobile", "")
        self.fax.value = data.get("fax", "")
        self.email.value = data.get("email", "")
        self.gstin.value = data.get("gstin", "")
        self.cst_no.value = data.get("cst_no", "")
        self.pan_no.value = data.get("pan_no", "")
        self.courier_name.value = data.get("courier_name", "")
        self.reference.value = data.get("reference", "")
        
        if data.get("agent_id"):
            self.agent_id.value = str(data.get("agent_id"))
        if data.get("transporter_id"):
            self.transporter_id.value = str(data.get("transporter_id"))
        if data.get("price_list_id"):
            self.price_list_id.value = str(data.get("price_list_id"))
            
        self.documents_thro.value = data.get("documents_thro", "Direct")
        self.order_thro.value = data.get("order_thro", "DIRECT")
        self.opening_balance.value = str(data.get("opening_balance", 0))
        self.opn_bal_type.value = data.get("opn_bal_type", "DEBIT")
        self.for_allowed.value = "Yes" if data.get("for_allowed", True) else "No"
        self.credit_days.value = str(data.get("credit_days", 0))
        self.credit_limit.value = str(data.get("credit_limit", 0))
        self.price_type.value = data.get("price_type", "Wholesale")
        self.tax_type.value = data.get("tax_type", "GST")
        self.igst_percent.value = str(data.get("igst_percent", 0))
        self.cgst_percent.value = str(data.get("cgst_percent", 0))
        self.sgst_percent.value = str(data.get("sgst_percent", 0))
        self.tcs_percent.value = str(data.get("tcs_percent", 0))
        self.cess_percent.value = str(data.get("cess_percent", 0))
        self.gst_percent.value = str(data.get("gst_percent") or data.get("rate_percent", 0))
        self.tcs_applicable.value = data.get("tcs_applicable", False)
        self.discount_percent.value = str(data.get("discount_percent", 0))
        self.bank_name.value = data.get("bank_name", "")
        self.bank_acc.value = data.get("bank_account_no", "")
        self.bank_ifsc.value = data.get("bank_ifsc", "")
        self.remarks.value = data.get("remarks", "")
        self.party_type.value = data.get("party_type", "Both")
        self.status_radio.value = "Blocked" if data.get("is_blocked", False) else "Approved"
        try:
            if self.page:
                self.update()
        except Exception:
            pass

    def clear(self, e=None):
        self.set_values({"is_approved": True, "is_blocked": False})

    def _submit(self, e):
        if not self.name.value:
            self.name.error_text = "Required"
            try:
                self.update()
            except Exception:
                pass
            return
        self.name.error_text = None
        if self.on_submit:
            self.on_submit(self.get_values())
# =========================================================
# MASTERS SCREEN (Full Tabbed Layout)
# =========================================================
class MastersScreen(ft.Container):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.padding = 20
        self.edit_id = None
        self.current_tab = 0

        self.form_area = ft.Container()
        self.table_area = ft.Container(expand=True)

        # Modal Holder
        self.modal = ft.AlertDialog(
            modal=False,  # Allow clicking outside to close
            title=ft.Row([
                ft.Row([
                    ft.Icon(ft.icons.EDIT_NOTE, color=AppColors.PRIMARY),
                    ft.Text("ENTRY MANAGEMENT", weight="bold", size=16),
                ], spacing=10),
                ft.IconButton(ft.icons.CLOSE, on_click=lambda _: self.close_modal())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            actions_alignment=ft.MainAxisAlignment.END,
            content=ft.Container(self.form_area, width=700, height=600)
        )

        self.tabs = ft.Tabs(
            selected_index=0,
            on_change=self.on_tab_change,
            indicator_color=AppColors.PRIMARY,
            label_color=AppColors.PRIMARY,
            unselected_label_color=AppColors.TEXT_SUB,
            divider_color="#F0F0F0",
            tabs=[
                ft.Tab(text="Items"),
                ft.Tab(text="Price Lists"),
                ft.Tab(text="Parties"),
                ft.Tab(text="Suppliers"),
                ft.Tab(text="Agents"),
                ft.Tab(text="Transporters"),
                ft.Tab(text="Banks"),
                ft.Tab(text="Taxes"),
                ft.Tab(text="Expense Ledger"),
                ft.Tab(text="General Items"),
            ]
        )

        # --- Top Button Bar ---
        self.add_entry_btn = ft.ElevatedButton(
            "Add Entry", 
            icon=ft.icons.ADD_ROUNDED,
            on_click=self.on_add_entry,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=AppColors.PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=25, vertical=15)
            )
        )

        self.content = ft.Column(
            controls=[
                ft.Row([
                    ft.Column([
                        ft.Text("Master Data Management", size=AppStyles.H1_SIZE, weight="bold", color=AppColors.TEXT_HEADER),
                        ft.Text("Define and manage your global infrastructure records.", size=AppStyles.BODY_SIZE, color=AppColors.TEXT_SUB),
                    ]),
                    self.add_entry_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                self.tabs,
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                
                # Full width Table
                self.table_area
            ],
            expand=True
        )

    def did_mount(self):
        if not self.page:
            return
        if self.modal not in self.page.overlay:
            self.page.overlay.append(self.modal)
            self.page.update()
        self.load_tab(0)

    def on_tab_change(self, e):
        self.current_tab = self.tabs.selected_index
        self.edit_id = None
        self.load_tab(self.current_tab)

    def on_add_entry(self, e):
        self.edit_id = None
        self.open_modal()  # Open first to attach to page
        if hasattr(self.form, "clear"):
            self.form.clear()

    def open_modal(self):
        self.modal.open = True
        if self.page:
            self.page.update()

    def close_modal(self):
        self.modal.open = False
        if self.page:
            self.page.update()

    def load_tab(self, idx):
        if not state.company_id:
            return

        loaders = [
            self.load_items, self.load_price_lists, self.load_parties,
            self.load_suppliers, self.load_agents, self.load_transporters, self.load_banks,
            self.load_taxes, self.load_expense_ledgers,
            self.load_general_items,
        ]
        if idx < len(loaders):
            loaders[idx]()

    def _refresh(self):
        if self.page:
            try:
                self.update()
            except Exception:
                pass

    def _confirm_delete(self, message, on_confirm):
        def handle_confirm(e):
            on_confirm()
            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=ft.colors.ORANGE), ft.Text("Confirm Delete")], spacing=10),
            content=ft.Text(message, size=14),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(self.page.dialog, "open", False) or self.page.update()),
                ft.ElevatedButton("Delete Permanently", on_click=handle_confirm, bgcolor=ft.colors.RED_400, color=ft.colors.WHITE),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    # =========================================================
    # 1. ITEMS
    # =========================================================
    def load_items(self):
        self.form = ItemMasterForm(on_submit=self.save_item)
        data = select("items", {"company_id": state.company_id})
        
        brands = sorted(list(set(str(i.get("brand_name")) for i in data if i.get("brand_name"))))
        styles = sorted(list(set(str(i.get("style")) for i in data if i.get("style"))))
        all_sizes_raw = []
        for i in data:
            if isinstance(i.get("sizes"), list):
                all_sizes_raw.extend(i.get("sizes"))
        unique_sizes = sort_sizes(list(set(str(s) for s in all_sizes_raw)))
        taxes = select("taxes", {"company_id": state.company_id})
        self.form.load_metadata(brands, styles, unique_sizes, taxes=taxes)
        
        for item in data:
            stock = item.get("opening_stock", {})
            item["total_stock"] = sum(int(v) for v in stock.values() if str(v).isdigit()) if isinstance(stock, dict) else 0
            item["status_str"] = "Blocked" if item.get("is_blocked") else "Approved"
            item["sizes_str"] = ", ".join(item.get("sizes", [])) if isinstance(item.get("sizes"), list) else ""

        table = TableBuilder(
            [
                {"key": "item_type", "label": "TYPE"},
                {"key": "item_code", "label": "CODE"},
                {"key": "item_name", "label": "ITEM NAME"},
                {"key": "brand_name", "label": "BRAND"},
                {"key": "variety", "label": "VARIETY"},
                {"key": "style", "label": "Style"},
                {"key": "total_stock", "label": "Opn Stock"},
                {"key": "pcs_per_inner_box", "label": "Inner"},
                {"key": "boxes_per_outer_box", "label": "Outer"},
                {"key": "box_type", "label": "Box Type"},
                {"key": "hsn_code", "label": "HSN"},
                {"key": "tax_name", "label": "Tax Slab"},
                {"key": "item_order", "label": "Order"},
                {"key": "status_str", "label": "Status"},
                {"key": "reason", "label": "Reason/Remarks"},
                {"key": "sizes_str", "label": "Sizes"},
            ],
            data, on_edit=self.edit_item, on_delete=self.delete_item
        )
        self.form_area.content = self.form
        self.table_area.content = table
        self._refresh()

    def save_item(self, data):
        data["company_id"] = state.company_id
        try:
            # Duplicate check
            existing = select("items", {"company_id": state.company_id, "item_code": data["item_code"]})
            if existing and (not self.edit_id or str(existing[0]["id"]) != str(self.edit_id)):
                self._snack(f"Error: Item code '{data['item_code']}' already exists!", "red")
                return

            if self.edit_id:
                update("items", data, {"id": self.edit_id})
                self.edit_id = None
            else:
                insert("items", data)
            self.close_modal()
            self.load_items()
            self._snack("Item Saved Successfully", "green")
        except Exception as e:
            self._snack(f"Error: {e}", "red")

    def edit_item(self, row):
        self.edit_id = row["id"]
        self.open_modal()
        self.form.set_values(row)

    def delete_item(self, row):
        item_id = row["id"]
        # Check all transaction tables that reference this item
        ref_tables = [
            ("order_items",              "item_id", "Sales Orders"),
            ("purchase_order_items",     "item_id", "Purchase Orders"),
            ("packing_slip_items",       "item_id", "Packing Slips"),
            ("transport_invoice_items",  "item_id", "Transport Invoices"),
            ("final_invoice_items",      "item_id", "Tax Invoices"),
            ("purchase_invoice_items",   "item_id", "Purchase Invoices"),
            ("stock_ledger",             "item_id", "Stock Ledger"),
        ]
        used_in = []
        for tbl, col, label in ref_tables:
            try:
                rows = select(tbl, {col: item_id})
                if rows:
                    used_in.append(f"{label} ({len(rows)} records)")
            except Exception:
                pass
        if used_in:
            self._snack(f"Cannot delete '{row.get('item_name')}' — used in: {', '.join(used_in)}", "red")
            return
        self._confirm_delete(f"Delete item '{row.get('item_name')}'?", lambda: (delete("items", {"id": item_id}), self.load_items()))

    # =========================================================
    # 2. PRICE LISTS
    # =========================================================
    def load_price_lists(self):
        self.form = PriceListForm(on_submit=self.save_price_list)
        items_data = select("items", {"company_id": state.company_id})
        self.form.load_metadata(items_data)
        data = select("price_lists", {"company_id": state.company_id})
        # Count items for each price list
        items_counts = select("price_list_items", {"company_id": state.company_id})
        count_map = {}
        for x in items_counts:
            pid = str(x["price_list_id"])
            count_map[pid] = count_map.get(pid, 0) + 1
        
        for p in data:
            p["item_count"] = count_map.get(str(p["id"]), 0)

        table = TableBuilder(
            [
                {"key": "list_name", "label": "List Name"},
                {"key": "effective_date", "label": "Date"},
                {"key": "price_type", "label": "Type"},
                {"key": "item_count", "label": "No. of Items"},
            ],
            data, on_edit=self.edit_price_list, on_delete=self.delete_price_list
        )
        self.form_area.content = self.form
        self.table_area.content = table
        self._refresh()

    def save_price_list(self, data):
        list_name = data.get("list_name", "").strip()
        if not list_name:
            self._snack("Price List name is required!", "red")
            return

        list_header = {"company_id": state.company_id, "list_name": list_name, "effective_date": data.get("effective_date"), "price_type": data.get("price_type")}
        items_pricing = data.get("items_pricing", {})
        try:
            # Duplicate name check
            is_cloning = data.get("is_clone", False)
            existing = select("price_lists", {"company_id": state.company_id, "list_name": list_name})
            if existing:
                existing_id = str(existing[0]["id"])
                # Allow if editing the same record (not cloning)
                if not (self.edit_id and not is_cloning and existing_id == str(self.edit_id)):
                    self._snack(f"Error: Price List '{list_name}' already exists!", "red")
                    return

            if self.edit_id and not is_cloning:
                update("price_lists", list_header, {"id": self.edit_id})
                price_list_id, self.edit_id = self.edit_id, None
            else:
                res = insert("price_lists", list_header)
                price_list_id = res[0]["id"]
            delete("price_list_items", {"price_list_id": price_list_id})
            for item_id, sizes_dict in items_pricing.items():
                for size_val, rates in sizes_dict.items():
                    insert("price_list_items", {"company_id": state.company_id, "price_list_id": price_list_id, "item_id": item_id, "size_value": size_val, **rates})
            self.close_modal()
            self.load_price_lists()
            self._snack("Price List Saved Successfully", "green")
        except Exception as e:
            self._snack(f"Error: {e}", "red")

    def edit_price_list(self, row):
        self.edit_id = row["id"]
        db_items = select("price_list_items", {"price_list_id": self.edit_id})
        pricing_state = {}
        for x in db_items:
            i_id = x["item_id"]
            if i_id not in pricing_state: pricing_state[i_id] = {}
            pricing_state[i_id][x["size_value"]] = {"wholesale_rate": x["wholesale_rate"], "retail_rate": x["retail_rate"], "mrp_rate": x["mrp_rate"]}
        
        self.open_modal()
        self.form.set_values(row, pricing_state)

    def delete_price_list(self, row):
        pl_id = row["id"]
        # Check if any orders or parties reference this price list
        ref_tables = [
            ("orders",           "price_list_id", "Sales Orders"),
            ("parties",          "price_list_id", "Parties"),
        ]
        used_in = []
        for tbl, col, label in ref_tables:
            try:
                rows = select(tbl, {col: pl_id})
                if rows:
                    used_in.append(f"{label} ({len(rows)} records)")
            except Exception:
                pass
        if used_in:
            self._snack(f"Cannot delete '{row.get('list_name')}' — used in: {', '.join(used_in)}", "red")
            return
        self._confirm_delete(f"Delete price list '{row.get('list_name')}'?", lambda: (delete("price_lists", {"id": pl_id}), self.load_price_lists()))

    # =========================================================
    # 3. PARTIES
    # =========================================================
    def load_parties(self):
        self.form = PartyMasterForm(on_submit=self.save_party)
        self.form.load_metadata(
            select("agents", {"company_id": state.company_id}), 
            select("transporters", {"company_id": state.company_id}), 
            select("price_lists", {"company_id": state.company_id}),
            select("taxes", {"company_id": state.company_id})
        )
        data = select("parties", {"company_id": state.company_id})
        # Resolve Agent/Transporter/PriceList names for the table
        agents = select("agents", {"company_id": state.company_id})
        transporters = select("transporters", {"company_id": state.company_id})
        price_lists = select("price_lists", {"company_id": state.company_id})
        
        agent_map = {str(a["id"]): a["name"] for a in agents}
        trans_map = {str(t["id"]): t["name"] for t in transporters}
        plist_map = {str(p["id"]): p["list_name"] for p in price_lists}
        
        for p in data:
            p["agent_name"] = agent_map.get(str(p.get("agent_id")), "-")
            p["transporter_name"] = trans_map.get(str(p.get("transporter_id")), "-")
            p["price_list_name"] = plist_map.get(str(p.get("price_list_id")), "-")
            # Combined discount display
            p["discounts"] = f"{p.get('discount_percent', 0)}%"
            p["full_billing"] = f"{p.get('billing_address_line1','')}, {p.get('billing_address_line2','')}, {p.get('billing_address_line3','')}, {p.get('billing_city','')}, {p.get('billing_state','')}"
            p["full_delivery"] = f"{p.get('delivery_address_line1','')}, {p.get('delivery_address_line2','')}, {p.get('delivery_address_line3','')}, {p.get('delivery_city','')}, {p.get('delivery_state','')}"
            p["status_str"] = "Blocked" if p.get("is_blocked") else "Approved"
            p["for_str"] = "Yes" if p.get("for_allowed") else "No"
            p["tcs_str"] = "Yes" if p.get("tcs_applicable") else "No"
            p["opn_bal_display"] = f"{p.get('opening_balance',0)} ({p.get('opn_bal_type','DEBIT')})"

        table = TableBuilder(
            [
                {"key": "party_type", "label": "TYPE"},
                {"key": "code", "label": "CODE"},
                {"key": "name", "label": "PARTY NAME"},
                {"key": "agent_name", "label": "AGENT"},
                {"key": "mobile", "label": "MOBILE"},
                {"key": "phone", "label": "PHONE"},
                {"key": "email", "label": "Email"},
                {"key": "contact_person", "label": "Contact Person"},
                {"key": "full_billing", "label": "Billing Address"},
                {"key": "full_delivery", "label": "Delivery Address"},
                {"key": "gstin", "label": "GSTIN"},
                {"key": "pan_no", "label": "PAN"},
                {"key": "cst_no", "label": "CST"},
                {"key": "transporter_name", "label": "Transporter"},
                {"key": "destination", "label": "Destination"},
                {"key": "courier_name", "label": "Courier"},
                {"key": "price_list_name", "label": "Price List"},
                {"key": "price_type", "label": "Price Type"},
                {"key": "opn_bal_display", "label": "Opn Balance"},
                {"key": "credit_days", "label": "Cr. Days"},
                {"key": "credit_limit", "label": "Cr. Limit"},
                {"key": "discounts", "label": "Discounts (%)"},
                {"key": "tax_type", "label": "Tax Type"},
                {"key": "gst_percent", "label": "GST %"},
                {"key": "igst_percent", "label": "IGST %"},
                {"key": "tcs_str", "label": "TCS"},
                {"key": "bank_name", "label": "Bank"},
                {"key": "bank_account_no", "label": "Account"},
                {"key": "bank_ifsc", "label": "IFSC"},
                {"key": "status_str", "label": "Status"},
                {"key": "remarks", "label": "Remarks"},
            ],
            data, on_edit=self.edit_party, on_delete=self.delete_party
        )
        self.form_area.content = self.form
        self.table_area.content = table
        self._refresh()

    def save_party(self, data):
        data["company_id"] = state.company_id
        try:
            # Duplicate check
            if data.get("code"):
                existing = select("parties", {"company_id": state.company_id, "code": data["code"]})
                if existing and (not self.edit_id or str(existing[0]["id"]) != str(self.edit_id)):
                    self._snack(f"Error: Party code '{data['code']}' already exists!", "red")
                    return

            if self.edit_id:
                update("parties", data, {"id": self.edit_id})
                self.edit_id = None
            else:
                insert("parties", data)
            self.close_modal()
            self.load_parties()
            self._snack("Party Saved Successfully", "green")
        except Exception as e:
            self._snack(f"Error: {e}", "red")

    def _snack(self, msg, color):
        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.page.snack_bar.open = True
            self.page.update()

    def edit_party(self, row):
        self.edit_id = row["id"]
        self.open_modal()
        self.form.set_values(row)

    def delete_party(self, row):
        party_id = row["id"]
        # Check if any transactions reference this party
        ref_tables = [
            ("orders",              "party_id",    "Sales Orders"),
            ("purchase_orders",     "supplier_id", "Purchase Orders"),
            ("packing_slips",       "party_id",    "Packing Slips"),
            ("transport_invoices",  "party_id",    "Transport Invoices"),
            ("final_invoices",      "party_id",    "Tax Invoices"),
            ("ledger_entries",      "account_id",  "Ledger Entries"),
        ]
        used_in = []
        for tbl, col, label in ref_tables:
            try:
                rows = select(tbl, {col: party_id})
                if rows:
                    used_in.append(f"{label} ({len(rows)} records)")
            except Exception:
                pass
        if used_in:
            self._snack(f"Cannot delete '{row.get('name')}' — used in: {', '.join(used_in)}", "red")
            return
        self._confirm_delete(f"Delete party '{row.get('name')}'?", lambda: (delete("parties", {"id": party_id}), self.load_parties()))

    # =========================================================
    # GENERIC MASTERS
    # =========================================================
    def _generic_loader(self, table_name, fields, cols, save_fn):
        self.form = FormBuilder(fields, on_submit=save_fn)
        data = select(table_name, {"company_id": state.company_id})
        table = TableBuilder(cols, data, on_edit=lambda r: self._generic_edit(r), on_delete=lambda r: self._generic_delete(table_name, r))
        self.form_area.content, self.table_area.content, self.curr_table = self.form, table, table_name
        self._refresh()

    def _generic_edit(self, row):
        self.edit_id = row["id"]
        self.open_modal()
        if hasattr(self.form, "set_values"): self.form.set_values(row)

    def _generic_delete(self, table, row):
        item_id = row["id"]
        item_name = row.get('name') or row.get('item_name') or "this entry"
        
        # Check dependencies based on table type
        dependency_map = {
            "agents": [
                ("parties", "agent_id", "Parties"),
                ("orders", "agent_id", "Sales Orders"),
                ("purchase_orders", "agent_id", "Purchase Orders"),
            ],
            "transporters": [
                ("parties", "transporter_id", "Parties"),
                ("orders", "transporter_id", "Sales Orders"),
                ("purchase_orders", "transporter_id", "Purchase Orders"),
                ("transport_invoices", "transporter_id", "Transport Invoices"),
            ],
            "banks": [
                ("parties", "bank_name", "Parties (Bank Name Match)"), # some use bank_name text
                ("payment_vouchers", "bank_id", "Payment Vouchers"),
                ("receipt_vouchers", "bank_id", "Receipt Vouchers"),
            ],
            "taxes": [
                ("items", "tax_name", "Items (Tax Slab)"),
                ("general_items", "tax_id", "General Items"),
                ("parties", "tax_type", "Parties"),
                ("orders", "tax_type", "Sales Orders"),
            ],
            "staff": [
                ("vouchers", "staff_id", "Vouchers"), # if applicable
            ],
            "expense_ledgers": [
                ("ledger_entries", "account_id", "Ledger Entries"),
            ],
            "general_items": [
                ("ledger_entries", "ref_id", "Transactions"), # General items might be used in expense entries
            ]
        }

        if table in dependency_map:
            used_in = []
            for ref_tbl, ref_col, label in dependency_map[table]:
                try:
                    # For some tables we check UUID, for others we might check Name (e.g. tax_name in items)
                    # We'll try to match by ID first, then by name if the column name implies it
                    val_to_match = item_id
                    if ref_col.endswith("_name") or ref_col == "tax_type":
                        val_to_match = row.get("name") or row.get("item_name")
                    
                    if not val_to_match: continue
                    
                    rows = select(ref_tbl, {ref_col: val_to_match})
                    if rows:
                        used_in.append(f"{label} ({len(rows)} records)")
                except Exception:
                    pass
            
            if used_in:
                self._snack(f"Cannot delete '{item_name}' — used in: {', '.join(used_in)}", "red")
                return

        self._confirm_delete(f"Delete entry '{item_name}'?", lambda: (delete(table, {"id": row["id"]}), self.load_tab(self.current_tab)))

    def load_agents(self):
        self._generic_loader("agents", 
                             [{"name": "name", "label": "Name *", "required": True}, {"name": "address", "label": "Address"}, {"name": "gstin", "label": "GSTIN"}, {"name": "bank_name", "label": "Bank"}, {"name": "bank_account", "label": "Account"}, {"name": "bank_ifsc", "label": "IFSC"}, {"name": "commission_percent", "label": "Comm %", "type": "number"}],
                             [{"key": "name", "label": "Name"}, {"key": "address", "label": "Address"}, {"key": "gstin", "label": "GSTIN"}, {"key": "commission_percent", "label": "Comm. %"}, {"key": "bank_name", "label": "Bank Name"}, {"key": "bank_account", "label": "Account No"}, {"key": "bank_ifsc", "label": "IFSC"}], 
                             self.save_agent)
    def save_agent(self, data):
        data["company_id"] = state.company_id
        (update("agents", data, {"id": self.edit_id}) and setattr(self, "edit_id", None)) if self.edit_id else insert("agents", data)
        self.close_modal(); self.load_agents()

    def load_transporters(self):
        self._generic_loader("transporters", 
                             [{"name": "name", "label": "Name *", "required": True}, {"name": "address", "label": "Address"}, {"name": "gstin", "label": "GSTIN"}],
                             [{"key": "name", "label": "Name"}, {"key": "address", "label": "Address"}, {"key": "gstin", "label": "GSTIN"}], 
                             self.save_transporter)
    def save_transporter(self, data):
        data["company_id"] = state.company_id
        (update("transporters", data, {"id": self.edit_id}) and setattr(self, "edit_id", None)) if self.edit_id else insert("transporters", data)
        self.close_modal(); self.load_transporters()

    def load_banks(self):
        self._generic_loader("banks", 
                             [
                                 {"name": "name",           "label": "Bank Name *", "required": True}, 
                                 {"name": "account_holder", "label": "Account Holder Name"},
                                 {"name": "account_no",     "label": "Account No"}, 
                                 {"name": "ifsc_code",      "label": "IFSC"}, 
                                 {"name": "branch",         "label": "Branch"},
                                 {"name": "opening_balance","label": "Opening Balance", "type": "number", "default": "0"}
                             ],
                             [
                                 {"key": "name",           "label": "Bank Name"}, 
                                 {"key": "account_no",     "label": "Account No"}, 
                                 {"key": "account_holder", "label": "Holder Name"},
                                 {"key": "opening_balance","label": "Opn. Bal"},
                                 {"key": "ifsc_code",      "label": "IFSC"}, 
                                 {"key": "branch",         "label": "Branch"}
                             ], 
                             self.save_bank)
    def save_bank(self, data):
        data["company_id"] = state.company_id
        try: data["opening_balance"] = float(data.get("opening_balance") or 0)
        except: data["opening_balance"] = 0.0
        (update("banks", data, {"id": self.edit_id}) and setattr(self, "edit_id", None)) if self.edit_id else insert("banks", data)
        self.close_modal(); self.load_banks()

    def load_taxes(self):
        self._generic_loader(
            "taxes",
            [
                {"name": "name",        "label": "Tax Name *",  "required": True},
                {"name": "hsn_code",    "label": "HSN / SAC Code"},
                {"name": "tax_type",    "label": "Tax Type",    "type": "dropdown",
                 "options": [{"value": "GST", "label": "GST"}, {"value": "IGST", "label": "IGST"},
                             {"value": "TCS", "label": "TCS"},  {"value": "Exempt", "label": "Exempt"}]},
                {"name": "rate_percent",  "label": "Total Tax Rate %", "type": "number", "default": "0",
                 "on_change": self._on_tax_rate_split_change},
                {"name": "cgst_percent",  "label": "CGST %",   "type": "number", "default": "0"},
                {"name": "sgst_percent",  "label": "SGST %",   "type": "number", "default": "0"},
                {"name": "igst_percent",  "label": "IGST %",   "type": "number", "default": "0"},
                {"name": "tcs_percent",   "label": "TCS %",    "type": "number", "default": "0"},
                {"name": "cess_percent",  "label": "CESS %",   "type": "number", "default": "0"},
            ],
            [
                {"key": "name",        "label": "Tax Name"},
                {"key": "hsn_code",    "label": "HSN/SAC"},
                {"key": "tax_type",    "label": "Type"},
                {"key": "cgst_percent","label": "CGST %"},
                {"key": "sgst_percent","label": "SGST %"},
                {"key": "igst_percent","label": "IGST %"},
                {"key": "tcs_percent", "label": "TCS %"},
                {"key": "cess_percent","label": "CESS %"},
                {"key": "rate_percent","label": "Total Rate %"},
            ],
            self.save_tax
        )
    
    def _on_tax_rate_split_change(self, e):
        try:
            val = float(e.control.value or 0)
            t_type = self.form.controls_map.get("tax_type").value
            
            if t_type == "GST":
                self.form.controls_map["cgst_percent"].value = str(val / 2)
                self.form.controls_map["sgst_percent"].value = str(val / 2)
                self.form.controls_map["igst_percent"].value = "0"
            
            self.form.update()
        except Exception as ex:
            print(f"Tax split error: {ex}")

    def save_tax(self, data):
        data["company_id"] = state.company_id
        for pct_field in ["cgst_percent", "sgst_percent", "igst_percent", "tcs_percent", "cess_percent", "rate_percent"]:
            try: data[pct_field] = float(data.get(pct_field) or 0)
            except: data[pct_field] = 0.0
        (update("taxes", data, {"id": self.edit_id}) and setattr(self, "edit_id", None)) if self.edit_id else insert("taxes", data)
        self.close_modal(); self.load_taxes()

    def load_suppliers(self):
        """Load suppliers — reuses Party Master form but filters for Supplier-type parties."""
        self.form = PartyMasterForm(on_submit=self.save_supplier)
        self.form.load_metadata(
            select("agents", {"company_id": state.company_id}), 
            select("transporters", {"company_id": state.company_id}), 
            select("price_lists", {"company_id": state.company_id}),
            select("taxes", {"company_id": state.company_id})
        )
        # Pre-set party type to Supplier
        self.form.party_type.value = "Supplier"
        
        all_parties = select("parties", {"company_id": state.company_id})
        data = [p for p in all_parties if p.get("party_type") in ("Supplier", "Both")]
        for p in data:
            p["full_billing"] = f"{p.get('billing_address_line1','')}, {p.get('billing_city','')}, {p.get('billing_state','')}"
            p["status_str"] = "Blocked" if p.get("is_blocked") else "Approved"

        table = TableBuilder(
            [
                {"key": "code", "label": "CODE"},
                {"key": "name", "label": "SUPPLIER NAME"},
                {"key": "mobile", "label": "MOBILE"},
                {"key": "email", "label": "Email"},
                {"key": "full_billing", "label": "Address"},
                {"key": "gstin", "label": "GSTIN"},
                {"key": "pan_no", "label": "PAN"},
                {"key": "bank_name", "label": "Bank"},
                {"key": "bank_account_no", "label": "Account"},
                {"key": "status_str", "label": "Status"},
            ],
            data, on_edit=self.edit_party, on_delete=self.delete_party
        )
        self.form_area.content = self.form
        self.table_area.content = table
        self._refresh()

    def save_supplier(self, data):
        data["company_id"] = state.company_id
        if not data.get("party_type"):
            data["party_type"] = "Supplier"
        try:
            if self.edit_id:
                update("parties", data, {"id": self.edit_id})
                self.edit_id = None
            else:
                insert("parties", data)
            self.close_modal()
            self.load_suppliers()
            self._snack("Supplier Saved Successfully", "green")
        except Exception as e:
            self._snack(f"Error: {e}", "red")

    def load_expense_ledgers(self):
        self._generic_loader(
            "expense_ledgers",
            [
                {"name": "name",         "label": "Ledger Name *", "required": True},
                {"name": "account_code",  "label": "Account Code"},
                {"name": "group_name",    "label": "Accounting Group", "type": "dropdown", "default": "Indirect Expenses",
                 "options": [
                     {"value": "Indirect Expenses", "label": "Indirect Expenses (Rent, Tea, etc.)"},
                     {"value": "Direct Expenses",   "label": "Direct Expenses (Freight, Wages)"},
                     {"value": "Fixed Assets",      "label": "Fixed Assets (Furniture, Machinery)"},
                     {"value": "Indirect Incomes",  "label": "Indirect Incomes (Interest, etc.)"},
                     {"value": "Current Assets",    "label": "Current Assets (Deposits)"},
                     {"value": "Loans & Liabilities","label": "Loans & Liabilities"}
                 ]},
                {"name": "hsn_sac",       "label": "HSN/SAC Code"},
                {"name": "description",   "label": "Description"},
            ],
            [
                {"key": "name",        "label": "Ledger Name"},
                {"key": "group_name",  "label": "Group"},
                {"key": "account_code","label": "Code"},
                {"key": "hsn_sac",     "label": "HSN/SAC"},
            ],
            self.save_ledger
        )
    def save_ledger(self, data):
        data["company_id"] = state.company_id
        (update("expense_ledgers", data, {"id": self.edit_id}) and setattr(self, "edit_id", None)) if self.edit_id else insert("expense_ledgers", data)
        self.close_modal(); self.load_expense_ledgers()

    def load_general_items(self):
        taxes = select("taxes", {"company_id": state.company_id})

        def on_tax_change(e):
            tid = e.control.value
            tax = next((t for t in taxes if str(t["id"]) == tid), None)
            if tax:
                info_ctrl = self.form.controls_map.get("tax_info")
                hsn_ctrl = self.form.controls_map.get("hsn_code")
                if info_ctrl:
                    info_ctrl.value = f"{tax.get('tax_type')} | C:{tax.get('cgst_percent')}% S:{tax.get('sgst_percent')}% I:{tax.get('igst_percent',0)}%"
                    info_ctrl.update()
                if hsn_ctrl and not hsn_ctrl.value and tax.get("hsn_code"):
                    hsn_ctrl.value = tax["hsn_code"]
                    hsn_ctrl.update()

        self.form = FormBuilder([
            {"name": "item_code", "label": "Code"},
            {"name": "item_name", "label": "Name *", "required": True},
            {"name": "uom",       "label": "UOM", "type": "dropdown",
             "options": [{"value": k, "label": k} for k in ["Pcs", "Box", "Kg", "Meter", "Litre", "Set", "Pair"]]},
            {"name": "hsn_code",  "label": "HSN / SAC Code"},
            {"name": "tax_id",    "label": "Tax Slab", "type": "dropdown", "on_change": on_tax_change,
             "options": [{"value": str(t["id"]), "label": t["name"]} for t in taxes]},
            {"name": "tax_info",  "label": "", "type": "info"}
        ], on_submit=self.save_general_item)
        
        data = select("general_items", {"company_id": state.company_id})
        tax_map = {str(t["id"]): t["name"] for t in taxes}
        for item in data:
            item["tax_name"] = tax_map.get(str(item.get("tax_id")), "-")

        table = TableBuilder([
            {"key": "item_code", "label": "Code"},
            {"key": "item_name", "label": "Name"},
            {"key": "uom",       "label": "UOM"},
            {"key": "hsn_code",  "label": "HSN"},
            {"key": "tax_name",  "label": "Tax Slab"},
        ], data, on_edit=self._generic_edit, on_delete=lambda r: self._generic_delete("general_items", r))
        
        self.form_area.content, self.table_area.content = self.form, table
        self._refresh()

    def save_general_item(self, data):
        data["company_id"] = state.company_id
        (update("general_items", data, {"id": self.edit_id}) and setattr(self, "edit_id", None)) if self.edit_id else insert("general_items", data)
        self.close_modal(); self.load_general_items()
