import flet as ft

from core.state import state
from services.report_service import ReportService
from components.filters import FilterBar
from components.table import TableBuilder


class SalesReportScreen(ft.Container):
    def __init__(self):
        super().__init__()

        self.expand = True
        self.padding = 10

        # =========================
        # SUMMARY
        # =========================
        self.total_sales_text = ft.Text("Total Sales: ₹0", size=16, weight="bold")
        self.total_orders_text = ft.Text("Orders: 0", size=16)

        # =========================
        # TABLE
        # =========================
        self.table = TableBuilder([
            {"key": "order_id", "label": "Order ID"},
            {"key": "party_id", "label": "Party"},
            {"key": "amount", "label": "Amount"},
        ])

        # =========================
        # FILTERS
        # =========================
        filters = [
            {"name": "party_id", "label": "Party ID"},
        ]

        self.filter_bar = FilterBar(filters, on_apply=self.apply_filters)

        # =========================
        # LAYOUT
        # =========================
        self.content = ft.Column(
            controls=[
                ft.Text("Sales Report", size=22, weight="bold"),

                self.filter_bar,

                ft.Row([
                    self.total_sales_text,
                    self.total_orders_text
                ], spacing=20),

                ft.Divider(),

                self.table
            ],
            expand=True,
            spacing=10
        )

        # Initial load
        self.apply_filters({})

    # =========================================================
    # APPLY FILTERS
    # =========================================================
    def apply_filters(self, filters):
        if not state.company_id:
            return

        data = ReportService.get_sales_report(filters)

        # Update table
        self.table.set_data(data)

        # Calculate summary
        total_sales = sum(r.get("amount", 0) for r in data)
        total_orders = len(data)

        self.total_sales_text.value = f"Total Sales: ₹{round(total_sales, 2)}"
        self.total_orders_text.value = f"Orders: {total_orders}"

        self.update()
