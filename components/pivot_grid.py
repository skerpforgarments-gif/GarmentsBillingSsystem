import flet as ft
from core.theme import AppColors, AppStyles


class PivotGridRow(ft.Row):
    def __init__(self, item_code, item_name, sizes_array, rate, pcs_per_box, on_total_change):
        super().__init__()
        self.spacing = 0
        self.vertical_alignment = ft.CrossAxisAlignment.CENTER
        
        self.item_code = item_code
        self.item_name = item_name
        self.sizes_array = sizes_array
        self.rate = rate
        self.pcs_per_box = pcs_per_box if pcs_per_box > 0 else 1
        self.on_total_change = on_total_change

        # Styling constants for density
        CELL_WIDTH = 50
        TEXT_SIZE = 12

        # -----------------------------
        # Static Columns
        # -----------------------------
        self.controls.append(ft.Container(
            content=ft.Text(item_code, size=TEXT_SIZE, weight="bold", color=AppColors.TEXT_HEADER),
            width=60, padding=5, border=ft.border.all(1, "#F1F5F9")
        ))
        self.controls.append(ft.Container(
            content=ft.Text(item_name, size=TEXT_SIZE, no_wrap=True, color=AppColors.TEXT_SUB),
            width=150, padding=5, border=ft.border.all(1, "#F1F5F9")
        ))

        # -----------------------------
        # Dynamic Size Columns (Inputs)
        # -----------------------------
        self.size_inputs = {}
        for size in sizes_array:
            tf = ft.TextField(
                value="",
                text_size=TEXT_SIZE,
                dense=True,
                content_padding=5,
                border=ft.InputBorder.NONE,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=self.calculate_row
            )
            self.size_inputs[size] = tf
            
            # Wrap in container for grid look
            self.controls.append(ft.Container(
                content=tf, width=CELL_WIDTH, border=ft.border.all(1, "#F1F5F9"),
                bgcolor="#F8FAFC"
            ))

        # -----------------------------
        # Computed Columns
        # -----------------------------
        self.total_pcs_text = ft.Text("0", size=TEXT_SIZE, color=AppColors.TEXT_HEADER)
        self.total_boxes_text = ft.Text("0", size=TEXT_SIZE, color=AppColors.TEXT_HEADER)
        self.rate_input = ft.TextField(
            value=str(rate), text_size=TEXT_SIZE, dense=True, 
            content_padding=5, border=ft.InputBorder.NONE,
            on_change=self.calculate_row,
            cursor_color=AppColors.PRIMARY,
        )
        self.amount_text = ft.Text("0.00", size=TEXT_SIZE, weight="bold", color=AppColors.PRIMARY)

        # Append computed column containers
        self.controls.extend([
            ft.Container(content=self.total_pcs_text, width=60, padding=5, border=ft.border.all(1, "#F1F5F9"), alignment=ft.alignment.center_right),
            ft.Container(content=self.total_boxes_text, width=60, padding=5, border=ft.border.all(1, "#F1F5F9"), alignment=ft.alignment.center_right),
            ft.Container(content=self.rate_input, width=60, border=ft.border.all(1, "#F1F5F9")),
            ft.Container(content=self.amount_text, width=80, padding=5, border=ft.border.all(1, "#F1F5F9"), alignment=ft.alignment.center_right)
        ])

    def calculate_row(self, e):
        total_qty = 0
        
        # Sum all size inputs
        for size, tf in self.size_inputs.items():
            if tf.value.isdigit():
                total_qty += int(tf.value)

        # Parse Rate
        try:
            current_rate = float(self.rate_input.value)
        except ValueError:
            current_rate = 0.0

        # Calculations
        boxes = round(total_qty / self.pcs_per_box, 2)
        amount = round(total_qty * current_rate, 2)

        # Update UI texts
        self.total_pcs_text.value = str(total_qty)
        self.total_boxes_text.value = str(boxes)
        self.amount_text.value = f"{amount:.2f}"
        
        self.update()

        # Trigger parent update
        if self.on_total_change:
            self.on_total_change()

    def get_data(self):
        """Returns the extracted data for database insertion"""
        data = []
        try:
            current_rate = float(self.rate_input.value)
        except:
            current_rate = 0.0

        for size, tf in self.size_inputs.items():
            if tf.value.isdigit() and int(tf.value) > 0:
                qty = int(tf.value)
                data.append({
                    "item_code": self.item_code,
                    "size_value": size,
                    "qty_pieces": qty,
                    "qty_boxes": round(qty / self.pcs_per_box, 2),
                    "rate": current_rate,
                    "amount": round(qty * current_rate, 2)
                })
        return data


class PivotGrid(ft.Container):
    def __init__(self):
        super().__init__()
        self.border = ft.border.all(1, "#F1F5F9")
        self.border_radius = AppStyles.RADIUS
        self.padding = 0
        self.expand = True
        self.bgcolor = AppColors.BG_CARD

        # Header Row (Will be built dynamically based on sizes)
        self.header_row = ft.Row(spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Body (Scrollable list of rows)
        self.body_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        self.content = ft.Column(
            controls=[
                ft.Container(
                    content=self.header_row, 
                    bgcolor="#F8FAFC", 
                    padding=0,
                    border=ft.border.only(bottom=ft.BorderSide(1, "#F1F5F9"))
                ),
                self.body_column
            ],
            spacing=0,
            expand=True
        )

        self.all_sizes = [] # Tracks unique sizes across all added items
        self.rows_data = []

    def build_header(self):
        self.header_row.controls.clear()
        
        CELL_WIDTH = 50
        TEXT_SIZE = 12

        # Fixed Header cols
        self.header_row.controls.append(ft.Container(content=ft.Text("IC CODE", size=10, weight="bold", color=AppColors.TEXT_HEADER), width=60, padding=5))
        self.header_row.controls.append(ft.Container(content=ft.Text("DESCRIPTION", size=10, weight="bold", color=AppColors.TEXT_HEADER), width=150, padding=5))

        # Dynamic Size cols
        for size in self.all_sizes:
            self.header_row.controls.append(ft.Container(
                content=ft.Text(str(size), size=10, weight="bold", text_align="center", color=AppColors.PRIMARY), 
                width=CELL_WIDTH, padding=5
            ))

        # Computed Header cols
        self.header_row.controls.extend([
            ft.Container(content=ft.Text("PCS", size=10, weight="bold", color=AppColors.TEXT_HEADER), width=60, padding=5),
            ft.Container(content=ft.Text("BOXES", size=10, weight="bold", color=AppColors.TEXT_HEADER), width=60, padding=5),
            ft.Container(content=ft.Text("RATE", size=10, weight="bold", color=AppColors.TEXT_HEADER), width=60, padding=5),
            ft.Container(content=ft.Text("AMOUNT", size=10, weight="bold", color=AppColors.PRIMARY), width=80, padding=5)
        ])

        if self.page:
            self.header_row.update()

    def add_item_row(self, item_code, item_name, sizes_array, rate, pcs_per_box, on_totals_changed_callback):
        # Merge new sizes into global tracking to keep header aligned
        for s in sizes_array:
            if s not in self.all_sizes:
                self.all_sizes.append(s)
        
        # Sort sizes (assuming numeric representation mostly)
        self.all_sizes.sort(key=lambda x: int(x) if str(x).isdigit() else x)
        self.build_header()

        # Add Row
        row = PivotGridRow(item_code, item_name, self.all_sizes, rate, pcs_per_box, on_totals_changed_callback)
        self.rows_data.append(row)
        self.body_column.controls.append(row)

        if self.page:
            self.update()

    def get_all_data(self):
        """Extracts flat list of all sizes inputted across all rows"""
        result = []
        for row in self.rows_data:
            result.extend(row.get_data())
        return result

    def get_grand_totals(self):
        grand_pcs = 0
        grand_amount = 0.0

        for row in self.rows_data:
            grand_pcs += int(row.total_pcs_text.value or 0)
            grand_amount += float(row.amount_text.value or 0)

        return grand_pcs, grand_amount
