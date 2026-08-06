import flet as ft
import uuid
import json
import math
from datetime import date
from core.state import state
from core.theme import AppColors, AppStyles
from database.db import select, insert, update, delete, get_next_doc_no
from components.size_matrix import sort_sizes
from core.pdf_gen import pdf_engine, print_pdf
import os

class OrderEntryTab(ft.Column):
    """
    Order Entry Screen — Two-panel split layout:
    ├── header_card           ← always visible, 3 rows
    ├── body_row (expand)     ← left panel (item list) + right panel (size grid)
    └── footer_container      ← always visible totals/actions
    """

    def __init__(self):
        super().__init__()
        self.expand  = True
        self.spacing = 0

        # --- Data ---
        self.order_items          = []
        self.all_items_metadata   = {}
        self.current_edit_id      = None
        self.selected_item_index  = 0   # which item is shown in right panel

        # SIZES setup
        self.SIZES = []

        S = AppStyles.get_input_style()

        # ── Header controls ───────────────────────────────────
        self.order_no   = ft.TextField(label="Order No", width=120, **S)
        self.order_date = ft.TextField(label="Order Date", width=140, **S)

        self.party_dd       = ft.Dropdown(label="Select Party *", options=[], on_change=self.on_party_change, width=260, **S)
        self.agent_dd       = ft.Dropdown(label="Agent", width=160, **S)
        self.transporter_dd = ft.Dropdown(label="Transporter", width=175, **S)
        self.destination    = ft.Dropdown(label="Delivery Address", width=200, **S)
        self.price_list_dd  = ft.Dropdown(label="Price List", options=[], width=170, on_change=self.on_price_type_change, **S)
        self.price_type_dd  = ft.Dropdown(label="Price Type", value="NET", options=[ft.dropdown.Option("NET"), ft.dropdown.Option("GROSS"), ft.dropdown.Option("Wholesale")], width=120, on_change=self.on_price_type_change, **S)

        self.order_by       = ft.TextField(label="Order By", width=120, **S)
        self.order_thro     = ft.Dropdown(label="Order Thro'", value="DIRECT", options=[ft.dropdown.Option("DIRECT"), ft.dropdown.Option("AGENT")], width=120, **S)
        self.party_order_no = ft.TextField(label="Party Order No", width=140, **S)
        self.party_order_dt = ft.TextField(label="Party Order Dt", width=135, **S)
        self.remarks        = ft.TextField(label="Remarks", width=220, **S)
        self.no_of_cases    = ft.TextField(label="No Of Cases", value="1", width=95, **S)
        self.qty_type       = ft.Dropdown(label="Qty Type", value="Pieces", options=[ft.dropdown.Option("Pieces"), ft.dropdown.Option("Boxes")], width=100, on_change=self.on_qty_type_change, **S)
        self.docs_by        = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="Direct", label="Direct"), ft.Radio(value="Bank", label="Bank")], spacing=8),
            value="Direct"
        )

        # Party-level tax rates
        self._party_gst_rate  = 5.0
        self._party_tax_type  = "GST"
        self._party_tcs_rate  = 0.0
        self._party_cess_rate = 0.0
        self._party_cgst_rate = 0.0
        self._party_sgst_rate = 0.0
        self._party_igst_rate = 0.0
        self._party_tcs_appl  = False

        # ── Footer controls ───────────────────────────────────
        self.no_of_items_lbl = ft.Text("Items: 0", size=12, weight="bold", color=AppColors.TEXT_SUB)
        self.total_pcs    = ft.Text("Pcs: 0",   size=12, weight="bold", color=AppColors.TEXT_HEADER)
        self.total_boxes  = ft.Text("Boxes: 0", size=12, weight="bold", color=AppColors.TEXT_HEADER)
        self.total_units  = ft.Text("Units: 0", size=12, weight="bold", color=AppColors.TEXT_HEADER)

        self.taxable_value = ft.Text("Taxable: ₹0.00", size=13, weight="bold", color=AppColors.TEXT_HEADER)

        self.tax_type_dd = ft.Dropdown(
            label="Tax Type", value="GST",
            options=[ft.dropdown.Option("GST"), ft.dropdown.Option("IGST")],
            width=110, on_change=self.on_calc_change, **S
        )
        self.gst_rate_tf  = ft.TextField(label="GST %",  value="0", width=75, on_change=self.on_calc_change, **S)
        self.cgst_rate_tf = ft.TextField(label="CGST %", value="0", width=75, on_change=self.on_calc_change, **S)
        self.sgst_rate_tf = ft.TextField(label="SGST %", value="0", width=75, on_change=self.on_calc_change, **S)
        self.igst_rate_tf = ft.TextField(label="IGST %", value="0", width=75, visible=False, on_change=self.on_calc_change, **S)
        self.cess_rate_tf = ft.TextField(label="Cess %", value="0", width=75, on_change=self.on_calc_change, **S)
        self.tcs_rate_tf  = ft.TextField(label="TCS %",  value="0", width=75, on_change=self.on_calc_change, **S)
        self.gst_amount   = ft.Text("GST: ₹0.00", size=12, color=AppColors.TEXT_SUB)

        self.discount_percent = ft.TextField(label="Discount %", value="0", width=90, on_change=self.on_calc_change, **S)
        self.discount_amount_lbl = ft.Text("₹0.00", size=10, color=AppColors.TEXT_SUB)
        
        self.discount_row = ft.Row([
            ft.Column([self.discount_percent, self.discount_amount_lbl], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        ], spacing=12, wrap=True)

        self.cgst_amt_lbl = ft.Text("₹0.00", size=10, color=AppColors.TEXT_SUB)
        self.sgst_amt_lbl = ft.Text("₹0.00", size=10, color=AppColors.TEXT_SUB)
        self.igst_amt_lbl = ft.Text("₹0.00", size=10, color=AppColors.TEXT_SUB)
        self.cess_amt_lbl = ft.Text("₹0.00", size=10, color=AppColors.TEXT_SUB)
        self.tcs_amt_lbl  = ft.Text("₹0.00", size=10, color=AppColors.TEXT_SUB)

        self.cgst_col = ft.Column([self.cgst_rate_tf, self.cgst_amt_lbl], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.sgst_col = ft.Column([self.sgst_rate_tf, self.sgst_amt_lbl], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.igst_col = ft.Column([self.igst_rate_tf, self.igst_amt_lbl], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)

        self.round_off    = ft.TextField(label="Round Off", value="0.00", width=90, on_change=self.on_calc_change, **S)
        self.gross_amount = ft.Text("₹0.00", size=26, weight="bold", color=AppColors.PRIMARY)

        # ── Two-panel split containers ─────────────────────────
        self.left_panel  = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)
        self.right_panel = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)

        self.body_row = ft.Row(
            [self._build_left_panel_wrapper(), self._build_right_panel_wrapper()],
            expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START
        )

        self.controls = [
            self._build_header(),
            ft.Divider(height=1, color="#E2E8F0"),
            self.body_row,
            ft.Divider(height=1, color="#E2E8F0"),
            self._build_footer(),
        ]



    def _build_header(self):
        """3-row always-visible header + action bar."""
        def sep():
            return ft.Container(width=1, height=36, bgcolor="#E2E8F0")

        action_bar = ft.Container(
            bgcolor="#F1F5F9",
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row([
                ft.OutlinedButton(
                    "View History", icon=ft.icons.HISTORY_ROUNDED,
                    on_click=self.show_history_modal,
                    style=ft.ButtonStyle(color=AppColors.PRIMARY, padding=ft.padding.symmetric(horizontal=14, vertical=10))
                ),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    "Clear All", icon=ft.icons.DELETE_SWEEP_OUTLINED,
                    on_click=self.clear_form,
                    style=ft.ButtonStyle(color=AppColors.DANGER, padding=ft.padding.symmetric(horizontal=14, vertical=10))
                ),
                ft.ElevatedButton(
                    "Save Order", icon=ft.icons.SAVE_ALT_ROUNDED,
                    on_click=self.save_order,
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor={ft.MaterialState.DEFAULT: AppColors.SUCCESS, ft.MaterialState.HOVERED: "#16A34A"},
                        shape=ft.RoundedRectangleBorder(radius=8),
                        elevation=2,
                        padding=ft.padding.symmetric(horizontal=18, vertical=10),
                    )
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        return ft.Container(
            bgcolor=ft.colors.WHITE,
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
            shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.with_opacity(0.06, "black"), offset=ft.Offset(0, 2)),
            content=ft.Column([
                # Row 1: Title + Order No/Date
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.icons.RECEIPT_LONG_ROUNDED, color=AppColors.PRIMARY, size=22),
                        ft.Text("Order Entry", size=20, weight="bold", color=AppColors.TEXT_HEADER),
                    ], spacing=8),
                    ft.Container(expand=True),
                    self.order_no,
                    self.order_date,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

                ft.Divider(height=1, color="#F1F5F9"),

                # Row 2: Party, Agent, Transporter, Destination, Price List, Price Type
                ft.Row([
                    self.party_dd,
                    sep(),
                    self.agent_dd,
                    sep(),
                    self.transporter_dd,
                    sep(),
                    self.destination,
                    sep(),
                    self.price_list_dd,
                    self.price_type_dd,
                ], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),

                # Row 3: Secondary fields
                ft.Row([
                    self.order_by,
                    self.order_thro,
                    self.party_order_no,
                    self.party_order_dt,
                    self.remarks,
                    self.no_of_cases,
                    self.qty_type,
                    ft.Column([
                        ft.Text("Docs By", size=10, color=AppColors.TEXT_MUTED),
                        self.docs_by
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.START),
                ], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),

                # Row 4: Action bar
                action_bar,

            ], spacing=10)
        )

    def _build_left_panel_wrapper(self):
        """Left panel container that holds self.left_panel (item list)."""
        return ft.Container(
            bgcolor=ft.colors.WHITE,
            border=ft.border.only(right=ft.border.BorderSide(1, "#E2E8F0")),
            padding=ft.padding.all(10),
            content=self.left_panel,
            expand=40,
        )

    def _build_right_panel_wrapper(self):
        """Right panel container that holds self.right_panel (size grid)."""
        return ft.Container(
            expand=60,
            bgcolor=AppColors.BG_MAIN,
            padding=ft.padding.all(12),
            content=self.right_panel,
        )



    def _build_footer(self):
        def vdiv():
            return ft.VerticalDivider(width=1, color="#E2E8F0")

        def stat_chip(label, ctrl):
            return ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                bgcolor="#F8F9FD",
                border_radius=8,
                border=ft.border.all(1, "#E2E8F0"),
                content=ft.Column([
                    ft.Text(label, size=10, color=AppColors.TEXT_MUTED),
                    ctrl
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

        def disc_col(field, amt_lbl):
            return ft.Column([field, amt_lbl], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        return ft.Container(
            bgcolor=ft.colors.WHITE,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border=ft.border.only(top=ft.border.BorderSide(1, "#E2E8F0")),
            content=ft.Column([
                # Row 1: Stats + Discounts
                ft.Row([
                    # Left: summary stats
                    ft.Row([
                        stat_chip("Items", self.no_of_items_lbl),
                        stat_chip("Pcs", self.total_pcs),
                        stat_chip("Boxes", self.total_boxes),
                        stat_chip("Taxable", self.taxable_value),
                    ], spacing=8),
                    ft.Container(expand=True),
                    # Right: discount columns
                    self.discount_row,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

                ft.Divider(height=1, color="#F1F5F9"),

                # Row 2: Tax + Grand Total
                ft.Row([
                    # Tax group
                    ft.Row([
                        self.tax_type_dd,
                        self.gst_rate_tf,
                        vdiv(),
                        self.cgst_col,
                        self.sgst_col,
                        self.igst_col,
                        vdiv(),
                        ft.Column([self.cess_rate_tf, self.cess_amt_lbl], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Column([self.tcs_rate_tf,  self.tcs_amt_lbl],  spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        self.gst_amount,
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),

                    ft.Container(expand=True),

                    # Round off
                    ft.Row([
                        ft.Column([
                            ft.Text("Round Off", size=10, color=AppColors.TEXT_MUTED),
                            self.round_off
                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.IconButton(ft.icons.REFRESH_ROUNDED, on_click=lambda _: self.load_metadata(),
                                      tooltip="Refresh Metadata", icon_size=16, icon_color=AppColors.TEXT_MUTED),
                    ], spacing=4),

                    vdiv(),

                    # Grand Total
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=16, vertical=8),
                        bgcolor=AppColors.PRIMARY_LIGHT,
                        border_radius=10,
                        content=ft.Column([
                            ft.Text("Grand Total", size=11, color=AppColors.PRIMARY, weight="w600"),
                            self.gross_amount,
                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            ], spacing=8),
        )

    # ─────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────
    def did_mount(self):
        self.load_metadata()

    def load_metadata(self):
        if not state.company_id:
            return
        items = select("items", {"company_id": state.company_id, "item_type": ["Sales", "Both"]})
        self.all_items_metadata = {str(i["id"]): i for i in items}

        parties      = select("parties",      {"company_id": state.company_id, "party_type": ["Customer", "Both"]})
        transporters = select("transporters", {"company_id": state.company_id})
        price_lists  = select("price_lists",  {"company_id": state.company_id})
        agents       = select("agents",       {"company_id": state.company_id})

        self.party_dd.options       = [ft.dropdown.Option(key=str(p["id"]), text=p["name"])      for p in parties]
        self.transporter_dd.options = [ft.dropdown.Option(key=str(t["id"]), text=t["name"])      for t in transporters]
        self.price_list_dd.options  = [ft.dropdown.Option(key=str(p["id"]), text=p["list_name"]) for p in price_lists]
        self.agent_dd.options       = [ft.dropdown.Option(key=str(a["id"]), text=a["name"])      for a in agents]

        if not self.order_no.value:
            self.order_no.value = get_next_doc_no("orders", "O", state.company_id, "order_no")

        if not self.order_date.value:
            self.order_date.value = date.today().strftime("%d-%m-%Y")

        self.populate_all_items()

        if self.page:
            self.update()


    # ─────────────────────────────────────────────────────────
    # Events
    # ─────────────────────────────────────────────────────────
    def on_party_change(self, e):
        party_id = self.party_dd.value
        if not party_id:
            return
        data = select("parties", {"id": party_id})
        if data:
            p = data[0]
            if p.get("transporter_id"): self.transporter_dd.value = str(p["transporter_id"])
            if p.get("price_list_id"):  self.price_list_dd.value  = str(p["price_list_id"])
            if p.get("price_type"):     self.price_type_dd.value  = p["price_type"]
            if p.get("agent_id"):       self.agent_dd.value       = str(p["agent_id"])
            
            # Populate Delivery Address dropdown
            addresses = []
            bill_city = p.get("billing_city", "")
            if bill_city:
                addresses.append(ft.dropdown.Option(f"{p.get('billing_address_line1', '')}, {bill_city}".strip(', ')))
            deliv_city = p.get("delivery_city", "")
            if deliv_city:
                addresses.append(ft.dropdown.Option(f"{p.get('delivery_address_line1', '')}, {deliv_city}".strip(', ')))
            
            self.destination.options = addresses
            if addresses:
                self.destination.value = addresses[-1].key # Default to delivery if exists, else billing
            else:
                self.destination.options = [ft.dropdown.Option("Default Location")]
                self.destination.value = "Default Location"
            
            if p.get("order_thro"):     self.order_thro.value     = p["order_thro"]
            if p.get("documents_thro"): self.docs_by.value        = p["documents_thro"]
            if p.get("remarks"):        self.remarks.value        = p["remarks"]

            # Auto-fill all 5 discount tiers from Party Master
            self.discount_percent.value = str(p.get("discount_percent", 0))
            
            # Load Tax Rates from Party Master
            self.gst_rate_tf.value  = str(p.get("gst_percent", 5) or 5)
            self.tax_type_dd.value  = str(p.get("tax_type", "GST") or "GST").upper()
            self.tcs_rate_tf.value  = str(p.get("tcs_percent", 0) or 0)
            self.cess_rate_tf.value = str(p.get("cess_percent", 0) or 0)
            self._party_tcs_appl    = p.get("tcs_applicable", False)
            
            # Load components from party table
            self.cgst_rate_tf.value = str(p.get("cgst_percent", 0) or 0)
            self.sgst_rate_tf.value = str(p.get("sgst_percent", 0) or 0)
            self.igst_rate_tf.value = str(p.get("igst_percent", 0) or 0)
            
            self.on_price_type_change(None)
            self.on_calc_change()
            self.update()

    def on_calc_change(self, e=None):
        trigger = e.control if (e and hasattr(e, "control")) else self.tax_type_dd
        tax_type = str(self.tax_type_dd.value or "GST").upper()
        
        # 1. Sync rates & visibility based on user input
        if trigger == self.tax_type_dd:
            if tax_type == "GST":
                self.gst_rate_tf.visible = True
                self.cgst_col.visible = True
                self.sgst_col.visible = True
                self.igst_col.visible = False
                try:
                    ig_val = float(self.igst_rate_tf.value or 0)
                    g_val = float(self.gst_rate_tf.value or 0)
                    if g_val == 0 and ig_val > 0:
                        self.gst_rate_tf.value = f"{ig_val:g}"
                        g_val = ig_val
                    self.cgst_rate_tf.value = f"{g_val / 2:g}"
                    self.sgst_rate_tf.value = f"{g_val / 2:g}"
                except ValueError:
                    pass
            else: # IGST
                self.gst_rate_tf.visible = False
                self.cgst_col.visible = False
                self.sgst_col.visible = False
                self.igst_col.visible = True
                try:
                    g_val = float(self.gst_rate_tf.value or 0)
                    ig_val = float(self.igst_rate_tf.value or 0)
                    if ig_val == 0 and g_val > 0:
                        self.igst_rate_tf.value = f"{g_val:g}"
                except ValueError:
                    pass

        elif trigger == self.gst_rate_tf:
            try:
                g_val = float(self.gst_rate_tf.value or 0)
                self.cgst_rate_tf.value = f"{g_val / 2:g}"
                self.sgst_rate_tf.value = f"{g_val / 2:g}"
                self.igst_rate_tf.value = f"{g_val:g}"
            except ValueError:
                pass

        elif trigger == self.cgst_rate_tf:
            try:
                c_val = float(self.cgst_rate_tf.value or 0)
                self.sgst_rate_tf.value = f"{c_val:g}"
                self.gst_rate_tf.value = f"{c_val * 2:g}"
                self.igst_rate_tf.value = f"{c_val * 2:g}"
            except ValueError:
                pass

        elif trigger == self.sgst_rate_tf:
            try:
                s_val = float(self.sgst_rate_tf.value or 0)
                self.cgst_rate_tf.value = f"{s_val:g}"
                self.gst_rate_tf.value = f"{s_val * 2:g}"
                self.igst_rate_tf.value = f"{s_val * 2:g}"
            except ValueError:
                pass

        elif trigger == self.igst_rate_tf:
            try:
                ig_val = float(self.igst_rate_tf.value or 0)
                self.gst_rate_tf.value = f"{ig_val:g}"
                self.cgst_rate_tf.value = f"{ig_val / 2:g}"
                self.sgst_rate_tf.value = f"{ig_val / 2:g}"
            except ValueError:
                pass

        # 2. Run the main calculation
        self.update_totals(trigger)
        
        # 3. Explicitly update the page to show the new component values
        if self.page:
            self.page.update()

    def on_price_type_change(self, e):
        """Automatically updates all rates in the grid when the Price Type changes."""
        if not getattr(self, "price_list_dd", None) or not self.price_list_dd.value or not self.order_items:
            return
            
        try:
            # 1. Fetch latest prices from master
            prices = select("price_list_items", {"price_list_id": self.price_list_dd.value})
            
            # 2. Build a lookup map: { item_id: { size: rate } }
            rate_key = f"{self.price_type_dd.value.lower()}_rate"
            rate_map = {}
            for p in prices:
                iid = str(p["item_id"])
                if iid not in rate_map: rate_map[iid] = {}
                rate_map[iid][p["size_value"]] = float(p.get(rate_key, 0))
                
            # 3. Update every item currently in the grid
            for item in self.order_items:
                iid = str(item["item_id"])
                if iid in rate_map:
                    for sz, rate_val in rate_map[iid].items():
                        if sz in item["sizes_data"]:
                            item["sizes_data"][sz]["rate"] = str(rate_val)

            # 4. Refresh UI
            self.rebuild_grid()
            if e and self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Switched to {self.price_type_dd.value} pricing"), bgcolor=AppColors.INFO)
                self.page.snack_bar.open = True
                self.page.update()
            
        except Exception as ex:
            print(f"Price Switch Error: {ex}")



    def on_qty_type_change(self, e):
        self.rebuild_grid()

    def populate_all_items(self):
        items = select("items", {"company_id": state.company_id, "item_type": ["Sales", "Both"]})
        options = [ft.dropdown.Option(key=str(i["id"]), text=i["item_name"]) for i in items]
        
        all_sizes = set()
        for i in items:
            raw = i.get("sizes")
            if isinstance(raw, list):
                all_sizes.update(raw)
            elif isinstance(raw, str):
                import json as _json
                try: all_sizes.update(_json.loads(raw))
                except: pass
        self.SIZES = sort_sizes(list(all_sizes))

        self.order_items = []
        for i in items:
            item_id = str(i["id"])
            inner = int(i.get("pcs_per_inner_box") or 1)
            outer = int(i.get("boxes_per_outer_box") or 1)
            packing = inner * outer if (inner * outer) > 0 else 240
            
            stock_data = select("stock_ledger", {"item_id": item_id})
            stk_map = {}
            for st in stock_data:
                s_val = st.get("size_value", "")
                qty_val = st.get("qty") or 0
                stk_map[s_val] = stk_map.get(s_val, 0) + int(float(qty_val))
            
            if i.get("opening_stock"):
                open_stk = i["opening_stock"]
                if isinstance(open_stk, dict):
                    for k, v in open_stk.items():
                        stk_map[k] = stk_map.get(k, 0) + int(float(v))

            sizes_data = {}
            for sz in self.SIZES:
                sizes_data[sz] = {"pieces": "", "rate": "", "amount": "", "boxes": "", "curr_stk": str(stk_map.get(sz, 0)), "wanted": ""}

            item_sizes_set = set()
            raw = i.get("sizes")
            if isinstance(raw, list):
                item_sizes_set = set(raw)
            elif isinstance(raw, str):
                import json as _json
                try: item_sizes_set = set(_json.loads(raw))
                except: pass

            self.order_items.append({
                "item_id":     item_id,
                "item_name":   i.get("item_name", "Unknown"),
                "sizes_data":  sizes_data,
                "packing":     str(packing),
                "total_boxes": "0",
                "total_units": "0",
                "s_no":        str(len(self.order_items) + 1),
                "options":     options,
                "valid_sizes": list(item_sizes_set),
            })
        
        # Sort items alphabetically by name
        self.order_items.sort(key=lambda x: str(x["item_name"]).lower())
        self.selected_item_index = 0
        self.rebuild_grid()


    
    def _make_row(self, item):
        """Build the right-panel size grid for a single item."""

        if "controls" not in item:
            item["controls"] = {}

        def mk_input(val, w=70, on_change=None, read_only=False):
            return ft.TextField(
                value=val, width=w, height=36, text_size=15,
                content_padding=ft.padding.symmetric(horizontal=6, vertical=6),
                border_radius=6, border_color="#E2E8F0",
                bgcolor="#F8F9FD" if read_only else "#FFFFFF",
                text_align=ft.TextAlign.CENTER,
                on_change=on_change, dense=True,
                read_only=read_only
            )

        def mk_amount_tf(sz):
            tf = mk_input(item["sizes_data"][sz]["amount"], read_only=True)
            if "controls" not in item["sizes_data"][sz]:
                item["sizes_data"][sz]["controls"] = {}
            item["sizes_data"][sz]["controls"]["amount"] = tf
            return tf

        def mk_boxes_tf(sz):
            tf = mk_input(item["sizes_data"][sz]["boxes"], read_only=True)
            if "controls" not in item["sizes_data"][sz]:
                item["sizes_data"][sz]["controls"] = {}
            item["sizes_data"][sz]["controls"]["boxes"] = tf
            return tf

        def update_val(sz, field, e):
            item["sizes_data"][sz][field] = e.control.value
            try:
                p = float(item["sizes_data"][sz]["pieces"] or 0)
                r = float(item["sizes_data"][sz]["rate"] or 0)
                pack = float(item.get("packing") or 1)

                amt_str = str(round(p * r, 2))
                box_str = str(round(p / pack, 2) if pack > 0 else 0)

                item["sizes_data"][sz]["amount"] = amt_str
                item["sizes_data"][sz]["boxes"]  = box_str

                if "controls" in item["sizes_data"][sz]:
                    if "amount" in item["sizes_data"][sz]["controls"]:
                        item["sizes_data"][sz]["controls"]["amount"].value = amt_str
                        item["sizes_data"][sz]["controls"]["amount"].update()
                    if "boxes" in item["sizes_data"][sz]["controls"]:
                        item["sizes_data"][sz]["controls"]["boxes"].value = box_str
                        item["sizes_data"][sz]["controls"]["boxes"].update()

                tot_p = sum(float(item["sizes_data"][s]["pieces"] or 0) for s in item["sizes_data"])
                item["total_units"] = str(int(tot_p))
                item["total_boxes"] = str(round(tot_p / pack, 2) if pack > 0 else 0)

                if "total_boxes_lbl" in item["controls"]:
                    item["controls"]["total_boxes_lbl"].value = item["total_boxes"]
                    item["controls"]["total_boxes_lbl"].update()
                if "total_units_lbl" in item["controls"]:
                    item["controls"]["total_units_lbl"].value = item["total_units"]
                    item["controls"]["total_units_lbl"].update()

                # Also refresh the left panel card to show updated pcs/amt
                self._refresh_left_panel()
                if self.page:
                    self.left_panel.update()

            except Exception:
                pass
            self.update_totals()

        def on_packing_change(e):
            item["packing"] = e.control.value
            try:
                pack = float(item.get("packing") or 1)
                tot_p = 0
                for s in item["sizes_data"]:
                    p_val = float(item["sizes_data"][s]["pieces"] or 0)
                    box_str = str(round(p_val / pack, 2) if pack > 0 else 0)
                    item["sizes_data"][s]["boxes"] = box_str
                    if "controls" in item["sizes_data"][s] and "boxes" in item["sizes_data"][s]["controls"]:
                        item["sizes_data"][s]["controls"]["boxes"].value = box_str
                        item["sizes_data"][s]["controls"]["boxes"].update()
                    tot_p += p_val
                item["total_boxes"] = str(round(tot_p / pack, 2) if pack > 0 else 0)
                if "total_boxes_lbl" in item["controls"]:
                    item["controls"]["total_boxes_lbl"].value = item["total_boxes"]
                    item["controls"]["total_boxes_lbl"].update()
            except Exception:
                pass
            self.update_totals()

        # Determine sizes to display
        valid_sizes = item.get("valid_sizes", [])
        display_sizes = [sz for sz in self.SIZES if not valid_sizes or sz in valid_sizes]
        if not display_sizes:
            display_sizes = self.SIZES

        # ── Build the column-based grid ──────────────────────────
        COL_W = 80  # each size column width

        def header_cell(text, w=COL_W, is_label=False):
            return ft.Container(
                width=w, height=36,
                bgcolor=AppColors.PRIMARY if not is_label else "#F1F5F9",
                border_radius=ft.border_radius.only(top_left=6, top_right=6),
                alignment=ft.alignment.center,
                content=ft.Text(text, size=14, weight="bold",
                                color=ft.colors.WHITE if not is_label else AppColors.TEXT_HEADER)
            )

        def row_label_cell(text):
            box = ft.Container(
                width=60, height=36,
                bgcolor="#F8F9FD",
                border=ft.border.all(1, "#E8EDF2"),
                border_radius=6,
                alignment=ft.alignment.center_left,
                padding=ft.padding.only(left=8),
                content=ft.Text(text, size=13, weight="bold", color=AppColors.TEXT_SUB)
            )
            return ft.Container(content=box, padding=ft.padding.symmetric(vertical=2))

        def data_cell(ctrl):
            return ft.Container(
                width=COL_W,
                content=ctrl,
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(horizontal=4, vertical=2)
            )

        # Build rows: one Column per size (header + 5 data cells)
        row_labels = ["Pcs", "Rate", "Amt", "Boxes", "Stock"]
        size_columns = []

        for sz in display_sizes:
            pcs_input = mk_input(item["sizes_data"][sz]["pieces"], w=COL_W - 8,
                                 on_change=lambda e, s=sz: update_val(s, "pieces", e))
            rate_input = mk_input(item["sizes_data"][sz]["rate"], w=COL_W - 8,
                                  on_change=lambda e, s=sz: update_val(s, "rate", e))
            amt_tf   = mk_amount_tf(sz)
            amt_tf.width = COL_W - 8
            box_tf   = mk_boxes_tf(sz)
            box_tf.width = COL_W - 8
            stk_input = mk_input(item["sizes_data"][sz]["curr_stk"], w=COL_W - 8, read_only=True)

            col = ft.Column([
                header_cell(sz),
                data_cell(pcs_input),
                data_cell(rate_input),
                data_cell(amt_tf),
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            size_columns.append(col)

        # Label column on the left
        label_col = ft.Column([
            header_cell("", w=60, is_label=True),
            row_label_cell("Pcs"),
            row_label_cell("Rate"),
            row_label_cell("Amt"),
        ], spacing=4)

        # Totals area
        tot_boxes_lbl = ft.Text(item["total_boxes"], size=14, weight="bold", color=AppColors.PRIMARY)
        tot_units_lbl = ft.Text(item["total_units"], size=14, weight="bold", color=AppColors.PRIMARY)
        item["controls"]["total_boxes_lbl"] = tot_boxes_lbl
        item["controls"]["total_units_lbl"] = tot_units_lbl

        packing_tf = mk_input(item["packing"], w=70, on_change=on_packing_change)

        totals_row = ft.Container(
            bgcolor="#F8F9FD",
            border=ft.border.all(1, "#E2E8F0"),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=4),
            content=ft.Row([
                ft.Column([ft.Text("Packing", size=10, color=AppColors.TEXT_MUTED), packing_tf],
                          spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.VerticalDivider(width=1, color="#E2E8F0"),
                ft.Column([ft.Text("Total Boxes", size=10, color=AppColors.TEXT_MUTED), tot_boxes_lbl],
                          spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.VerticalDivider(width=1, color="#E2E8F0"),
                ft.Column([ft.Text("Total Units", size=10, color=AppColors.TEXT_MUTED), tot_units_lbl],
                          spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        grid = ft.Row([label_col, *size_columns], spacing=4, scroll=ft.ScrollMode.AUTO)

        return ft.Container(
            bgcolor=ft.colors.WHITE,
            border=ft.border.all(1, "#E2E8F0"),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            content=ft.Column([
                # Item header
                ft.Row([
                    ft.Icon(ft.icons.INVENTORY_2_OUTLINED, color=AppColors.PRIMARY, size=18),
                    ft.Text(item.get("item_name", ""), size=15, weight="bold", color=AppColors.TEXT_HEADER),
                    # ft.Container(expand=True),
                    # totals_row,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                ft.Divider(height=1, color="#F1F5F9"),
                # Size grid
                grid,
            ], spacing=6)
        )

    def delete_selected_row(self, e):
        """Delete the currently selected item."""
        if not self.order_items:
            return
        idx = self.selected_item_index
        if 0 <= idx < len(self.order_items):
            self.order_items.pop(idx)
            self.selected_item_index = max(0, idx - 1)
        self.rebuild_grid()

    def remove_item(self, item):
        try:
            idx = self.order_items.index(item)
            self.order_items.remove(item)
            self.selected_item_index = max(0, idx - 1)
        except ValueError:
            pass
        self.rebuild_grid()

    def rebuild_grid(self):
        self._refresh_left_panel()
        self._refresh_right_panel()
        self.update_totals()
        if self.page:
            self.left_panel.update()
            self.right_panel.update()

    def _refresh_left_panel(self):
        """Rebuild the left item-list panel."""
        self.left_panel.controls.clear()
        
        # Header
        self.left_panel.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(vertical=6),
                content=ft.Row([
                    ft.Text("Items", size=12, weight="bold", color=AppColors.TEXT_HEADER),
                    ft.Container(expand=True),
                    ft.Text(f"{len(self.order_items)}", size=12, color=AppColors.PRIMARY, weight="bold"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
        )

        if not self.order_items:
            self.left_panel.controls.append(
                ft.Container(
                    padding=ft.padding.all(20),
                    content=ft.Column([
                        ft.Icon(ft.icons.SHOPPING_CART_OUTLINED, color=AppColors.TEXT_MUTED, size=32),
                        ft.Text("No items added", size=12, color=AppColors.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                        ft.Text("Click 'Add Item' to begin", size=10, color=AppColors.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                    ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center
                )
            )
            return

        for i, item in enumerate(self.order_items):
            is_selected = (i == self.selected_item_index)
            total_pcs = sum(float(item["sizes_data"][s]["pieces"] or 0) for s in item["sizes_data"])
            total_amt = sum(
                float(item["sizes_data"][s]["pieces"] or 0) * float(item["sizes_data"][s]["rate"] or 0)
                for s in item["sizes_data"]
            )
            valid_sz = item.get("valid_sizes", [])
            sz_label = ", ".join(valid_sz) if valid_sz else "-"

            def make_card(idx=i, it=item):
                def on_click(e, _idx=idx):
                    self.selected_item_index = _idx
                    self._refresh_left_panel()
                    self._refresh_right_panel()
                    if self.page:
                        self.left_panel.update()
                        self.right_panel.update()

                is_sel = (idx == self.selected_item_index)
                _tp = sum(float(it["sizes_data"][s]["pieces"] or 0) for s in it["sizes_data"])
                _ta = sum(
                    float(it["sizes_data"][s]["pieces"] or 0) * float(it["sizes_data"][s]["rate"] or 0)
                    for s in it["sizes_data"]
                )
                _sz = ", ".join(it.get("valid_sizes", [])) if it.get("valid_sizes") else "-"

                return ft.GestureDetector(
                    on_tap=on_click,
                    content=ft.Container(
                        bgcolor=AppColors.PRIMARY_LIGHT if is_sel else ft.colors.WHITE,
                        border=ft.border.all(2 if is_sel else 1, AppColors.PRIMARY if is_sel else "#E2E8F0"),
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(str(idx + 1), size=11, weight="bold", color=ft.colors.WHITE),
                                    bgcolor=AppColors.PRIMARY if is_sel else AppColors.TEXT_MUTED,
                                    border_radius=12, width=20, height=20,
                                    alignment=ft.alignment.center
                                ),
                                ft.Container(expand=True, content=ft.Text(
                                    it.get("item_name", "?"),
                                    size=14, weight="bold",
                                    color=AppColors.PRIMARY if is_sel else AppColors.TEXT_HEADER,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS
                                )),
                                ft.GestureDetector(
                                    on_tap=lambda e, _it=it: self.remove_item(_it),
                                    content=ft.Icon(
                                        ft.icons.DELETE_OUTLINE,
                                        size=16, color=AppColors.DANGER
                                    )
                                )
                            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Text(
                                f"Sizes: {_sz}",
                                size=11, color=AppColors.TEXT_MUTED,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS
                            ),
                            ft.Row([
                                ft.Text(f"Pcs: {int(_tp)}", size=12, color=AppColors.TEXT_SUB, weight="w500"),
                                ft.Container(expand=True),
                                ft.Text(f"\u20b9{_ta:,.0f}", size=12, color=AppColors.SUCCESS, weight="bold"),
                            ]),
                        ], spacing=2)
                    )
                )

            self.left_panel.controls.append(make_card())

    def _refresh_right_panel(self):
        """Rebuild the right size-grid panel for the currently selected item."""
        self.right_panel.controls.clear()

        if not self.order_items:
            self.right_panel.controls.append(
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    content=ft.Column([
                        ft.Icon(ft.icons.TABLE_CHART_OUTLINED, color=AppColors.TEXT_MUTED, size=48),
                        ft.Text("Add an item to start entering quantities",
                                size=14, color=AppColors.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
            return

        idx = self.selected_item_index
        if idx >= len(self.order_items):
            idx = len(self.order_items) - 1
            self.selected_item_index = idx

        item = self.order_items[idx]
        row_widget = self._make_row(item)
        self.right_panel.controls.append(row_widget)


    # ─────────────────────────────────────────────────────────
    # Totals
    # ─────────────────────────────────────────────────────────
    


    def update_totals(self, trigger=None):
        total_pcs = 0
        total_boxes = 0
        base_sum = 0
        
        for item in self.order_items:
            for sz in item["sizes_data"]:
                p = float(item["sizes_data"][sz]["pieces"] or 0)
                r = float(item["sizes_data"][sz]["rate"] or 0)
                amt = p * r
                item["sizes_data"][sz]["amount"] = str(round(amt, 2))
                base_sum += amt
                total_pcs += p
            try:
                item["total_units"] = str(int(sum(float(item["sizes_data"][s]["pieces"] or 0) for s in item["sizes_data"])))
                item["total_boxes"] = str(int(float(item["total_units"]) / float(item["packing"] or 1)))
                total_boxes += float(item["total_boxes"])
            except: pass

            
        self._val_total_pcs = total_pcs
        self._val_total_boxes = total_boxes
        self._val_taxable = base_sum

        self.no_of_items_lbl.value = f"{len(self.order_items)}"
        self.total_pcs.value   = f"{int(total_pcs)}"
        self.total_boxes.value = f"{total_boxes}"
        self.total_units.value = f"{int(total_pcs)}"
        self.taxable_value.value = f"₹{base_sum:.2f}"

        # Calculate Discount
        current_amount = base_sum
        dp = float(self.discount_percent.value or 0)
        da = current_amount * (dp / 100)
        current_amount -= da
        self.discount_amount_lbl.value = f"Amt: ₹{da:.2f}"
        
        discounted_taxable = current_amount
        
        # Tax Calculation (GST or IGST)
        tax_type = str(self.tax_type_dd.value or "GST").upper()
        
        if tax_type == "GST":
            cgst_p = float(self.cgst_rate_tf.value or 0)
            sgst_p = float(self.sgst_rate_tf.value or 0)
            
            cgst_amt = discounted_taxable * (cgst_p / 100)
            sgst_amt = discounted_taxable * (sgst_p / 100)
            
            self.cgst_amt_lbl.value = f"₹{cgst_amt:.2f}"
            self.sgst_amt_lbl.value = f"₹{sgst_amt:.2f}"
            self.igst_amt_lbl.value = "₹0.00"
            
            tax_amt = cgst_amt + sgst_amt
            self.gst_amount.value = f"GST: ₹{tax_amt:.2f}"
        else:
            igst_p = float(self.igst_rate_tf.value or 0)
            igst_amt = discounted_taxable * (igst_p / 100)
            
            self.igst_amt_lbl.value = f"₹{igst_amt:.2f}"
            self.cgst_amt_lbl.value = "₹0.00"
            self.sgst_amt_lbl.value = "₹0.00"
            
            tax_amt = igst_amt
            self.gst_amount.value = f"IGST: ₹{tax_amt:.2f}"

        cess_p = float(self.cess_rate_tf.value or 0)
        cess_amt = discounted_taxable * (cess_p / 100)
        self.cess_amt_lbl.value = f"₹{cess_amt:.2f}"

        tcs_p = float(self.tcs_rate_tf.value or 0)
        tcs_amt = discounted_taxable * (tcs_p / 100)
        self.tcs_amt_lbl.value = f"₹{tcs_amt:.2f}"
        
        # Grand Total
        grand_total = discounted_taxable + tax_amt + cess_amt + tcs_amt
        
        if trigger == self.round_off:
            try:
                diff = float(self.round_off.value or 0)
            except ValueError:
                diff = 0.0
            rounded = round(grand_total + diff, 2)
        else:
            rounded = math.ceil(grand_total)
            diff = rounded - grand_total
            self.round_off.value = f"{diff:.2f}"

        self._val_round_off = diff
        self._val_net_amount = rounded
        self.gross_amount.value = f"Total: ₹{rounded:.2f}"
        
        if self.page:
            self.update()


    def save_order(self, e):
        if not self.party_dd.value or not self.order_items:
            self.page.snack_bar = ft.SnackBar(ft.Text("Select Party and add at least one item!"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()
            return
        if not self.tax_type_dd.value:
            self.page.snack_bar = ft.SnackBar(ft.Text("Please select a Tax Type (GST/IGST) before saving!"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()
            return

        def date_to_iso(val):
            """Convert dd-mm-yyyy or dd/mm/yyyy display date to ISO yyyy-mm-dd for DB."""
            if not val:
                return date.today().isoformat()
            val = str(val).strip()
            # Already ISO format (YYYY-MM-DD)?
            if len(val) == 10 and val[4] == "-" and val[7] == "-":
                return val
            # Try common display formats
            from datetime import datetime as _dt
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
                try:
                    return _dt.strptime(val, fmt).date().isoformat()
                except ValueError:
                    continue
            return val  # fallback

        def safe_float_label(ctrl, default=0):
            val = str(ctrl.value or "")
            if "₹" in val:
                try:
                    return float(val.split("₹")[1].replace(",", ""))
                except:
                    return default
            elif any(char.isdigit() for char in val):
                try:
                    return float(''.join(c for c in val if c.isdigit() or c == '.'))
                except:
                    return default
            return default

        try:
            order_val = self.order_no.value or get_next_doc_no("orders", "O", state.company_id, "order_no")
            
            total_tax_amt = (
                safe_float_label(self.cgst_amt_lbl) + 
                safe_float_label(self.sgst_amt_lbl) + 
                safe_float_label(self.igst_amt_lbl) + 
                safe_float_label(self.cess_amt_lbl) + 
                safe_float_label(self.tcs_amt_lbl)
            )

            header = {
                "company_id":     state.company_id,
                "order_no":       order_val,
                "order_date":     date_to_iso(self.order_date.value),
                "discount_percent": float(self.discount_percent.value or 0),
                "discount_amount":  safe_float_label(self.discount_amount_lbl),
                "party_id":       self.party_dd.value,
                "agent_id":       self.agent_dd.value if getattr(self.agent_dd, 'value', None) else None,
                "transporter_id": self.transporter_dd.value,
                "price_list_id":  self.price_list_dd.value,
                "price_type":     self.price_type_dd.value,
                "destination":    self.destination.value,
                "order_by":       self.order_by.value,
                "order_thro":     self.order_thro.value,
                "party_order_no": self.party_order_no.value,
                "party_order_date": date_to_iso(self.party_order_dt.value),
                "remarks":        self.remarks.value,
                "no_of_cases":    int(self.no_of_cases.value or 0),
                "documents_by":   self.docs_by.value,
                "total_pcs":      int(safe_float_label(self.total_pcs)),
                "total_boxes":    safe_float_label(self.total_boxes),
                
                "cgst_amount":    safe_float_label(self.cgst_amt_lbl),
                "sgst_amount":    safe_float_label(self.sgst_amt_lbl),
                "igst_amount":    safe_float_label(self.igst_amt_lbl),
                
                "tax_type":       self.tax_type_dd.value,
                "tax_per":        float(self.gst_rate_tf.value or 0) if (self.tax_type_dd.value or "GST").upper() == "GST" else float(self.igst_rate_tf.value or 0),
                "gst_amount":     total_tax_amt,
                "total_amount":   safe_float_label(self.taxable_value),
                "round_off":      float(self.round_off.value or 0),
                "net_amount":     safe_float_label(self.gross_amount),
                "no_of_items":    len(self.order_items),
                "status":         "Pending"
            }

            if self.current_edit_id:
                order_id = self.current_edit_id
                update("orders", header, {"id": order_id})
                delete("order_items", {"order_id": order_id})
            else:
                res = insert("orders", header)
                if not res:
                    raise Exception("Failed to save order header")
                order_id = res[0]["id"]

            # Calculate Footer Discount Multiplier
            footer_multiplier = (1 - float(self.discount_percent.value or 0) / 100)

            local_order_items = []
            for item in self.order_items:
                if not item["item_id"]: continue
                for sz, sz_data in item["sizes_data"].items():
                    pcs = float(sz_data["pieces"] or 0)
                    if pcs > 0:
                        rate = float(sz_data["rate"] or 0)
                        
                        # Combine row-level and footer discounts
                        item_multiplier = (1 - item.get("disc_p", 0) / 100)
                        net_multiplier = item_multiplier * footer_multiplier
                        net_rate = rate * net_multiplier
                        amount = pcs * net_rate
                        
                        item_dict = {
                            "order_id":        order_id,
                            "company_id":      state.company_id,
                            "item_id":         item["item_id"],
                            "item_name":       item.get("item_name", "Unknown"),
                            "size_value":      sz,
                            "rate":            round(rate, 2), # Gross Rate
                            "qty_pieces":      int(pcs),
                            "qty_boxes":       pcs / float(item["packing"] or 1),
                            "amount":          round(amount, 2), # Net Amount
                            "discount_amount": round(pcs * rate * (1 - net_multiplier), 2),
                            "gross_amount":    round(pcs * rate, 2),
                            "tax_percent":     float(self.gst_rate_tf.value or 0),
                        }
                        insert("order_items", item_dict)
                        local_order_items.append(item_dict)

            # Generate PDF using in-memory data
            def get_dd_text(dd):
                if not getattr(dd, 'value', None): return ""
                for opt in getattr(dd, 'options', []):
                    if str(opt.key) == str(dd.value): return opt.text
                return ""

            order_data = dict(header)
            order_data["id"] = order_id
            order_data["party_name"] = get_dd_text(self.party_dd)
            order_data["agent_name"] = get_dd_text(self.agent_dd)
            order_data["transporter_name"] = get_dd_text(self.transporter_dd)

            order_data = self._enrich_order_data_for_pdf(order_data)

            comp_data = select("companies", {"id": state.company_id})
            company = comp_data[0] if comp_data else {}
            pdf_path = pdf_engine.generate_order(order_data, local_order_items, company)
            print_pdf(pdf_path)

            self.page.snack_bar = ft.SnackBar(ft.Text("✅ Order Saved Successfully & PDF Generated!"), bgcolor="green")
            self.page.snack_bar.open = True
            self.clear_form(None)

        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()

    # ─────────────────────────────────────────────────────────
    # Clear
    # ─────────────────────────────────────────────────────────
    def clear_form(self, e=None):
        self.order_no.value = get_next_doc_no("orders", "O", state.company_id, "order_no")
        self.order_date.value = date.today().strftime("%d-%m-%Y")
        self.party_dd.value = None
        self.agent_dd.value = None
        self.transporter_dd.value = None
        self.destination.value = ""
        self.order_by.value = ""
        self.party_order_no.value = ""
        self.party_order_dt.value = date.today().strftime("%d-%m-%Y")
        self.remarks.value = ""
        self.no_of_cases.value = "1"
        self.qty_type.value = "Pieces"

        self.discount_percent.value = "0"
        self.round_off.value = "0.00"
        self.SIZES = []
        self.order_items = []
        self.selected_item_index = 0
        self.current_edit_id = None
        self.rebuild_grid()
        self.update_totals()
        if self.page: self.update()


    # ─────────────────────────────────────────────────────────
    # History & Printing
    # ─────────────────────────────────────────────────────────
    def show_history_modal(self, e):
        orders = select("orders", {"company_id": state.company_id})
        # Sort by created_at DESC (latest first)
        orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        parties = select("parties", {"company_id": state.company_id})
        party_map = {str(p["id"]): p["name"] for p in parties}
        
        lv = ft.ListView(expand=1, spacing=10, padding=20)
        for ord in orders:
            p_name = party_map.get(str(ord.get("party_id")), "Unknown")
            ord["party_name"] = p_name
            
            lv.controls.append(
                ft.Container(
                    padding=10,
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    border=ft.border.all(1, "#E2E8F0"),
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"{ord.get('order_no')}", weight="bold", size=14),
                            ft.Row([
                                ft.Icon(ft.icons.CALENDAR_TODAY, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(f"{ord.get('order_date')}", size=11, color=ft.colors.BLUE_GREY_600),
                                ft.VerticalDivider(width=10),
                                ft.Icon(ft.icons.ACCESS_TIME, size=12, color=ft.colors.BLUE_GREY_400),
                                ft.Text(self._format_timestamp(ord.get('created_at')), size=11, color=ft.colors.BLUE_GREY_600),
                            ], spacing=5),
                            ft.Text(p_name, size=13, weight="w500", color=AppColors.PRIMARY),
                        ], expand=True, spacing=4),
                        ft.Column([
                            ft.Text(f"Pcs: {int(ord.get('total_pcs', 0))}", size=12, weight="bold"),
                            ft.Text(f"₹ {float(ord.get('net_amount', 0)):,.2f}", size=16, weight="bold", color=ft.colors.GREEN_700),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                        ft.Row([
                            ft.IconButton(ft.icons.EDIT_OUTLINED, tooltip="Edit Order", icon_color=AppColors.PRIMARY, 
                                          on_click=lambda e, o=ord: self.load_order_for_edit(o, dlg)),
                            ft.IconButton(ft.icons.PRINT, tooltip="Print Order", icon_color=ft.colors.BLUE_700, 
                                          on_click=lambda e, o=ord: self.print_history_order(o)),
                            ft.IconButton(ft.icons.DELETE_OUTLINE, tooltip="Delete Order", icon_color="red",
                                          on_click=lambda e, o=ord: self.delete_order_from_history(o, dlg))
                        ])
                    ])
                )
            )
            
        dlg = ft.AlertDialog(
            title=ft.Text("Recent Orders"),
            content=ft.Container(width=600, height=400, content=lv),
            actions=[ft.TextButton("Close", on_click=lambda e: self._close_dialog(dlg))]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def load_order_for_edit(self, order, dlg):
        """Loads a past order into the main form for editing."""
        try:
            self._close_dialog(dlg)
            self.clear_form()
            
            self.current_edit_id = order["id"]
            self.order_no.value   = order.get("order_no", "")
            self.order_date.value = order.get("order_date", "")
            self.party_dd.value   = str(order.get("party_id"))
            self.agent_dd.value   = str(order.get("agent_id")) if order.get("agent_id") else None
            self.transporter_dd.value = str(order.get("transporter_id")) if order.get("transporter_id") else None
            self.price_list_dd.value  = str(order.get("price_list_id")) if order.get("price_list_id") else None
            self.price_type_dd.value  = order.get("price_type", "Wholesale")
            self.destination.value    = order.get("destination", "")
            self.order_by.value       = order.get("order_by", "")
            self.order_thro.value     = order.get("order_thro", "DIRECT")
            self.party_order_no.value = order.get("party_order_no", "")
            self.party_order_dt.value = order.get("party_order_date", "")
            self.remarks.value        = order.get("remarks", "")
            self.no_of_cases.value    = str(order.get("no_of_cases", 1))
            
            # Tax & Discounts
            self.tax_type_dd.value = order.get("tax_type", "GST")
            self.gst_rate_tf.value  = str(order.get("tax_per", 5))
            
            self.discount_percent.value = str(order.get("discount_percent", 0))
            
            # Load items
            db_items = select("order_items", {"order_id": order["id"]})
            
            # Pre-populate all items
            self.populate_all_items()
            
            # Fetch default rates dynamically so that newly added items/sizes get the correct rate
            self.on_price_type_change(None)
            
            # Update quantities from db_items
            for it in db_items:
                item_id = str(it["item_id"])
                sz = it["size_value"]
                qty = it["qty_pieces"]
                rate = it["rate"]
                
                # Find the item in self.order_items
                for item in self.order_items:
                    if str(item["item_id"]) == item_id:
                        if sz in item["sizes_data"]:
                            item["sizes_data"][sz]["pieces"] = str(qty)
                            item["sizes_data"][sz]["rate"] = str(rate)
                            item["sizes_data"][sz]["amount"] = str(round(qty * float(rate or 0), 2))
                        break
            
            # Recalculate totals for all items
            for item in self.order_items:
                pack = float(item["packing"] or 1)
                tot_p = sum(float(item["sizes_data"][s]["pieces"] or 0) for s in item["sizes_data"])
                item["total_units"] = str(int(tot_p))
                item["total_boxes"] = str(round(tot_p / pack, 2) if pack > 0 else 0)
                for sz in item["sizes_data"]:
                    pcs = float(item["sizes_data"][sz]["pieces"] or 0)
                    item["sizes_data"][sz]["boxes"] = str(round(pcs / pack, 2) if pack > 0 else 0)
            
            # Select the first item that has any pieces > 0
            for i, item in enumerate(self.order_items):
                if sum(float(item["sizes_data"][s]["pieces"] or 0) for s in item["sizes_data"]) > 0:
                    self.selected_item_index = i
                    break

            self.rebuild_grid()
            self.on_calc_change() # Force UI to split CGST/SGST
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Loaded Order: {self.order_no.value}"), bgcolor=AppColors.PRIMARY)
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            print(f"Edit Load Error: {ex}")
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Failed to load order: {ex}"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()

    def _format_timestamp(self, ts):
        if not ts: return "-"
        try:
            # Assumes ISO format from Postgres
            from datetime import datetime
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime("%b %d, %Y %I:%M %p")
        except:
            return str(ts)[:16]

    def delete_order_from_history(self, order, dlg):
        """Deletes an order and its items from the database, checking for dependencies."""
        def confirm_delete(e):
            try:
                order_id = order["id"]
                order_no = order.get("order_no", "")

                # Check full downstream chain
                linked_slips = select("packing_slip_items", {"order_id": order_id})
                if linked_slips:
                    confirm_dlg.open = False
                    self.page.update()
                    self.page.snack_bar = ft.SnackBar(
                        ft.Text("Cannot delete: Order is linked to Packing Slips. Delete the slips first."),
                        bgcolor="orange"
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                    return

                # Also check if order referenced in packing_slips header
                linked_ps = select("packing_slips", {"order_id": order_id})
                if linked_ps:
                    confirm_dlg.open = False
                    self.page.update()
                    self.page.snack_bar = ft.SnackBar(
                        ft.Text(f"Cannot delete: Order has {len(linked_ps)} Packing Slip(s). Delete them first."),
                        bgcolor="orange"
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                    return

                # Safe to delete — clean up everything
                delete("order_items", {"order_id": order_id})
                delete("orders", {"id": order_id})

                # Clean up ledger & stock entries tied to this order
                try:
                    delete("ledger_entries", {"company_id": state.company_id, "ref_type": "Sales Order", "ref_id": order_no})
                    delete("stock_ledger",  {"company_id": state.company_id, "ref_type": "Sales Order", "ref_id": order_no})
                except Exception:
                    pass

                confirm_dlg.open = False
                dlg.open = False
                self.page.update()

                self.page.snack_bar = ft.SnackBar(ft.Text(f"Order {order_no} deleted successfully"), bgcolor="green")
                self.page.snack_bar.open = True
                self.page.update()

                # Refresh history modal
                self.show_history_modal(None)
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Delete Error: {ex}"), bgcolor="red")
                self.page.snack_bar.open = True
                self.page.update()

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete order {order.get('order_no')}? This cannot be undone."),
            actions=[
                ft.TextButton("Yes, Delete", on_click=confirm_delete, style=ft.ButtonStyle(color="red")),
                ft.TextButton("Cancel", on_click=lambda e: self._close_dialog(confirm_dlg))
            ]
        )
        self.page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        self.page.update()

    def _close_dialog(self, dlg):
        dlg.open = False
        self.page.update()

    def print_history_order(self, order):
        try:
            items = select("order_items", {"order_id": order["id"]})
            comp_data = select("companies", {"id": state.company_id})
            company = comp_data[0] if comp_data else {}

            order = self._enrich_order_data_for_pdf(dict(order))
            pdf_path = pdf_engine.generate_order(order, items, company)
            print_pdf(pdf_path)
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error printing: {ex}"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()

    def _enrich_order_data_for_pdf(self, order_dict):
        pid = order_dict.get("party_id")
        if pid:
            p_data = select("parties", {"id": pid})
            if p_data:
                p = p_data[0]
                order_dict["party_name"] = p.get("name", "")
                
                # Billing address
                b_parts = [p.get("billing_address_line1"), p.get("billing_address_line2"), p.get("billing_address_line3"), p.get("billing_city"), p.get("billing_state"), p.get("billing_pincode")]
                order_dict["party_address"] = ", ".join([str(x).strip() for x in b_parts if x and str(x).strip()])
                
                # Delivery address
                d_parts = [p.get("delivery_address_line1"), p.get("delivery_address_line2"), p.get("delivery_address_line3"), p.get("delivery_city"), p.get("delivery_state"), p.get("delivery_pincode")]
                order_dict["delivery_address"] = ", ".join([str(x).strip() for x in d_parts if x and str(x).strip()])
                
                # Mobile / Phone
                order_dict["party_mob"] = str(p.get("mobile") or p.get("phone") or "")
                
                # GSTIN
                order_dict["party_gstin"] = str(p.get("gstin") or "")
                
        if order_dict.get("agent_id"):
            a_data = select("agents", {"id": order_dict["agent_id"]})
            if a_data: order_dict["agent_name"] = a_data[0].get("name", "")
            
        if order_dict.get("transporter_id"):
            t_data = select("transporters", {"id": order_dict["transporter_id"]})
            if t_data: order_dict["transporter_name"] = t_data[0].get("name", "")
            
        return order_dict


# =========================================================
# SALES SCREEN - Tab container for all Sales transactions
# =========================================================



