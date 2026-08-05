import flet as ft
from datetime import date, timedelta
from core.state import state
from core.theme import AppColors, AppStyles
from database.db import select
from components.table import TableBuilder
from core.pdf_gen import pdf_engine, print_pdf

# ── Report Categories & Structure ──────────────────────
REPORT_CATEGORIES = {
    "Sales Analytics": [
        "Sales Details",
        "Party-wise Sales",
        "Item-wise Sales"
    ]
}

class ReportsScreen(ft.Container):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.padding = 20

        # Current State
        self.current_report = "Sales Details"
        self.current_columns = []
        self.current_data = []
        
        # ── Header ──────────────────────────────────────────
        self.header = ft.Container(
            content=ft.Row([
                ft.Text("Business Intelligence & Reports", size=AppStyles.H1_SIZE, weight="bold", color=AppColors.TEXT_HEADER),
                ft.ElevatedButton("Dashboard", icon=ft.icons.DASHBOARD, on_click=lambda _: self.load_analytics(), style=AppStyles.secondary_button_style())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        # ── Sidebar Menu ────────────────────────────────────
        self.sidebar_col = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
        self._build_sidebar()
        
        self.sidebar = ft.Container(
            width=250,
            border=ft.border.only(right=ft.border.BorderSide(1, "#E2E8F0")),
            padding=ft.padding.only(right=15),
            content=self.sidebar_col
        )

        # ── Main Content Area ───────────────────────────────
        self.content_area = ft.Container(expand=True, padding=ft.padding.only(left=20))

        self.content = ft.Column([
            self.header,
            ft.Divider(height=20, color=ft.colors.TRANSPARENT),
            ft.Row([self.sidebar, self.content_area], expand=True, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        ], expand=True)

    def did_mount(self):
        self.load_analytics()

    # =========================================================
    # SIDEBAR BUILDER
    # =========================================================
    def _build_sidebar(self):
        self.sidebar_col.controls.clear()
        
        for category, reports in REPORT_CATEGORIES.items():
            self.sidebar_col.controls.append(
                ft.Container(
                    padding=ft.padding.only(top=10, bottom=5),
                    content=ft.Text(category.upper(), size=11, weight="bold", color=AppColors.TEXT_SUB)
                )
            )
            for report in reports:
                is_selected = (report == self.current_report)
                self.sidebar_col.controls.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=6,
                        bgcolor=ft.colors.with_opacity(0.1, AppColors.PRIMARY) if is_selected else ft.colors.TRANSPARENT,
                        on_click=lambda e, r=report: self.on_report_select(r),
                        ink=True,
                        content=ft.Text(
                            report, 
                            color=AppColors.PRIMARY if is_selected else AppColors.TEXT_HEADER,
                            weight="w600" if is_selected else "normal",
                            size=13
                        )
                    )
                )

    def on_report_select(self, report_name):
        self.current_report = report_name
        self._build_sidebar() # Rebuild to update active state
        self.load_central_viewer()
        if self.page: self.update()

    # =========================================================
    # 1. ANALYTICS DASHBOARD
    # =========================================================
    def load_analytics(self):
        # Deselect sidebar item
        self.current_report = None
        self._build_sidebar()
        
        if not state.company_id:
            self.content_area.content = ft.Text("Select company first", color="red")
            if self.page: self.update()
            return

        invoices = select("final_invoices", {"company_id": state.company_id})
        orders = select("orders", {"company_id": state.company_id})
        ledger = select("ledger_entries", {"company_id": state.company_id})

        total_sales = sum(float(i.get("net_amount", 0) or 0) for i in invoices)
        pending_orders_count = sum(1 for o in orders if o.get("status") in ["Pending", "Partial"])
        
        total_debit = sum(float(l.get("debit", 0) or 0) for l in ledger)
        total_credit = sum(float(l.get("credit", 0) or 0) for l in ledger)
        net_outstanding = total_debit - total_credit

        self.content_area.content = ft.Column([
            ft.Text("Business Health Overview", size=18, weight="bold", color=AppColors.TEXT_HEADER),
            ft.Divider(height=20, color=ft.colors.TRANSPARENT),
            ft.ResponsiveRow([
                ft.Container(self.build_card("Total Sales Invoiced", f"₹{total_sales:,.2f}", ft.icons.MONETIZATION_ON, AppColors.PRIMARY), col={"sm": 12, "md": 4}),
                ft.Container(self.build_card("Net Market Outstanding", f"₹{net_outstanding:,.2f}", ft.icons.ACCOUNT_BALANCE, AppColors.DANGER), col={"sm": 12, "md": 4}),
                ft.Container(self.build_card("Orders Left to Pack", str(pending_orders_count), ft.icons.INVENTORY, AppColors.WARNING), col={"sm": 12, "md": 4}),
            ], spacing=20)
        ])
        if self.page: self.update()

    def build_card(self, title, value, icon, accent_color):
        return ft.Container(
            padding=24, bgcolor=AppColors.BG_CARD, border_radius=AppStyles.RADIUS,
            shadow=AppStyles.CARD_SHADOW, border=ft.border.all(1, "#F0F0F0"),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, color=accent_color, size=24),
                        bgcolor=ft.colors.with_opacity(0.1, accent_color),
                        padding=12, border_radius=12
                    ),
                ]),
                ft.Divider(height=15, color=ft.colors.TRANSPARENT),
                ft.Text(title.upper(), size=11, weight="bold", color=AppColors.TEXT_SUB, style=ft.TextStyle(letter_spacing=0.5)),
                ft.Text(value, size=28, weight="bold", color=AppColors.TEXT_HEADER),
            ], spacing=0)
        )

    # =========================================================
    # 2. CENTRAL REPORT VIEWER
    # =========================================================
    def load_central_viewer(self):
        if not state.company_id:
            self.content_area.content = ft.Text("Select company first", color="red")
            return
            
        S = AppStyles.get_input_style()

        # Filters
        today = date.today()
        first_day = today.replace(day=1)
        self.from_date = ft.TextField(label="From Date", value=first_day.isoformat(), width=150, prefix_icon=ft.icons.CALENDAR_TODAY, **S)
        self.to_date = ft.TextField(label="To Date", value=today.isoformat(), width=150, prefix_icon=ft.icons.CALENDAR_TODAY, **S)
        self.entity_dd = ft.Dropdown(label="Select Target", width=250, visible=False, prefix_icon=ft.icons.PERSON, **S)
        
        self.generate_btn = ft.ElevatedButton("Generate", icon=ft.icons.PLAY_ARROW, on_click=self.generate_report, style=AppStyles.primary_button_style())
        self.export_pdf_btn = ft.OutlinedButton("Export PDF", icon=ft.icons.PICTURE_AS_PDF, on_click=self.export_pdf, style=AppStyles.secondary_button_style())

        self.report_container = ft.Container(expand=True)
        self.report_header = ft.Container() # Holds the professional header text

        # Setup Entity Dropdown based on selected report
        self._setup_entity_dropdown()

        # Build Filter Card
        filter_card = ft.Container(
            bgcolor="#F8FAFC",
            padding=20,
            border_radius=8,
            border=ft.border.all(1, "#E2E8F0"),
            content=ft.Column([
                ft.Text(f"Filters for {self.current_report}", weight="bold", color=AppColors.TEXT_HEADER),
                ft.Row([self.from_date, self.to_date, self.entity_dd, self.generate_btn, self.export_pdf_btn], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=15)
            ])
        )

        self.content_area.content = ft.Column([
            filter_card,
            ft.Divider(height=20, color=ft.colors.TRANSPARENT),
            self.report_header,
            self.report_container
        ], expand=True)

    def _setup_entity_dropdown(self):
        val = self.current_report
        self.entity_dd.visible = False
        self.entity_dd.options = []
        
        if val in ["Party Ledger", "Agent Ledger", "Expense Ledger"]:
            self.entity_dd.visible = True
            
            if "Party" in val:
                self.entity_dd.label = "Select Party"
                data = select("parties", {"company_id": state.company_id})
            elif "Agent" in val:
                self.entity_dd.label = "Select Agent"
                data = select("agents", {"company_id": state.company_id})
            else:
                self.entity_dd.label = "Select Expense Ledger"
                data = select("expense_ledgers", {"company_id": state.company_id})
                
            self.entity_dd.options = [ft.dropdown.Option(str(d["id"]), d.get("name", d.get("ledger_name", "Unknown"))) for d in data]

    def _set_report_header(self, entity_name=None):
        title = self.current_report
        subtitle = f"Period: {self.from_date.value} to {self.to_date.value}"
        if entity_name:
            title = f"{self.current_report} — {entity_name}"
            
        self.report_header.content = ft.Column([
            ft.Text(title.upper(), size=16, weight="bold", color=AppColors.PRIMARY),
            ft.Text(subtitle, size=12, color=AppColors.TEXT_SUB),
            ft.Divider(height=10)
        ], spacing=2)

    # =========================================================
    # REPORT GENERATION ENGINE
    # =========================================================
    def generate_report(self, e):
        r_type = self.current_report
        f_date = self.from_date.value
        t_date = self.to_date.value
        
        self.report_container.content = ft.ProgressRing()
        if self.page: self.update()

        try:
            if r_type == "Sales Details":                   self.run_sales_details(f_date, t_date)
            elif r_type == "Party-wise Sales":              self.run_party_wise_sales(f_date, t_date)
            elif r_type == "Item-wise Sales":               self.run_item_wise_sales(f_date, t_date)
            elif r_type == "Agent-wise Sales":              self.run_agent_wise_sales(f_date, t_date)
            elif r_type == "Party Ledger":                  self.run_party_ledger(f_date, t_date)
            elif r_type == "Party Outstanding":             self.run_party_outstanding(f_date, t_date)
            elif r_type == "Agent Ledger":                  self.run_agent_ledger(f_date, t_date)
            elif r_type == "Agent Outstanding":             self.run_agent_outstanding(f_date, t_date)
            elif r_type == "Expense Ledger":                self.run_expense_ledger(f_date, t_date)
            elif r_type == "Expense Outstanding":           self.run_expense_outstanding(f_date, t_date)
            elif r_type == "Purchase Order Details":        self.run_po_details(f_date, t_date)
            elif r_type == "Cheque Issue Details":          self.run_cheque_details(f_date, t_date)
            elif r_type == "Stock Ledger":                  self.run_stock_ledger(f_date, t_date)
            else:
                self.report_container.content = ft.Text(f"Report '{r_type}' not configured.", color="orange")
        except Exception as ex:
            self.report_container.content = ft.Text(f"Error generating report: {ex}", color="red")
            
        if self.page: self.update()

    def _render_table(self, cols, data):
        self.current_columns = cols
        self.current_data = data
        self.report_container.content = TableBuilder(cols, data)

    def export_pdf(self, e):
        if not self.current_columns or not self.current_data:
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text("Please generate a report first."), bgcolor="orange")
                self.page.snack_bar.open = True
                self.page.update()
            return
            
        try:
            subtitle = f"Period: {self.from_date.value} to {self.to_date.value}"
            if self.entity_dd.visible and self.entity_dd.value:
                entity_name = next((opt.text for opt in self.entity_dd.options if opt.key == str(self.entity_dd.value)), "")
                subtitle += f" | {entity_name}"
                
            pdf_path = pdf_engine.generate_report_pdf(
                self.current_report,
                subtitle,
                self.current_columns,
                self.current_data,
                company_data={"name": state.current_company.get("name", "Garments ERP")} if state.current_company else {}
            )
            print_pdf(pdf_path)
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text("PDF Generated and Opened"), bgcolor=AppColors.SUCCESS)
                self.page.snack_bar.open = True
                self.page.update()
        except Exception as ex:
            print(f"PDF Export Error: {ex}")
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red")
                self.page.snack_bar.open = True
                self.page.update()

    # =========================================================
    # INDIVIDUAL REPORT LOGIC
    # =========================================================
    def run_sales_details(self, fd, td):
        self._set_report_header()
        invoices = select("final_invoices", {"company_id": state.company_id})
        parties = {str(p["id"]): p["name"] for p in select("parties", {"company_id": state.company_id})}
        
        data = []
        for inv in invoices:
            dt = inv.get("invoice_date", "")
            if fd <= dt <= td:
                tot_tax = float(inv.get('igst_amount', 0) or 0) + float(inv.get('cgst_amount', 0) or 0) + float(inv.get('sgst_amount', 0) or 0) + float(inv.get('tcs_amount', 0) or 0)
                data.append({
                    "inv_no": inv.get("invoice_no"),
                    "date": dt,
                    "party": parties.get(str(inv.get("party_id")), "Unknown"),
                    "taxable": f"₹{float(inv.get('taxable_amount',0)):,.2f}",
                    "tax": f"₹{tot_tax:,.2f}",
                    "net": f"₹{float(inv.get('net_amount',0)):,.2f}"
                })
        
        cols = [
            {"key": "inv_no", "label": "Inv No"},
            {"key": "date", "label": "Date"},
            {"key": "party", "label": "Party"},
            {"key": "taxable", "label": "Taxable Amt"},
            {"key": "tax", "label": "Tax Amt"},
            {"key": "net", "label": "Net Amount"},
        ]
        self._render_table(cols, sorted(data, key=lambda x: x["date"], reverse=True))

    def run_party_wise_sales(self, fd, td):
        self._set_report_header()
        invoices = select("final_invoices", {"company_id": state.company_id})
        parties = {str(p["id"]): p["name"] for p in select("parties", {"company_id": state.company_id})}
        
        agg = {}
        for inv in invoices:
            dt = inv.get("invoice_date", "")
            if fd <= dt <= td:
                pid = str(inv.get("party_id"))
                if pid not in agg:
                    agg[pid] = {"party": parties.get(pid, "Unknown"), "count": 0, "net": 0}
                agg[pid]["count"] += 1
                agg[pid]["net"] += float(inv.get("net_amount", 0))
                
        data = [{"party": v["party"], "count": str(v["count"]), "net": f"₹{v['net']:,.2f}", "_sort": v["net"]} for v in agg.values()]
        cols = [{"key": "party", "label": "Party Name"}, {"key": "count", "label": "No. of Invoices"}, {"key": "net", "label": "Total Sales Value"}]
        self._render_table(cols, sorted(data, key=lambda x: x["_sort"], reverse=True))

    def run_item_wise_sales(self, fd, td):
        self._set_report_header()
        orders = select("orders", {"company_id": state.company_id})
        order_items = select("order_items", {"company_id": state.company_id})
        items_db = {str(i["id"]): i.get("item_name", "Unknown") for i in select("items", {"company_id": state.company_id})}
        
        # Map order ID to date
        order_dates = {str(o["id"]): o.get("order_date", "") for o in orders}
        
        agg = {}
        for o_item in order_items:
            oid = str(o_item.get("order_id"))
            dt = order_dates.get(oid, "")
            if fd <= dt <= td:
                item_id = str(o_item.get("item_id"))
                iname = items_db.get(item_id, o_item.get("item_name", "Unknown"))
                
                if iname not in agg: agg[iname] = {"qty": 0, "value": 0}
                agg[iname]["qty"] += int(float(o_item.get("qty_pieces", 0)))
                agg[iname]["value"] += float(o_item.get("amount", 0))
                    
        data = [{"item": k, "qty": str(v["qty"]), "val": f"₹{v['value']:,.2f}", "_sort": v["value"]} for k, v in agg.items()]
        cols = [{"key": "item", "label": "Item Name"}, {"key": "qty", "label": "Total Pcs Sold"}, {"key": "val", "label": "Total Value"}]
        self._render_table(cols, sorted(data, key=lambda x: x["_sort"], reverse=True))

    def run_agent_wise_sales(self, fd, td):
        self._set_report_header()
        invoices = select("final_invoices", {"company_id": state.company_id})
        parties = {str(p["id"]): {"name": p["name"], "agent_id": p.get("agent_id")} for p in select("parties", {"company_id": state.company_id})}
        agents = {str(a["id"]): {"name": a["name"], "comm": float(a.get("commission_percent", 0))} for a in select("agents", {"company_id": state.company_id})}
        
        agg = {}
        for inv in invoices:
            dt = inv.get("invoice_date", "")
            if fd <= dt <= td:
                p_info = parties.get(str(inv.get("party_id")), {})
                
                # Get agent from invoice or fallback to party default
                aid = inv.get("agent_id")
                if not aid or str(aid) == "None":
                    aid = p_info.get("agent_id")
                
                aid = str(aid) if aid else None
                
                a_info = agents.get(aid, {"name": "Direct/No Agent", "comm": 0})
                aname = a_info["name"]
                
                if aname not in agg: agg[aname] = {"sales": 0, "comm_pct": a_info["comm"], "comm_amt": 0}
                net = float(inv.get("net_amount", 0))
                agg[aname]["sales"] += net
                agg[aname]["comm_amt"] += net * (a_info["comm"] / 100)
                
        data = [{"agent": k, "sales": f"₹{v['sales']:,.2f}", "pct": f"{v['comm_pct']}%", "comm": f"₹{v['comm_amt']:,.2f}", "_sort": v["sales"]} for k, v in agg.items()]
        cols = [{"key": "agent", "label": "Agent Name"}, {"key": "sales", "label": "Total Sales"}, {"key": "pct", "label": "Comm %"}, {"key": "comm", "label": "Commission Earned"}]
        self._render_table(cols, sorted(data, key=lambda x: x["_sort"], reverse=True))

    def run_party_ledger(self, fd, td):
        pid = self.entity_dd.value
        if not pid:
            self.report_container.content = ft.Text("Please select a Party from the dropdown.", color="red")
            return
            
        party_name = next((opt.text for opt in self.entity_dd.options if opt.key == str(pid)), "Unknown")
        self._set_report_header(party_name)
            
        # FIX: query by account_id, not party_id
        entries = select("ledger_entries", {"company_id": state.company_id, "account_id": pid})
        data = []
        running_bal = 0
        for e in sorted(entries, key=lambda x: x.get("entry_date", "")):
            dr = float(e.get("debit", 0) or 0)
            cr = float(e.get("credit", 0) or 0)
            running_bal += (dr - cr)
            data.append({
                "date": str(e.get("entry_date", ""))[:10],
                "type": f"{e.get('ref_type', 'Entry')} ({e.get('ref_id', '-')})",
                "dr": f"₹{dr:,.2f}" if dr > 0 else "",
                "cr": f"₹{cr:,.2f}" if cr > 0 else "",
                "bal": f"₹{abs(running_bal):,.2f} {'Dr' if running_bal >= 0 else 'Cr'}"
            })
            
        cols = [{"key": "date", "label": "Date"}, {"key": "type", "label": "Type"}, {"key": "dr", "label": "Debit (+)"}, {"key": "cr", "label": "Credit (-)"}, {"key": "bal", "label": "Balance"}]
        self._render_table(cols, data[::-1])

    def run_party_outstanding(self, fd, td):
        self._set_report_header()
        ledger = select("ledger_entries", {"company_id": state.company_id})
        parties = {str(p["id"]): p["name"] for p in select("parties", {"company_id": state.company_id})}
        
        bal = {}
        for p_id, p_name in parties.items():
            bal[p_id] = {"name": p_name, "debit": 0, "credit": 0}

        for entry in ledger:
            dt = entry.get("entry_date", "")
            if fd <= dt <= td:
                pid = str(entry.get("account_id"))
                if pid in bal:
                    bal[pid]["debit"] += float(entry.get("debit", 0))
                    bal[pid]["credit"] += float(entry.get("credit", 0))

        summary_data = []
        for pid, v in bal.items():
            net = v["debit"] - v["credit"]
            if round(net, 2) != 0:
                side = "Dr" if net > 0 else "Cr"
                summary_data.append({
                    "party": v["name"],
                    "debit": f"₹{v['debit']:,.2f}",
                    "credit": f"₹{v['credit']:,.2f}",
                    "net": f"₹{abs(net):,.2f} {side}",
                    "_sort": abs(net)
                })
        
        summary_cols = [{"key": "party", "label": "Party Name"}, {"key": "debit", "label": "Total Debit"}, {"key": "credit", "label": "Total Credit"}, {"key": "net", "label": "Net Balance"}]
        summary_table = TableBuilder(summary_cols, sorted(summary_data, key=lambda x: x["_sort"], reverse=True))
        summary_table.expand = False
        summary_table.height = 300

        self.report_container.content = ft.Column([
            ft.Text("Party Balances Summary", size=14, weight="bold", color=AppColors.TEXT_HEADER),
            summary_table,
        ], expand=True, scroll=ft.ScrollMode.AUTO)

    def run_agent_ledger(self, fd, td):
        aid = self.entity_dd.value
        if not aid:
            self.report_container.content = ft.Text("Please select an Agent from the dropdown.", color="red")
            return
            
        agent_name = next((opt.text for opt in self.entity_dd.options if opt.key == str(aid)), "Unknown")
        self._set_report_header(agent_name)
            
        invoices = select("final_invoices", {"company_id": state.company_id})
        parties = {str(p["id"]): p for p in select("parties", {"company_id": state.company_id})}
        payments = select("payment_vouchers", {"company_id": state.company_id})
        agent_raw = select("agents", {"id": aid})
        agent_info = agent_raw[0] if agent_raw else {"commission_percent": 0}
        comm_pct = float(agent_info.get("commission_percent", 0))

        data = []
        running_bal = 0
        
        # 1. Commissions Earned
        for inv in invoices:
            dt = inv.get("invoice_date", "")
            if fd <= dt <= td:
                pid = str(inv.get("party_id"))
                p_agent = str(inv.get("agent_id")) if inv.get("agent_id") else str(parties.get(pid, {}).get("agent_id"))
                if p_agent == aid:
                    net = float(inv.get("net_amount", 0))
                    comm = net * (comm_pct / 100)
                    running_bal += comm
                    data.append({
                        "date": dt,
                        "type": f"Comm (Inv {inv.get('invoice_no')})",
                        "dr": "",
                        "cr": f"₹{comm:,.2f}",
                        "bal": f"₹{running_bal:,.2f} Cr"
                    })
                    
        # 2. Commissions Paid
        for pv in sorted(payments, key=lambda x: x.get("voucher_date", "")):
            dt = pv.get("voucher_date", "")
            # FIX: query by agent_id, not account_id
            if fd <= dt <= td and str(pv.get("agent_id")) == aid:
                amt = float(pv.get("amount", 0))
                running_bal -= amt
                data.append({
                    "date": dt,
                    "type": f"Payment ({pv.get('voucher_no')})",
                    "dr": f"₹{amt:,.2f}",
                    "cr": "",
                    "bal": f"₹{running_bal:,.2f} Cr"
                })
                
        cols = [{"key": "date", "label": "Date"}, {"key": "type", "label": "Particulars"}, {"key": "dr", "label": "Paid (Dr)"}, {"key": "cr", "label": "Earned (Cr)"}, {"key": "bal", "label": "Balance"}]
        self._render_table(cols, sorted(data, key=lambda x: x["date"], reverse=True))

    def run_agent_outstanding(self, fd, td):
        self._set_report_header()
        invoices = select("final_invoices", {"company_id": state.company_id})
        parties = {str(p["id"]): {"name": p["name"], "agent_id": p.get("agent_id")} for p in select("parties", {"company_id": state.company_id})}
        agents = {str(a["id"]): {"name": a["name"], "comm_pct": float(a.get("commission_percent", 0)), "earned": 0, "paid": 0} for a in select("agents", {"company_id": state.company_id})}
        payments = select("payment_vouchers", {"company_id": state.company_id})

        for inv in invoices:
            dt = inv.get("invoice_date", "")
            if fd <= dt <= td:
                pid = str(inv.get("party_id"))
                
                # Get agent from invoice or fallback to party default
                aid = inv.get("agent_id")
                if not aid or str(aid) == "None":
                    aid = parties.get(pid, {}).get("agent_id")
                
                aid = str(aid) if aid else None
                
                if aid and aid in agents:
                    agents[aid]["earned"] += float(inv.get("net_amount", 0)) * (agents[aid]["comm_pct"] / 100)
                
        for pv in payments:
            dt = pv.get("voucher_date", "")
            if fd <= dt <= td:
                # FIX: query by agent_id, not account_id
                aid = str(pv.get("agent_id"))
                if aid in agents:
                    agents[aid]["paid"] += float(pv.get("amount", 0))

        summary_data = []
        for v in agents.values():
            net = v["earned"] - v["paid"]
            if round(net, 2) != 0:
                summary_data.append({
                    "agent": v["name"], "earned": f"\u20b9{v['earned']:,.2f}", "paid": f"\u20b9{v['paid']:,.2f}",
                    "net": f"\u20b9{net:,.2f} Cr", "_sort": net
                })
        
        summary_cols = [{"key": "agent", "label": "Agent Name"}, {"key": "earned", "label": "Total Earned (Cr)"}, {"key": "paid", "label": "Total Paid (Dr)"}, {"key": "net", "label": "Net Payable"}]
        summary_table = TableBuilder(summary_cols, sorted(summary_data, key=lambda x: x["_sort"], reverse=True))
        summary_table.expand = False
        summary_table.height = 250

        detail_data = []
        for inv in invoices:
            dt = inv.get("invoice_date", "")
            if fd <= dt <= td:
                pid = str(inv.get("party_id"))
                p_info = parties.get(pid, {})
                aid = inv.get("agent_id")
                if not aid or str(aid) == "None":
                    aid = p_info.get("agent_id")
                
                aid = str(aid) if aid else None
                
                if aid and aid in agents:
                    net_amt = float(inv.get("net_amount", 0))
                    comm = net_amt * (agents[aid]["comm_pct"] / 100)
                    detail_data.append({
                        "agent": agents[aid]["name"], "inv": inv.get("invoice_no", "-"),
                        "party": p_info.get("name", "Unknown"), "amt": f"₹{net_amt:,.2f}",
                        "comm": f"₹{comm:,.2f}"
                    })
        detail_cols = [{"key": "agent", "label": "Agent"}, {"key": "inv", "label": "Invoice"}, {"key": "party", "label": "Party"}, {"key": "amt", "label": "Sale Amt"}, {"key": "comm", "label": "Commission"}]
        detail_table = TableBuilder(detail_cols, detail_data)
        detail_table.expand = False
        detail_table.height = 400

        self.report_container.content = ft.Column([
            ft.Text("Summary View", size=14, weight="bold", color=AppColors.TEXT_HEADER),
            summary_table,
            ft.Container(height=20),
            ft.Text("Detail View (Invoice-by-Invoice)", size=14, weight="bold", color=AppColors.TEXT_HEADER),
            detail_table
        ], expand=True, scroll=ft.ScrollMode.AUTO)

    def run_expense_ledger(self, fd, td):
        eid = self.entity_dd.value
        if not eid:
            self.report_container.content = ft.Text("Please select an Expense Ledger from the dropdown.", color="red")
            return
            
        expense_name = next((opt.text for opt in self.entity_dd.options if opt.key == str(eid)), "Unknown")
        self._set_report_header(expense_name)
            
        payments = select("payment_vouchers", {"company_id": state.company_id})
        
        data = []
        running_total = 0
        for pv in sorted(payments, key=lambda x: x.get("voucher_date", "")):
            if str(pv.get("expense_id")) == eid:
                dt = pv.get("voucher_date", "")
                if fd <= dt <= td:
                    amt = float(pv.get("amount", 0))
                    running_total += amt
                    data.append({
                        "date": dt,
                        "voucher": pv.get("voucher_no", "-"),
                        "narration": pv.get("narration", "-"),
                        "amount": f"\u20b9{amt:,.2f}",
                        "running": f"\u20b9{running_total:,.2f}"
                    })
                
        cols = [{"key": "date", "label": "Date"}, {"key": "voucher", "label": "Voucher No"}, {"key": "narration", "label": "Narration"}, {"key": "amount", "label": "Amount"}, {"key": "running", "label": "Running Total"}]
        self._render_table(cols, data[::-1])

    def run_expense_outstanding(self, fd, td):
        self._set_report_header()
        payments = select("payment_vouchers", {"company_id": state.company_id})
        exp_ledgers = {str(e["id"]): e["ledger_name"] for e in select("expense_ledgers", {"company_id": state.company_id})}
        
        agg = {eid: 0 for eid in exp_ledgers}
        for pv in payments:
            dt = pv.get("voucher_date", "")
            if fd <= dt <= td:
                eid = str(pv.get("expense_id"))
                if eid in agg:
                    agg[eid] += float(pv.get("amount", 0))
                
        data = []
        for eid, total in agg.items():
            if total > 0:
                data.append({"expense": exp_ledgers[eid], "total": f"₹{total:,.2f}", "_sort": total})
        
        cols = [{"key": "expense", "label": "Expense Category"}, {"key": "total", "label": "Total Spending"}]
        table = TableBuilder(cols, sorted(data, key=lambda x: x["_sort"], reverse=True))
        table.expand = False
        table.height = 600

        self.report_container.content = ft.Column([
            ft.Text("Expense Summary", size=14, weight="bold", color=AppColors.TEXT_HEADER),
            table
        ], expand=True, scroll=ft.ScrollMode.AUTO)

    def run_po_details(self, fd, td):
        self._set_report_header()
        pos = select("purchase_orders", {"company_id": state.company_id})
        parties = {str(p["id"]): p["name"] for p in select("parties", {"company_id": state.company_id})}
        data = []
        for po in pos:
            dt = po.get("po_date", "")
            if fd <= dt <= td:
                data.append({
                    "po": po.get("po_no"), "date": dt, "supplier": parties.get(str(po.get("supplier_id")), "Unknown"),
                    "pcs": str(po.get("total_pcs")), "amt": f"₹{float(po.get('total_amount', 0)):,.2f}"
                })
        cols = [{"key": "po", "label": "PO No"}, {"key": "date", "label": "Date"}, {"key": "supplier", "label": "Supplier"}, {"key": "pcs", "label": "Total Pcs"}, {"key": "amt", "label": "Amount"}]
        self._render_table(cols, sorted(data, key=lambda x: x["date"], reverse=True))

    def run_cheque_details(self, fd, td):
        self._set_report_header()
        pv = select("payment_vouchers", {"company_id": state.company_id})
        data = []
        for p in pv:
            dt = p.get("voucher_date", "")
            if fd <= dt <= td and p.get("mode", "").lower() == "cheque":
                data.append({
                    "vno": p.get("voucher_no"), "date": dt, "ref": p.get("narration", "-"), # using narration as ref
                    "amt": f"₹{float(p.get('amount', 0)):,.2f}", "narration": p.get("narration", "-")
                })
        cols = [{"key": "vno", "label": "Voucher No"}, {"key": "date", "label": "Date"}, {"key": "ref", "label": "Cheque/Ref No"}, {"key": "amt", "label": "Amount"}, {"key": "narration", "label": "Remarks"}]
        self._render_table(cols, sorted(data, key=lambda x: x["date"], reverse=True))

    def run_stock_ledger(self, fd, td):
        self._set_report_header()
        stock = select('stock_ledger', {'company_id': state.company_id})
        items_db = {str(i['id']): i['item_name'] for i in select('items', {'company_id': state.company_id})}
        
        inventory = {}
        for row in stock:
            dt = row.get('entry_date', '')
            if fd <= dt <= td:
                iid = str(row.get('item_id'))
                sz = row.get('size_value', 'FS')
                key = f'{iid}_{sz}'
                
                if key not in inventory:
                    inventory[key] = {
                        'item': items_db.get(iid, 'Unknown'),
                        'size': sz,
                        'in_qty': 0,
                        'out_qty': 0,
                        'balance': 0
                    }
                
                q = int(row.get('qty', 0))
                ttype = row.get('transaction_type', '')
                if ttype == 'IN' or ttype == 'OPENING':
                    inventory[key]['in_qty'] += q
                    inventory[key]['balance'] += q
                elif ttype == 'OUT':
                    inventory[key]['out_qty'] += q
                    inventory[key]['balance'] -= q
                    
        data = list(inventory.values())
        data.sort(key=lambda x: x['item'])
        
        cols = [
            {'key': 'item', 'label': 'Item Name'},
            {'key': 'size', 'label': 'Size'},
            {'key': 'in_qty', 'label': 'Total Inward'},
            {'key': 'out_qty', 'label': 'Total Outward'},
            {'key': 'balance', 'label': 'Closing Stock'}
        ]
        
        self._render_table(cols, data)
