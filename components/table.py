import flet as ft
from core.theme import AppColors, AppStyles


class TableBuilder(ft.Container):
    def __init__(self, columns, data=None, on_edit=None, on_delete=None):
        super().__init__()

        self.expand = True
        self.bgcolor = AppColors.BG_CARD
        self.border_radius = AppStyles.RADIUS
        self.shadow = AppStyles.CARD_SHADOW
        self.border = ft.border.all(1, "#F0F0F0")
        self.padding = 0
        self.clip_behavior = ft.ClipBehavior.ANTI_ALIAS # Smooth corners for header

        self.columns_config = columns
        self.all_data = data or []
        self.filtered_data = list(self.all_data)

        self.on_edit = on_edit
        self.on_delete = on_delete
        self.selected_row = None # Tracks the currently checked row

        # =========================
        # SEARCH BAR & GLOBAL ACTIONS
        # =========================
        self.search_field = ft.TextField(
            hint_text="Search records...",
            prefix_icon=ft.icons.SEARCH,
            width=280,
            height=40,
            text_size=13,
            dense=True,
            border_radius=AppStyles.BUTTON_RADIUS,
            border_color="#F1F5F9",
            focused_border_color=AppColors.PRIMARY,
            on_change=self._on_search_change,
            bgcolor="#f9fafb"
        )

        # Global Edit Button (Top)
        self.edit_btn = ft.ElevatedButton(
            "Edit",
            icon=ft.icons.EDIT_ROUNDED,
            on_click=self._handle_top_edit,
            disabled=True, # Disabled until selection
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor={"": AppColors.PRIMARY, "disabled": ft.colors.GREY_300},
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20)
            )
        )

        # Global Delete Button (Top)
        self.delete_btn = ft.ElevatedButton(
            "Delete",
            icon=ft.icons.DELETE_OUTLINE_ROUNDED,
            on_click=self._handle_top_delete,
            disabled=True, # Disabled until selection
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor={"": ft.colors.RED_400, "disabled": ft.colors.GREY_300},
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20)
            )
        )

        # =========================
        # DATA TABLE
        # =========================
        self.table = ft.DataTable(
            columns=self._build_columns(),
            rows=[],
            column_spacing=25, # More breathing room
            heading_row_color="#F8FAFC",
            heading_row_height=45,
            data_row_min_height=45,
            data_row_max_height=55,
            horizontal_lines=ft.border.BorderSide(0.5, "#F1F5F9"),
            show_checkbox_column=True, # Single selection via checkbox
        )

        self._build_rows()

        self.content = ft.Column(
            [
                ft.Container(
                    content=ft.Row([
                        ft.Row([self.search_field, self.edit_btn, self.delete_btn], spacing=10),
                        ft.Text(f"Total: {len(self.all_data)}", size=12, color=ft.colors.BLUE_GREY_400)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(left=15, right=15, top=10, bottom=5)
                ),
                ft.Divider(height=1, color="#f0f1f5"),
                ft.Container(
                    # Tighten layout: Row with horizontal scroll, Column for vertical
                    content=ft.Row(
                        [ft.Column([self.table], scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.START)], 
                        scroll=ft.ScrollMode.ALWAYS,
                        vertical_alignment=ft.CrossAxisAlignment.START
                    ),
                    expand=True,
                    padding=ft.padding.only(left=10, right=10, bottom=10)
                )
            ],
            spacing=0,
            expand=True
        )

    # =========================================================
    # BUILD COLUMNS
    # =========================================================
    def _build_columns(self):
        cols = []
        for col in self.columns_config:
            cols.append(
                ft.DataColumn(
                    ft.Text(col["label"].upper(), size=11, weight="bold", color=AppColors.TEXT_SUB, style=ft.TextStyle(letter_spacing=1.0))
                )
            )
        # Note: No more 'Actions' column for 'Cleaner Look' as requested
        return cols

    # =========================================================
    # BUILD ROWS
    # =========================================================
    def _build_rows(self):
        self.table.rows.clear()
        self.selected_row = None
        self.edit_btn.disabled = True
        self.delete_btn.disabled = True

        for row_data in self.filtered_data:
            cells = []

            for col in self.columns_config:
                value = row_data.get(col["key"], "")
                cells.append(
                    ft.DataCell(ft.Text(str(value), size=13, color=AppColors.TEXT_HEADER))
                )

            self.table.rows.append(
                ft.DataRow(
                    cells=cells,
                    on_select_changed=lambda e, r=row_data: self._on_row_select(e, r),
                )
            )

    # =========================================================
    # SELECTION & ACTION LOGIC
    # =========================================================
    def _on_row_select(self, e, row_data):
        # Mutual exclusivity: only one row selected at a time
        if e.data == "true":
            # Deselect all rows first
            for r in self.table.rows:
                r.selected = False
            # Select only the current row
            e.control.selected = True
            self.selected_row = row_data
            self.edit_btn.disabled = False
            self.delete_btn.disabled = False
        else:
            # Handle unselection (e.data == "false")
            e.control.selected = False
            self.selected_row = None
            self.edit_btn.disabled = True
            self.delete_btn.disabled = True
        
        self._safe_update()

    def _handle_top_edit(self, e):
        if self.selected_row and self.on_edit:
            self.on_edit(self.selected_row)

    def _handle_top_delete(self, e):
        if self.selected_row and self.on_delete:
            self.on_delete(self.selected_row)

    # =========================================================
    # SEARCH LOGIC
    # =========================================================
    def _on_search_change(self, e):
        query = self.search_field.value.lower()
        if not query:
            self.filtered_data = list(self.all_data)
        else:
            self.filtered_data = []
            for item in self.all_data:
                match = False
                for col in self.columns_config:
                    val = str(item.get(col["key"], "")).lower()
                    if query in val:
                        match = True
                        break
                if match:
                    self.filtered_data.append(item)
        
        self._build_rows()
        self._safe_update()

    def _safe_update(self):
        try:
            if self.page:
                self.update()
        except Exception:
            pass

    def set_data(self, data):
        self.all_data = data or []
        self._on_search_change(None)

    def add_row(self, row_data):
        self.all_data.append(row_data)
        self._on_search_change(None)

    def remove_row(self, row_id, key="id"):
        self.all_data = [r for r in self.all_data if r.get(key) != row_id]
        self._on_search_change(None)

    def clear(self):
        self.all_data = []
        self.filtered_data = []
        self._build_rows()
        self._safe_update()
