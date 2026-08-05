import flet as ft
from datetime import datetime
from core.theme import AppColors, AppStyles
from components.size_matrix import sort_sizes

class PriceListForm(ft.Stack):
    def __init__(self, on_submit=None):
        super().__init__()
        self.expand = True
        self.on_submit = on_submit
        
        self.all_items = []
        self.item_prices_state = {}
        self.rate_inputs = {}

        # Internal Modal Layer
        self.modal_layer = ft.Container(
            content=ft.Text("Modal"),
            visible=False,
            bgcolor="#80000000",
            expand=True,
            alignment=ft.alignment.center,
        )

        # =============================================
        # HEADER FIELDS
        # =============================================
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

        self.list_name = ft.TextField(label="Price List Name *", width=250, **self.style_args)
        self.effective_date = ft.TextField(
            label="Effective Date (YYYY-MM-DD) *", width=200,
            value=datetime.now().strftime("%Y-%m-%d"), **self.style_args
        )
        self.price_type = ft.Dropdown(
            label="Primary Price Type", width=160,
            value="Wholesale",
            options=[
                ft.dropdown.Option("Wholesale"),
                ft.dropdown.Option("Retail"),
                ft.dropdown.Option("MRP"),
            ], **self.style_args
        )

        # =============================================
        # ITEM SELECTION
        # =============================================
        self.item_dd = ft.Dropdown(
            label="Select Item to Setup Pricing", width=350,
            on_change=self.on_item_select, **self.style_args
        )
        self.bulk_btn = ft.OutlinedButton(
            "Bulk Apply to Multiple Items",
            icon=ft.icons.LIBRARY_ADD_CHECK_ROUNDED,
            on_click=self._open_bulk_picker,
            style=ft.ButtonStyle(color=AppColors.PRIMARY, side=ft.BorderSide(1, AppColors.PRIMARY))
        )

        # =============================================
        # SIZE MATRIX (Dynamic per Item)
        # =============================================
        self.rate_inputs = {}  # {size: {"wholesale": TextField, "retail": TextField, "mrp": TextField}}
        self.matrix_grid = ft.Row(wrap=True, spacing=10)
        self.save_item_btn = ft.ElevatedButton(
            "Update Item Pricing", icon=ft.icons.CHECK_CIRCLE,
            on_click=self._save_current_grid_to_state,
            style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_400, color=ft.colors.WHITE)
        )
        self.matrix_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("ITEM SIZE PRICING", weight="bold", size=10, color=AppColors.PRIMARY, style=ft.TextStyle(letter_spacing=1.0)),
                    ft.Container(expand=True),
                    self.save_item_btn
                ]),
                self.matrix_grid
            ], spacing=8),
            visible=False,
            padding=15,
            border=ft.border.all(1, "#F1F5F9"),
            border_radius=AppStyles.RADIUS,
            bgcolor="#F8FAFC"
        )

        # =============================================
        # SUMMARY TABLE
        # =============================================
        self.pricing_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Item Code")),
                ft.DataColumn(ft.Text("Item Name")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[],
            border=ft.border.all(1, "#F1F5F9"),
            border_radius=8,
            heading_row_color="#F8FAFC",
        )
        self.summary_section = ft.Container(
            content=ft.Column([
                ft.Text("ITEMS IN THIS PRICE LIST", weight="bold", size=12, color=AppColors.TEXT_HEADER),
                self.pricing_table
            ], spacing=10),
            visible=False
        )
        
        # We need a way to store multiple items' prices before submitting, 
        # or we assume we edit ONE item's pricing per submission?
        # Actually, a Price List typically holds many items. 
        # To keep UI simple, let's allow editing existing rates by just selecting an item and updating the matrix.
        # But for submission, we want to return the structured dictionary of everything filled out.
        # So we'll maintain a state of `self.item_prices_state = {item_id: {size: {rates...}}}`
        self.item_prices_state = {}

        # =============================================
        # BUTTONS
        # =============================================
        save_btn = ft.ElevatedButton(
            "Save", icon=ft.icons.SAVE, on_click=self._submit,
            style=AppStyles.primary_button_style(), height=45
        )
        save_as_btn = ft.ElevatedButton(
            "Save As", icon=ft.icons.COPY, on_click=self._save_as,
            style=ft.ButtonStyle(
                bgcolor=AppColors.WARNING, color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=AppStyles.BUTTON_RADIUS)
            ), height=45
        )
        clear_btn = ft.TextButton(
            "Clear", icon=ft.icons.REFRESH, on_click=self.clear,
            style=AppStyles.secondary_button_style()
        )

        # =============================================
        # LAYOUT
        # =============================================
        self.form_container = ft.Container(
            padding=10,
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Row([self.list_name, self.effective_date, self.price_type], spacing=12, wrap=True),
                    ft.Divider(height=1, color="grey300"),
                    ft.Row([self.item_dd, self.bulk_btn], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
                    self.matrix_section,
                    self.summary_section,
                    ft.Divider(height=1, color="grey300"),
                    ft.Row([save_btn, save_as_btn, clear_btn], spacing=12, wrap=True),
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
                expand=True
            )
        )

        self.controls = [
            self.form_container,
            self.modal_layer
        ]

    def load_metadata(self, items):
        """Loads items for the dropdown. items should be a list of dicts."""
        self.all_items = items
        self.item_dd.options.clear()
        
        for item in self.all_items:
            label = f"{item.get('item_name')} ({item.get('item_code')})"
            self.item_dd.options.append(ft.dropdown.Option(key=str(item.get("id")), text=label))
            
        try:
            self.update()
        except Exception:
            pass

    def on_item_select(self, e):
        """When an item is selected, render the size grid for it."""
        item_id = self.item_dd.value
        if not item_id:
            self.matrix_section.visible = False
            self.update()
            return
            
        # Optional: Save current matrix state to state dict before switching
        # Let's skip auto-saving on switch for now to keep it simple, 
        # or we could save it so users can configure multiple items then Save.
        # Doing multiple items before saving is best. Let's auto-save current grid if populated.
        
        item = next((i for i in self.all_items if str(i.get("id")) == item_id), None)
        if not item:
            return
            
        sizes = item.get("sizes", [])
        
        self.rate_inputs.clear()
        self.matrix_grid.controls.clear()
        
        existing_rates = self.item_prices_state.get(item_id, {})
        
        if not sizes:
            self.matrix_grid.controls.append(ft.Text("No sizes configured for this item.", color="red"))
        else:
            for s in sort_sizes(sizes):
                s_rates = existing_rates.get(s, {})
                def _fmt(val):
                    if val is None or val == 0 or val == 0.0 or val == "": return ""
                    return str(val)
                
                ws = ft.TextField(label="Wholesale", value=_fmt(s_rates.get("wholesale_rate")), width=85, **self.style_args, text_align=ft.TextAlign.RIGHT, keyboard_type=ft.KeyboardType.NUMBER)
                rt = ft.TextField(label="Retail", value=_fmt(s_rates.get("retail_rate")), width=85, **self.style_args, text_align=ft.TextAlign.RIGHT, keyboard_type=ft.KeyboardType.NUMBER)
                mrp = ft.TextField(label="MRP", value=_fmt(s_rates.get("mrp_rate")), width=85, **self.style_args, text_align=ft.TextAlign.RIGHT, keyboard_type=ft.KeyboardType.NUMBER)
                
                self.rate_inputs[s] = {"wholesale": ws, "retail": rt, "mrp": mrp}
                
                self.matrix_grid.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(s, size=11, weight="bold", color=AppColors.TEXT_HEADER),
                            ws, rt, mrp
                        ], spacing=7, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12,
                        bgcolor=AppColors.BG_CARD,
                        border_radius=8,
                        shadow=AppStyles.CARD_SHADOW,
                        border=ft.border.all(1, "#F0F0F0")
                    )
                )
                
        self.matrix_section.visible = True
        self._update_summary_table()
        try:
            self.update()
        except:
            pass
            
    def _save_current_grid_to_state(self, e=None):
        """Forces the current UI table inputs onto the Python state dict"""
        item_id = self.item_dd.value
        if not item_id or not self.matrix_section.visible:
            return
            
        size_dict = {}
        for s, inputs in self.rate_inputs.items():
            try:
                ws = float(inputs["wholesale"].value or 0)
                rt = float(inputs["retail"].value or 0)
                mrp = float(inputs["mrp"].value or 0)
            except ValueError:
                ws = rt = mrp = 0.0
                
            size_dict[s] = {
                "wholesale_rate": ws,
                "retail_rate": rt,
                "mrp_rate": mrp
            }
            
        self.item_prices_state[item_id] = size_dict
        self._update_summary_table()
        if e: # if called from button
            self.page.snack_bar = ft.SnackBar(ft.Text("Pricing Updated for this item"), bgcolor="green")
            self.page.snack_bar.open = True
            self.update()

    def _update_summary_table(self):
        self.pricing_table.rows = []
        if not self.item_prices_state:
            self.summary_section.visible = False
            return
            
        self.summary_section.visible = True
        for iid, pricing in self.item_prices_state.items():
            item = next((i for i in self.all_items if str(i.get("id")) == iid), None)
            if not item: continue
            
            # Check if any price is actually set
            has_pricing = any(any(v > 0 for v in s.values()) for s in pricing.values())
            status_icon = ft.Icon(ft.icons.CHECK_CIRCLE, color="green", size=16) if has_pricing else ft.Icon(ft.icons.CIRCLE_OUTLINED, color="grey400", size=16)
            
            self.pricing_table.rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(item.get("item_code", "-"))),
                    ft.DataCell(ft.Text(item.get("item_name", "-"))),
                    ft.DataCell(ft.Row([status_icon, ft.Text("Configured" if has_pricing else "Pending", size=12)])),
                    ft.DataCell(ft.Row([
                        ft.IconButton(ft.icons.EDIT, icon_size=16, on_click=lambda _, id=iid: self._load_item_to_edit(id), tooltip="Edit Pricing"),
                        ft.IconButton(ft.icons.DELETE, icon_size=16, icon_color="red400", on_click=lambda _, id=iid: self._remove_item_from_list(id), tooltip="Remove from List")
                    ])),
                ]
            ))

    def _load_item_to_edit(self, iid):
        self.item_dd.value = str(iid)
        self.on_item_select(None)

    def _remove_item_from_list(self, iid):
        if str(iid) in self.item_prices_state:
            del self.item_prices_state[str(iid)]
        if self.item_dd.value == str(iid):
            self.item_dd.value = None
            self.matrix_section.visible = False
        self._update_summary_table()
        self.update()

    def get_values(self):
        self._save_current_grid_to_state() # Flush current active grid
        
        return {
            "list_name": self.list_name.value or "",
            "effective_date": self.effective_date.value or "",
            "price_type": self.price_type.value or "Wholesale",
            "items_pricing": self.item_prices_state
        }

    def set_values(self, data: dict, items_pricing: dict = None):
        self.list_name.value = data.get("list_name", "")
        if data.get("effective_date"):
            self.effective_date.value = str(data.get("effective_date"))
        self.price_type.value = data.get("price_type", "Wholesale")
        
        self.item_prices_state = items_pricing or {}
        self.item_dd.value = None
        self.matrix_section.visible = False
        self._update_summary_table()
        
        try:
            self.update()
        except:
            pass

    def clear(self, e=None):
        self.list_name.value = ""
        self.effective_date.value = datetime.now().strftime("%Y-%m-%d")
        self.price_type.value = "Wholesale"
        self.item_prices_state = {}
        self.item_dd.value = None
        self.matrix_section.visible = False
        self.summary_section.visible = False
        self.list_name.error_text = None
        try:
            self.update()
        except:
            pass

    def _save_as(self, e):
        if not self.list_name.value:
            self.list_name.error_text = "Enter a NEW name for cloning"
            self.update()
            return
        self.list_name.error_text = None
        self._save_current_grid_to_state()
        
        # We pass a flag to tell the parent that this is a CLONE (ignore edit_id)
        if self.on_submit:
            data = self.get_values()
            data["is_clone"] = True
            self.on_submit(data)

    def _submit(self, e):
        if not self.list_name.value:
            self.list_name.error_text = "Required"
            self.update()
            return
        self.list_name.error_text = None
        self._save_current_grid_to_state()
        
        if self.on_submit:
            self.on_submit(self.get_values())

    # =============================================
    # BULK SELECT LOGIC
    # =============================================
    def _open_bulk_picker(self, e):
        if not self.matrix_section.visible:
            self.page.snack_bar = ft.SnackBar(ft.Text("Please select and configure pricing for one item first!"), bgcolor="orange")
            self.page.snack_bar.open = True
            self.page.update()
            return

        search_field = ft.TextField(label="Search Items...", prefix_icon=ft.icons.SEARCH, dense=True, on_change=lambda e: _update_list(e.control.value))
        items_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
        selected_ids = set()

        def _update_list(search=""):
            items_col.controls = []
            current_id = self.item_dd.value
            for item in self.all_items:
                iid = str(item["id"])
                if iid == current_id: continue # Skip currently active item
                
                label = f"{item['item_name']} ({item['item_code']})"
                if search.lower() in label.lower():
                    cb = ft.Checkbox(
                        label=label,
                        value=iid in selected_ids,
                        data=iid,
                        on_change=lambda e: _toggle_id(e.control.data, e.control.value)
                    )
                    items_col.controls.append(cb)
            self.update()

        def _toggle_id(iid, val):
            if val: selected_ids.add(iid)
            else: selected_ids.discard(iid)

        def _confirm_bulk(e):
            if not selected_ids:
                _close_modal(None)
                return
            
            # Just add items to the state with empty pricing (so they can be customized)
            for iid in selected_ids:
                if iid not in self.item_prices_state:
                    self.item_prices_state[iid] = {}
            
            self._update_summary_table()
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Added {len(selected_ids)} items to the list. You can now edit their prices individually."), bgcolor="green")
            self.page.snack_bar.open = True
            _close_modal(None)

        def _close_modal(e):
            self.modal_layer.visible = False
            self.update()

        def _select_all(e):
            current_id = self.item_dd.value
            for item in self.all_items:
                iid = str(item["id"])
                if iid != current_id: selected_ids.add(iid)
            _update_list(search_field.value)

        _update_list()

        dialog = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Bulk Add Items", weight="bold", size=16),
                    ft.IconButton(ft.icons.CLOSE, on_click=_close_modal)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Select multiple items to add them to this price list. You can then set their prices individually.", size=12, color=AppColors.TEXT_SUB),
                search_field,
                ft.Row([
                    ft.TextButton("Select All", on_click=_select_all),
                    ft.TextButton("Clear All", on_click=lambda _: (selected_ids.clear(), _update_list(search_field.value))),
                ]),
                ft.Container(items_col, height=300, border=ft.border.all(1, "#E2E8F0"), border_radius=8, padding=5),
                ft.Row([
                    ft.TextButton("Cancel", on_click=_close_modal),
                    ft.ElevatedButton("Add to Price List", icon=ft.icons.ADD, on_click=_confirm_bulk, style=AppStyles.primary_button_style())
                ], alignment=ft.MainAxisAlignment.END)
            ], spacing=15),
            bgcolor=ft.colors.WHITE,
            padding=20,
            border_radius=12,
            width=500,
            shadow=ft.BoxShadow(blur_radius=20, color="#40000000"),
        )

        self.modal_layer.content = dialog
        self.modal_layer.visible = True
        self.update()
