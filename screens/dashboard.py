import flet as ft
from datetime import datetime, timezone

from core.state import state
from core.theme import AppColors, AppStyles
from database.db import select, select_recent


class DashboardScreen(ft.Container):
    def __init__(self):
        super().__init__()

        self.expand = True
        self.padding = 20

        # =========================
        # UI ELEMENTS
        # =========================
        self.company_text = ft.Text("", size=16, color=ft.colors.BLUE_GREY_400, weight="w500")
        self.header_text = ft.Text("Business Overview", size=AppStyles.H1_SIZE, weight="bold", color=AppColors.TEXT_HEADER)
        
        # Premium Cards (Updated design)
        self.sales_card = self.build_stat_card(
            "Total Sales", "₹0", ft.icons.MONETIZATION_ON, 
            AppColors.PRIMARY, "+12%"
        )
        self.orders_card = self.build_stat_card(
            "Total Orders", "0", ft.icons.SHOPPING_BAG, 
            AppColors.INFO, "+5%"
        )
        self.delivered_card = self.build_stat_card(
            "Orders Delivered", "0", ft.icons.LOCAL_SHIPPING, 
            AppColors.SUCCESS, "+8%"
        )

        # Activity list (will be populated dynamically)
        self.activity_col = ft.Column([], spacing=12, scroll=ft.ScrollMode.AUTO)
        self.activity_loading = ft.ProgressRing(width=24, height=24, stroke_width=2, visible=False)

        # =========================
        # LAYOUT
        # =========================
        self.content = ft.Column(
            controls=[
                # Header
                ft.Row([
                    ft.Column([
                        self.header_text,
                        self.company_text,
                    ], spacing=2),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                ft.Divider(height=20, color=ft.colors.TRANSPARENT),

                # Stats Grid
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(self.sales_card, col={"sm": 12, "md": 4}),
                        ft.Container(self.orders_card, col={"sm": 12, "md": 4}),
                        ft.Container(self.delivered_card, col={"sm": 12, "md": 4}),
                    ],
                    spacing=20
                ),

                ft.Divider(height=30, color=ft.colors.TRANSPARENT),

                # Recent Activity Section (Dynamic)
                ft.Row([
                    ft.Text("Recent Activity", size=18, weight="bold", color=AppColors.TEXT_HEADER),
                    self.activity_loading,
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.icons.REFRESH_ROUNDED, 
                        icon_color=AppColors.PRIMARY, 
                        icon_size=20,
                        tooltip="Refresh Activity",
                        on_click=lambda _: self.load_data()
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(
                    padding=24,
                    bgcolor=AppColors.BG_CARD,
                    border_radius=AppStyles.RADIUS,
                    shadow=AppStyles.CARD_SHADOW,
                    border=ft.border.all(1, "#F0F0F0"),
                    content=self.activity_col,
                    height=400, # Ensure visibility
                )
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO
        )

        state.subscribe(self.on_state_change)

    def did_mount(self):
        if not state.current_user:
            return
        self.load_data()

    # =========================================================
    # BUILD STAT CARD
    # =========================================================
    def build_stat_card(self, title, value, icon, accent_color, grow_text):
        value_text = ft.Text(value, size=24, weight="bold", color=AppColors.TEXT_HEADER)
        
        card = ft.Container(
            padding=24,
            bgcolor=AppColors.BG_CARD,
            border_radius=AppStyles.RADIUS,
            shadow=AppStyles.CARD_SHADOW,
            border=ft.border.all(1, "#F0F0F0"),
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(icon, color=accent_color, size=20),
                            bgcolor=ft.colors.with_opacity(0.1, accent_color),
                            padding=10,
                            border_radius=10
                        ),
                        ft.Container(
                            content=ft.Text(grow_text, size=11, weight="bold", color=accent_color),
                            bgcolor=ft.colors.with_opacity(0.1, accent_color),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=15
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=20, color=ft.colors.TRANSPARENT),
                    ft.Text(title, size=13, color=AppColors.TEXT_SUB, weight="w500"),
                    value_text
                ],
                spacing=0
            )
        )
        card.value_text = value_text
        return card

    # =========================================================
    # BUILD ACTIVITY ITEM (Enhanced with type-specific icons)
    # =========================================================
    def build_activity_item(self, title, subtitle, time_str, icon=ft.icons.NOTIFICATIONS_OUTLINED, accent=None):
        accent = accent or AppColors.PRIMARY
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=8,
            bgcolor=ft.colors.with_opacity(0.02, accent),
            border=ft.border.all(1, ft.colors.with_opacity(0.06, accent)),
            content=ft.Row([
                ft.Container(
                    width=40, height=40, 
                    bgcolor=ft.colors.with_opacity(0.1, accent), 
                    border_radius=20,
                    content=ft.Icon(icon, color=accent, size=18)
                ),
                ft.Column([
                    ft.Text(title, size=14, weight="bold", color=AppColors.TEXT_HEADER),
                    ft.Text(subtitle, size=12, color=AppColors.TEXT_SUB),
                ], spacing=2, expand=True),
                ft.Text(time_str, size=11, color=AppColors.TEXT_MUTED)
            ], alignment=ft.MainAxisAlignment.START, spacing=15)
        )

    # =========================================================
    # RELATIVE TIME HELPER
    # =========================================================
    @staticmethod
    def _relative_time(timestamp_str):
        """Convert an ISO timestamp string to a human-friendly relative time."""
        if not timestamp_str:
            return ""
        try:
            # Parse ISO format (handles both Z and +00:00 suffixes)
            ts = timestamp_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            now = datetime.now(timezone.utc)
            diff = now - dt

            seconds = int(diff.total_seconds())
            if seconds < 0:
                return "just now"
            if seconds < 60:
                return "just now"
            minutes = seconds // 60
            if minutes < 60:
                return f"{minutes}m ago"
            hours = minutes // 60
            if hours < 24:
                return f"{hours}h ago"
            days = hours // 24
            if days < 7:
                return f"{days}d ago"
            if days < 30:
                weeks = days // 7
                return f"{weeks}w ago"
            return dt.strftime("%d %b %Y")
        except Exception:
            return str(timestamp_str)[:10]

    # =========================================================
    # LOAD DATA
    # =========================================================
    def load_data(self):
        if not state.company_id:
            self.header_text.value = "Business Overview"
            self.company_text.value = "Welcome back! Please select a company."
            if self.page: self.update()
            return

        company_name = state.current_company.get('name', 'Business')
        self.header_text.value = "Business Overview"
        self.company_text.value = f"Managing: {company_name}"

        # Show loading spinner
        self.activity_loading.visible = True
        if self.page: self.update()

        # ── Pre-fetch Party Map for naming ──────────────────
        party_map = {}
        try:
            all_parties = select("parties", {"company_id": state.company_id})
            party_map = {str(p["id"]): p["name"] for p in all_parties}
        except Exception as e:
            print("Error pre-fetching parties:", e)

        try:
            # ── Stat cards ─────────────────────────────
            orders = select("orders", {"company_id": state.company_id})
            total_orders = len(orders)
            total_sales = sum(o.get("total_amount", 0) for o in orders)

            invoices = select("final_invoices", {"company_id": state.company_id})
            total_delivered = len(invoices)

            self.sales_card.value_text.value = f"₹{round(total_sales, 2):,}"
            self.orders_card.value_text.value = str(total_orders)
            self.delivered_card.value_text.value = str(total_delivered)

        except Exception as e:
            print("Dashboard stats error:", e)

        # ── Recent Activity (Dynamic) ──────────────
        activity_items = []
        company_filter = {"company_id": state.company_id}

        # 1. Recent Orders
        try:
            recent_orders = select_recent("orders", company_filter, order_by="created_at", limit=5)
            for o in recent_orders:
                p_name = party_map.get(str(o.get("party_id", "")), "Unknown Party")
                amount = o.get("net_amount") or o.get("total_amount") or 0
                status = o.get("status", "Pending")
                activity_items.append({
                    "title": f"Order {o.get('order_no', '—')} — {p_name}",
                    "subtitle": f"₹{float(amount):,.2f} · {status}",
                    "time": o.get("created_at", ""),
                    "icon": ft.icons.SHOPPING_BAG_OUTLINED,
                    "accent": AppColors.INFO,
                })
        except Exception as e:
            print("Error loading recent orders:", e)

        # 2. Recent Packing Slips
        try:
            recent_slips = select_recent("packing_slips", company_filter, order_by="created_at", limit=3)
            for s in recent_slips:
                p_name = party_map.get(str(s.get("party_id", "")), "Unknown Party")
                activity_items.append({
                    "title": f"Packing Slip {s.get('slip_no', '—')} — {p_name}",
                    "subtitle": f"Pcs: {s.get('total_pcs', 0)} · Status: {s.get('status', 'Packed')}",
                    "time": s.get("created_at", ""),
                    "icon": ft.icons.INVENTORY_2_OUTLINED,
                    "accent": "#8B5CF6",
                })
        except Exception:
            pass 

        # 3. Recent Transport Invoices
        try:
            recent_trans = select_recent("transport_invoices", company_filter, order_by="created_at", limit=3)
            for t in recent_trans:
                p_name = party_map.get(str(t.get("party_id", "")), "Unknown Party")
                activity_items.append({
                    "title": f"Transport Inv {t.get('invoice_no', '—')} — {p_name}",
                    "subtitle": f"Cases: {t.get('no_case', 0)} · LR: {t.get('lr_no', '—')}",
                    "time": t.get("created_at", ""),
                    "icon": ft.icons.LOCAL_SHIPPING_OUTLINED,
                    "accent": "#9333EA",
                })
        except Exception:
            pass

        # 4. Recent Final Invoices
        try:
            recent_invoices = select_recent("final_invoices", company_filter, order_by="created_at", limit=3)
            for inv in recent_invoices:
                p_name = party_map.get(str(inv.get("party_id", "")), "Unknown Party")
                amt = inv.get("net_amount") or inv.get("total_amount") or 0
                activity_items.append({
                    "title": f"Sales Invoice {inv.get('invoice_no', '—')} — {p_name}",
                    "subtitle": f"₹{float(amt):,.2f} · Final Invoice",
                    "time": inv.get("created_at", ""),
                    "icon": ft.icons.RECEIPT_LONG_OUTLINED,
                    "accent": "#059669",
                })
        except Exception:
            pass

        # 5. Recent Purchase Orders
        try:
            recent_po = select_recent("purchase_orders", company_filter, order_by="created_at", limit=3)
            for po in recent_po:
                p_name = party_map.get(str(po.get("supplier_id", "")), "Unknown Supplier")
                activity_items.append({
                    "title": f"Purchase Order {po.get('po_no', '—')} — {p_name}",
                    "subtitle": f"₹{float(po.get('total_amount', 0)):,.2f} · Pending",
                    "time": po.get("created_at", ""),
                    "icon": ft.icons.SHOPPING_CART_CHECKOUT_OUTLINED,
                    "accent": "#EA580C",
                })
        except Exception:
            pass

        # 6. Recent Purchase Invoices
        try:
            recent_pi = select_recent("purchase_invoices", company_filter, order_by="created_at", limit=3)
            for pi in recent_pi:
                p_name = party_map.get(str(pi.get("supplier_id", "")), "Unknown Supplier")
                activity_items.append({
                    "title": f"Purchase Invoice {pi.get('invoice_no', '—')} — {p_name}",
                    "subtitle": f"₹{float(pi.get('net_amount', 0)):,.2f} · Purchase",
                    "time": pi.get("created_at", ""),
                    "icon": ft.icons.FACT_CHECK_OUTLINED,
                    "accent": "#4F46E5",
                })
        except Exception:
            pass

        # 7. Recent Vouchers (Receipts)
        try:
            recent_receipts = select_recent("receipt_vouchers", company_filter, order_by="created_at", limit=3)
            for v in recent_receipts:
                p_name = party_map.get(str(v.get("party_id", "")), "Unknown Party")
                activity_items.append({
                    "title": f"Receipt Voucher — {p_name}",
                    "subtitle": f"₹{float(v.get('amount', 0)):,.2f} · {v.get('mode', 'Cash')}",
                    "time": v.get("created_at", ""),
                    "icon": ft.icons.PAYMENTS_OUTLINED,
                    "accent": "#D97706",
                })
        except Exception:
            pass

        # 5. Recently added Parties
        try:
            recent_parties = select_recent("parties", company_filter, order_by="created_at", limit=2)
            for p in recent_parties:
                activity_items.append({
                    "title": f"New Party: {p.get('name', '—')}",
                    "subtitle": f"City: {p.get('billing_city', '—')} · {p.get('party_type', 'Customer')}",
                    "time": p.get("created_at", ""),
                    "icon": ft.icons.PERSON_ADD_ALT_1_OUTLINED,
                    "accent": "#7C3AED",
                })
        except Exception:
            pass

        # 6. Recently added Items
        try:
            recent_items = select_recent("items", company_filter, order_by="created_at", limit=2)
            for it in recent_items:
                activity_items.append({
                    "title": f"New Item: {it.get('item_name', '—')}",
                    "subtitle": f"Code: {it.get('item_code', '—')} · {it.get('category', 'General')}",
                    "time": it.get("created_at", ""),
                    "icon": ft.icons.CHECKROOM_OUTLINED,
                    "accent": "#0891B2",
                })
        except Exception:
            pass

        # ── Sort all activity by timestamp (newest first) ──
        try:
            def sort_key(item):
                ts = item.get("time", "")
                return str(ts) if ts else ""

            activity_items.sort(key=sort_key, reverse=True)
        except Exception as e:
            print("Error sorting activity items:", e)

        # Limit to top 10 combined
        activity_items = activity_items[:10]

        # Build UI
        try:
            self.activity_col.controls.clear()
            if not activity_items:
                self.activity_col.controls.append(
                    ft.Container(
                        padding=40,
                        content=ft.Column([
                            ft.Icon(ft.icons.INBOX_OUTLINED, size=48, color=AppColors.TEXT_MUTED),
                            ft.Text("No recent activity yet", size=14, color=AppColors.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                            ft.Text("Start by creating orders, parties, or items", size=12, color=AppColors.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
                    )
                )
            else:
                for item in activity_items:
                    self.activity_col.controls.append(
                        self.build_activity_item(
                            item["title"],
                            item["subtitle"],
                            self._relative_time(item["time"]),
                            icon=item.get("icon", ft.icons.NOTIFICATIONS_OUTLINED),
                            accent=item.get("accent", AppColors.PRIMARY),
                        )
                    )
        except Exception as e:
            print("Error building activity UI:", e)
            self.activity_col.controls = [ft.Text(f"UI Error: {e}", color="red")]

        # Hide loading
        self.activity_loading.visible = False
        if self.page: self.update()

    def on_state_change(self, updated_state):
        self.load_data()

    def did_unmount(self):
        state.unsubscribe(self.on_state_change)

