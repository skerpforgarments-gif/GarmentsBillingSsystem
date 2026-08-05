import flet as ft
from core.theme import AppColors, AppStyles

class ItemMasterForm(ft.Stack):
    """
    Full Item Master form using ft.Stack to support internal sub-modals without page.dialog conflicts.
    """

    def __init__(self, on_submit=None):
        super().__init__()
        self.expand = True
        self.on_submit = on_submit

        # 1. CORE DATA ATTRIBUTES (Initialize early to avoid AttributeErrors)
        self.size_checkboxes = {}
        self.opening_stock_inputs = {}
        self.price_inputs = {}
        self.size_matrix_grid = ft.Row(wrap=True, spacing=10)
        self.size_grid_row = ft.Row(spacing=30, vertical_alignment=ft.CrossAxisAlignment.START)

        # 2. FIELD STYLING
        self.style_args = {
            "dense": True,
            "text_size": 13,
            "height": 45,
            "border_radius": AppStyles.BUTTON_RADIUS,
            "border_color": "#E2E8F0",
            "focused_border_color": AppColors.PRIMARY,
            "bgcolor": "#F8FAFC",
            "label_style": ft.TextStyle(color=AppColors.TEXT_SUB, size=12)
        }

        # 3. UI CONTROLS
        self.item_code = ft.TextField(label="Item Code *", width=100, **self.style_args)
        self.item_order = ft.TextField(label="Item Order", width=100, keyboard_type=ft.KeyboardType.NUMBER, value="", **self.style_args)
        self.brand_dd = ft.Dropdown(label="Brand Name", width=100, options=[], **self.style_args)
        self.brand_name = self.brand_dd # Alias
        self.variety = ft.TextField(label="Variety", width=200, **self.style_args)
        self.style_dd = ft.Dropdown(label="Style", width=100, options=[], **self.style_args)
        self.style = self.style_dd # Alias
        self.item_name = ft.TextField(label="Item Name *", width=350, **self.style_args)
        self.hsn_code = ft.TextField(label="HSN Code", width=160, **self.style_args)
        self.tax_dd   = ft.Dropdown(label="Tax Slab", width=200, on_change=self.on_tax_change, **self.style_args)
        self.tax_details = ft.Text("", size=11, color=AppColors.TEXT_SUB, italic=True)
        self.all_taxes = []
        self.inner_box_count = ft.TextField(label="Inner", width=80, value="1", **self.style_args)
        self.outer_box_qty = ft.TextField(label="Outer", width=80, value="1", **self.style_args)
        self.box_type = ft.Dropdown(
            label="Box Pack Type", width=160, value="Single Box Pack", **self.style_args,
            options=[
                ft.dropdown.Option("Single Box Pack"),
                ft.dropdown.Option("Master Carton"),
                ft.dropdown.Option("Polybag"),
                ft.dropdown.Option("Hanger Pack")
            ]
        )
        self.status_radio = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="Approved", label="Approved"), ft.Radio(value="Blocked", label="Blocked")], spacing=20),
            value="Approved"
        )
        self.item_type = ft.Dropdown(
            label="Item Type", width=160, value="Sales", **self.style_args,
            options=[ft.dropdown.Option("Sales"), ft.dropdown.Option("Supplies"), ft.dropdown.Option("Both")]
        )
        self.reason = ft.TextField(label="Reason/Remarks", multiline=True, min_lines=2, max_lines=3, expand=True, **self.style_args)

        # 4. SUB-MODAL OVERLAY UI
        self.sub_modal_content = ft.Column(spacing=20, tight=True)
        self.sub_modal_title = ft.Text("", weight="bold", size=16)
        self.sub_modal_box = ft.Container(
            content=ft.Column([
                ft.Row([self.sub_modal_title, ft.IconButton(ft.icons.CLOSE, on_click=lambda _: self.close_sub_modal())], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1),
                self.sub_modal_content
            ], spacing=15, tight=True),
            bgcolor=ft.colors.WHITE, padding=25, border_radius=12, width=400,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.colors.with_opacity(0.3, "black"))
        )
        self.sub_modal_overlay = ft.Container(
            content=self.sub_modal_box, bgcolor=ft.colors.with_opacity(0.5, "black"),
            visible=False, expand=True, alignment=ft.alignment.center, on_click=lambda _: self.close_sub_modal()
        )

        # 5. BUTTONS & HELPER FUNCTIONS
        self.btn_add_brand = ft.IconButton(ft.icons.ADD_CIRCLE, tooltip="Add New Brand")
        self.btn_add_style = ft.IconButton(ft.icons.ADD_CIRCLE, tooltip="Add New Style")
        self._setup_add_functions()

        self.size_matrix_section = ft.Container(
            content=ft.Column([
                ft.Text("SELECTED SIZES", weight="bold", size=10, color=AppColors.PRIMARY, style=ft.TextStyle(letter_spacing=1.0)),
                self.size_matrix_grid
            ], spacing=8),
            visible=False, padding=15, border=ft.border.all(1, "#F1F5F9"), border_radius=AppStyles.RADIUS, bgcolor="#F8FAFC"
        )

        # 6. ASSEMBLE MAIN CONTENT
        main_form = ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    ft.Row([self.item_code, self.item_order], spacing=12),
                    ft.Row([ft.Row([self.brand_dd, self.btn_add_brand], spacing=0), self.variety, ft.Row([self.style_dd, self.btn_add_style], spacing=0)], spacing=12),
                    ft.Row([self.item_name], spacing=12),
                    ft.Row([
                        self.inner_box_count, self.outer_box_qty, self.box_type, self.hsn_code,
                        ft.Column([self.tax_dd, self.tax_details], spacing=2)
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                    # Size Section
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("SIZE", weight="bold", size=10, color=AppColors.PRIMARY, style=ft.TextStyle(letter_spacing=1.0)),
                                ft.TextButton("All", on_click=self.select_all, height=30),
                                ft.TextButton("None", on_click=self.unselect_all, height=30),
                                ft.VerticalDivider(width=1),
                                ft.TextButton("S-3XL", on_click=lambda _: self.select_range(["S", "M", "L", "XL", "XXL", "XXXL", "2XL", "3XL"]), height=30),
                                ft.TextButton("32-42", on_click=lambda _: self.select_range([str(x) for x in range(32, 43, 2)]), height=30),
                                ft.TextButton("20-30", on_click=lambda _: self.select_range([str(x) for x in range(20, 31, 2)]), height=30),
                                ft.Container(expand=True),
                                ft.TextButton("New Size", icon=ft.icons.ADD, on_click=lambda _: self.btn_add_size_action(None), height=30),
                            ], spacing=10),
                            ft.Container(content=self.size_grid_row, border=ft.border.all(1, "#F1F5F9"), border_radius=AppStyles.BUTTON_RADIUS, bgcolor="#F8FAFC", padding=10)
                        ], spacing=4)
                    ),
                    ft.Row([self.status_radio, self.item_type], spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([ft.Container(content=self.reason, expand=True)]),
                    self.size_matrix_section,
                    ft.Row([
                        ft.ElevatedButton("Save Item", icon=ft.icons.SAVE, on_click=self._submit, style=AppStyles.primary_button_style(), height=45),
                        ft.TextButton("Clear", icon=ft.icons.REFRESH, on_click=self.clear, style=AppStyles.secondary_button_style())
                    ], spacing=12),
                ],
                spacing=8, scroll=ft.ScrollMode.AUTO, expand=True
            )
        )

        self.controls = [main_form, self.sub_modal_overlay]

    def _setup_add_functions(self):
        def add_custom_brand(e):
            txt = ft.TextField(label="New Brand Name", autofocus=True, on_submit=lambda _: save_new(None))
            def save_new(e):
                val = txt.value.strip()
                if val:
                    if not any(o.key == val for o in self.brand_dd.options):
                        self.brand_dd.options.append(ft.dropdown.Option(val))
                    self.brand_dd.value = val
                    self.close_sub_modal(); self.brand_dd.update()
            self.open_sub_modal("Add New Brand", txt, save_new)

        def add_custom_style(e):
            txt = ft.TextField(label="New Style Name", autofocus=True, on_submit=lambda _: save_new(None))
            def save_new(e):
                val = txt.value.strip()
                if val:
                    if not any(o.key == val for o in self.style_dd.options):
                        self.style_dd.options.append(ft.dropdown.Option(val))
                    self.style_dd.value = val
                    self.close_sub_modal(); self.style_dd.update()
            self.open_sub_modal("Add New Style", txt, save_new)

        def add_custom_size(e):
            txt = ft.TextField(label="Size (e.g. S, 32, XL)", autofocus=True, on_submit=lambda _: save_new(None))
            def save_new(e):
                val = txt.value.strip().upper()
                if val and val not in self.size_checkboxes:
                    cb = ft.Checkbox(label=val, value=True, on_change=self.on_size_change)
                    self.size_checkboxes[val] = cb
                    self._render_size_grid(); self.close_sub_modal(); self.rebuild_size_matrix()
            self.open_sub_modal("Add Custom Size", txt, save_new)

        self.btn_add_brand.on_click = add_custom_brand
        self.btn_add_style.on_click = add_custom_style
        self.btn_add_size_action = add_custom_size

    def open_sub_modal(self, title, control, on_save):
        self.sub_modal_title.value = title
        self.sub_modal_content.controls = [
            control,
            ft.Row([ft.TextButton("Cancel", on_click=lambda _: self.close_sub_modal()), ft.ElevatedButton("Add", on_click=on_save, style=AppStyles.primary_button_style())], alignment=ft.MainAxisAlignment.END, spacing=10)
        ]
        self.sub_modal_overlay.visible = True; self.sub_modal_overlay.update()

    def close_sub_modal(self):
        self.sub_modal_overlay.visible = False; self.sub_modal_overlay.update()

    def on_size_change(self, e):
        self.rebuild_size_matrix()

    def select_all(self, e):
        for cb in self.size_checkboxes.values(): cb.value = True
        self.rebuild_size_matrix(); self.update()

    def unselect_all(self, e):
        for cb in self.size_checkboxes.values(): cb.value = False
        self.rebuild_size_matrix(); self.update()

    def select_range(self, sizes):
        """Clears current selection and selects only the provided range."""
        for cb in self.size_checkboxes.values():
            cb.value = False
        for s in sizes:
            if s in self.size_checkboxes:
                self.size_checkboxes[s].value = True
            else:
                # If size doesn't exist, add it
                cb = ft.Checkbox(label=s, value=True, on_change=self.on_size_change)
                self.size_checkboxes[s] = cb
        self._render_size_grid()
        self.rebuild_size_matrix()
        self.update()

    def load_metadata(self, brands, styles, sizes, taxes=None):
        self.brand_dd.options = [ft.dropdown.Option(b) for b in brands]
        self.style_dd.options = [ft.dropdown.Option(s) for s in styles]
        self.all_taxes = taxes or []
        if taxes:
            self.tax_dd.options = [ft.dropdown.Option(key=str(t["id"]), text=t["name"]) for t in taxes]
        checked_list = [s for s, cb in self.size_checkboxes.items() if cb.value]
        self.size_checkboxes.clear(); self.size_grid_row.controls.clear()
        
        def size_sort_key(s):
            s = str(s).upper().strip()
            order = ["FREE", "XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "2XL", "3XL", "4XL", "5XL"]
            if s in order: return (0, order.index(s))
            try: return (1, float(s))
            except ValueError: return (2, s)

        for s in sorted(list(set(sizes)), key=size_sort_key):
            cb = ft.Checkbox(label=s, value=(s in checked_list), on_change=self.on_size_change)
            self.size_checkboxes[s] = cb
        self._render_size_grid(); self.rebuild_size_matrix()
        try: self.update()
        except: pass

    def on_tax_change(self, e):
        tid = self.tax_dd.value
        if not tid:
            self.tax_details.value = ""
            self.update()
            return
        tax = next((t for t in self.all_taxes if str(t["id"]) == tid), None)
        if tax:
            self.tax_details.value = f"{tax.get('tax_type','GST')} | C:{tax.get('cgst_percent',0)}% S:{tax.get('sgst_percent',0)}% I:{tax.get('igst_percent',0)}%"
            if tax.get("hsn_code") and not self.hsn_code.value:
                self.hsn_code.value = tax["hsn_code"]
            self.update()

    def _render_size_grid(self):
        self.size_grid_row.controls.clear()
        def size_sort_key(s):
            s = str(s).upper().strip()
            order = ["FREE", "XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "2XL", "3XL", "4XL", "5XL"]
            if s in order: return (0, order.index(s))
            try: return (1, float(s))
            except ValueError: return (2, s)
        sorted_keys = sorted(self.size_checkboxes.keys(), key=size_sort_key)
        for i in range(0, len(sorted_keys), 6):
            chunk = sorted_keys[i : i + 6]
            col = ft.Column(controls=[self.size_checkboxes[s] for s in chunk if s in self.size_checkboxes], spacing=2)
            self.size_grid_row.controls.append(col)
        try:
            if self.size_grid_row.page: self.size_grid_row.update()
        except: pass

    def rebuild_size_matrix(self):
        selected_sizes = [s for s, cb in self.size_checkboxes.items() if cb.value]
        self.size_matrix_grid.controls.clear()
        old_stocks = {k: v.value for k, v in self.opening_stock_inputs.items()}
        self.opening_stock_inputs.clear()
        if not selected_sizes:
            self.size_matrix_section.visible = False
        else:
            self.size_matrix_section.visible = True
            for s in selected_sizes:
                stk_field = ft.TextField(label="Stock Qty", value=old_stocks.get(s, ""), width=100, dense=True, text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER, visible=False)
                self.opening_stock_inputs[s] = stk_field
                self.size_matrix_grid.controls.append(ft.Container(content=ft.Column([ft.Text(s, size=11, weight="bold", color=AppColors.TEXT_HEADER), stk_field], spacing=7, horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=12, bgcolor=AppColors.BG_CARD, border_radius=8, shadow=AppStyles.CARD_SHADOW, border=ft.border.all(1, "#F0F0F0")))
        try: self.update()
        except: pass

    def get_values(self):
        selected_sizes = [size for size, cb in self.size_checkboxes.items() if cb.value]
        opening_stock = {s: int(float(self.opening_stock_inputs[s].value or 0)) for s in selected_sizes if s in self.opening_stock_inputs}
        return {
            "item_code": self.item_code.value or "", "item_order": int(self.item_order.value or 1),
            "brand_name": self.brand_name.value or "", "variety": self.variety.value or "",
            "style": self.style.value or "", "item_name": self.item_name.value or "",
            "sizes": selected_sizes, "pcs_per_inner_box": int(self.inner_box_count.value or 1),
            "boxes_per_outer_box": int(self.outer_box_qty.value or 1), 
            "box_type": self.box_type.value or "Single Box Pack",
            "hsn_code": self.hsn_code.value or "",
            "tax_id": self.tax_dd.value,
            "is_approved": self.status_radio.value == "Approved", "is_blocked": self.status_radio.value == "Blocked",
            "reason": self.reason.value or "", "opening_stock": opening_stock,
            "item_type": self.item_type.value or "Sales",
        }

    def set_values(self, data: dict):
        self.item_code.value = data.get("item_code", "")
        self.item_order.value = str(data.get("item_order", 1))
        b_val = data.get("brand_name", "")
        if b_val and not any(o.key == b_val for o in self.brand_dd.options): self.brand_dd.options.append(ft.dropdown.Option(b_val))
        self.brand_dd.value = b_val
        self.variety.value = data.get("variety", "")
        s_val = data.get("style", "")
        if s_val and not any(o.key == s_val for o in self.style_dd.options): self.style_dd.options.append(ft.dropdown.Option(s_val))
        self.style_dd.value = s_val
        self.item_name.value = data.get("item_name", "")
        self.inner_box_count.value = str(data.get("pcs_per_inner_box", 1))
        self.outer_box_qty.value = str(data.get("boxes_per_outer_box", 1))
        self.box_type.value = data.get("box_type", "Single Box Pack")
        self.hsn_code.value = data.get("hsn_code", "")
        if data.get("tax_id"):
            self.tax_dd.value = str(data["tax_id"])
        self.item_type.value = data.get("item_type", "Sales")
        self.status_radio.value = "Blocked" if data.get("is_blocked", False) else "Approved"
        self.reason.value = data.get("reason", "")
        for cb in self.size_checkboxes.values(): cb.value = False
        
        sizes_raw = data.get("sizes")
        if sizes_raw is None:
            sizes_raw = []
        elif isinstance(sizes_raw, str):
            import json
            try: sizes_raw = json.loads(sizes_raw)
            except: sizes_raw = []
            
        for s in sizes_raw:
            if s in self.size_checkboxes: self.size_checkboxes[s].value = True
        self.rebuild_size_matrix()
        stock_data = data.get("opening_stock", {})
        for k, v in stock_data.items():
            if k in self.opening_stock_inputs: self.opening_stock_inputs[k].value = str(v)
        try: self.update()
        except: pass

    def clear(self, e=None):
        self.item_code.value = ""; self.item_order.value = ""; self.brand_name.value = ""; self.variety.value = ""; self.style.value = ""; self.item_name.value = ""; self.inner_box_count.value = "1"; self.outer_box_qty.value = "1"; self.box_type.value = "Single Box Pack"; self.hsn_code.value = ""; self.status_radio.value = "Approved"; self.reason.value = ""
        for cb in self.size_checkboxes.values(): cb.value = False
        try: self.update()
        except: pass

    def _submit(self, e):
        if not self.item_code.value or not self.item_name.value:
            self.item_code.error_text = "Required" if not self.item_code.value else None
            self.item_name.error_text = "Required" if not self.item_name.value else None
            try: self.update()
            except: pass
            return
        self.item_code.error_text = None; self.item_name.error_text = None
        if self.on_submit: self.on_submit(self.get_values())
