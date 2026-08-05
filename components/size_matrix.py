import flet as ft
from core.theme import AppColors, AppStyles
from database.db import select

# Canonical size order for Tirupur garments
_ALPHA_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "4XL", "5XL"]

def _size_sort_key(s: str):
    """Return a sort key so sizes appear in natural order."""
    s = str(s).strip()
    if s.isdigit():
        return (0, int(s), s)          # numeric sizes: 28, 30, 32 …
    if s.upper() in _ALPHA_ORDER:
        return (1, _ALPHA_ORDER.index(s.upper()), s)  # alpha sizes: S M L …
    return (2, 0, s)                   # anything else: alphabetical

def sort_sizes(sizes):
    return sorted(sizes, key=_size_sort_key)

class SizeMatrixModal(ft.AlertDialog):
    def __init__(self, on_submit):
        super().__init__()
        self.on_submit = on_submit
        self.modal = True
        self.title = ft.Text("Select Item & Sizes")
        
        # --- Refs ---
        self.item_dd = ft.Dropdown(label="Search Item", width=600, on_change=self.on_item_select, **AppStyles.get_input_style())
        self.matrix_container = ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)
        self.price_list_id = None
        self.price_type = "Wholesale"  # Default
        
        self.content = ft.Container(
            content=ft.Column([
                ft.Row([self.item_dd], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=1, color="#F1F5F9"),
                self.matrix_container
            ], width=750, height=650, spacing=15),
            padding=20
        )
        
        self.actions = [
            ft.TextButton("Cancel", on_click=lambda _: self.close_modal()),
            ft.ElevatedButton("Add to Order", icon=ft.icons.ADD_SHOPPING_CART, on_click=self.submit, style=AppStyles.primary_button_style())
        ]
        
        self.matrix_data = {} # To store the text fields: {size_val: TextField}

    def reset(self):
        self.item_dd.value = None
        self.matrix_container.controls.clear()
        self.matrix_data.clear()
        if self.page: self.update()

    def close_modal(self, e=None):
        self.open = False
        if self.page: self.page.update()

    def load_items(self, items):
        self.item_dd.options = [ft.dropdown.Option(key=str(i["id"]), text=f"{i['item_name']} ({i['item_code']})") for i in items]
        if self.page: self.update()

    def on_tf_focus(self, e):
        if e.control.value == "0":
            e.control.value = ""
            e.control.update()

    def on_tf_blur(self, e):
        if e.control.value == "" or e.control.value is None:
            e.control.value = "0"
            e.control.update()

    def on_item_select(self, e):
        if not self.item_dd.value:
            return
            
        # Get prices for this item
        prices = select("price_list_items", {
            "price_list_id": self.price_list_id,
            "item_id": self.item_dd.value
        })
        
        # Group by rate
        rate_map = {}
        for p in prices:
            r = p.get("wholesale_rate" if self.price_type == "Wholesale" else "retail_rate", 0)
            if r not in rate_map: rate_map[r] = []
            rate_map[r].append(p.get("size_value"))

        self.matrix_container.controls.clear()
        self.matrix_data.clear()

        for rate, sizes in rate_map.items():
            size_controls = []
            for s in sort_sizes(sizes):
                tf = ft.TextField(
                    label=s, width=70, height=40, dense=True, 
                    text_size=12, text_align=ft.TextAlign.CENTER,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    value="0",
                    on_focus=self.on_tf_focus,
                    on_blur=self.on_tf_blur
                )
                self.matrix_data[s] = {"tf": tf, "rate": rate}
                size_controls.append(tf)
            
            self.matrix_container.controls.append(
                ft.Container(
                    padding=15,
                    bgcolor="#F8FAFC",
                    border_radius=10,
                    border=ft.border.all(1, "#E2E8F0"),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.PAYMENTS, size=16, color=AppColors.PRIMARY),
                            ft.Text(f"Rate: ₹{rate}", weight="bold", size=14, color=AppColors.TEXT_HEADER),
                        ], spacing=8),
                        ft.Row(size_controls, wrap=True, spacing=15, run_spacing=15)
                    ], spacing=12)
                )
            )
        
        if self.page: self.update()

    def submit(self, e):
        # Gather non-zero quantities
        results = []
        item_id = self.item_dd.value
        item_text = ""
        for opt in self.item_dd.options:
            if opt.key == item_id:
                item_text = opt.text
                break
        
        try:
            for size, data in self.matrix_data.items():
                qty = data["tf"].value
                if qty and qty.isdigit() and int(qty) > 0:
                    results.append({
                        "item_id": item_id,
                        "item_name": item_text,
                        "size": size,
                        "rate": data["rate"],
                        "qty": int(qty)
                    })
            
            if results:
                self.on_submit(results)
            self.close_modal()
        except Exception as ex:
            print(f"Matrix Submit Error: {ex}")
            self.close_modal()
