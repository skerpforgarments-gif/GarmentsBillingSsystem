import flet as ft

from core.router import Router
from core.theme import AppColors, AppStyles
from core.state import state


class MainLayout(ft.Row):
    def __init__(self, page: ft.Page):
        super().__init__()

        self.main_page = page
        self.expand = True
        self.active_route = "dashboard"

        # =========================
        # CONTENT AREA (RIGHT SIDE)
        # =========================
        self.content_area = ft.Container(
            expand=True,
            padding=0,
            bgcolor=ft.colors.WHITE,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

        # =========================
        # ROUTER
        # =========================
        self.router = Router(self)

        # =========================
        # SIDEBAR
        # =========================
        self.nav_items = [
            ("Dashboard", "dashboard", ft.icons.DASHBOARD),
            ("Masters", "masters", ft.icons.STORAGE),
            ("Purchases", "purchases", ft.icons.SHOPPING_BAG),
            ("Sales", "sales", ft.icons.SHOPPING_CART),
            ("Dyeing", "dyeing", ft.icons.COLOR_LENS),
            ("Knitting", "knitting", ft.icons.PRECISION_MANUFACTURING),
            ("Cheque", "cheque", ft.icons.ACCOUNT_BALANCE),
            ("Reports", "reports", ft.icons.BAR_CHART),
            ("Settings", "settings", ft.icons.SETTINGS),
        ]
        self.nav_buttons = {}
        self.sidebar_column = ft.Column(spacing=5)
        self.sidebar = self.build_sidebar()

        # =========================
        # LAYOUT STRUCTURE
        # =========================
        self.controls = [
            self.sidebar,
            self.content_area
        ]
        
        # Subscribe to state changes to update company name dynamically
        state.subscribe(self.on_state_change)

    # =========================================================
    # SIDEBAR
    # =========================================================
    def build_sidebar(self):
        # Build Navigation items
        # Header
        self.company_name_text = ft.Text("Garments ERP", size=20, weight="bold", color=ft.colors.WHITE, overflow=ft.TextOverflow.ELLIPSIS)
        self.sidebar_logo = ft.Image(width=32, height=32, fit=ft.ImageFit.CONTAIN, visible=False, border_radius=4)
        self.sidebar_icon = ft.Icon(ft.icons.AUTO_AWESOME, color=ft.colors.WHITE, size=24)
        
        self.sidebar_column.controls = [
            ft.Container(
                content=ft.Row([
                    ft.Stack([
                        self.sidebar_icon,
                        self.sidebar_logo
                    ], width=32, height=32),
                    self.company_name_text,
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                padding=ft.padding.only(left=5, top=20, bottom=30)
            ),
        ]

        for text, route, icon in self.nav_items:
            btn = self.create_nav_item(text, route, icon)
            self.nav_buttons[route] = btn
            self.sidebar_column.controls.append(btn)

        # Add logout at the bottom
        self.sidebar_column.controls.append(ft.Container(expand=True))
        self.sidebar_column.controls.append(
            self.create_nav_item("Logout", "login", ft.icons.LOGOUT)
        )

        return ft.Container(
            width=260,
            bgcolor=AppColors.TEXT_HEADER,
            padding=15,
            border=ft.border.only(right=ft.border.BorderSide(1, "#2D2D5F")),
            content=self.sidebar_column
        )

    # =========================================================
    # CREATE NAV ITEM
    # =========================================================
    def create_nav_item(self, text, route, icon):
        is_active = self.active_route == route
        
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=20, color=ft.colors.WHITE if is_active else ft.colors.with_opacity(0.7, ft.colors.WHITE)),
                ft.Text(text, size=14, weight="bold" if is_active else "w500", 
                        color=ft.colors.WHITE if is_active else ft.colors.with_opacity(0.7, ft.colors.WHITE))
            ], spacing=15),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=10,
            bgcolor=ft.colors.with_opacity(0.15, ft.colors.WHITE) if is_active else None,
            on_click=lambda e: self.router.go(route),
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT)
        )

    # =========================================================
    # SET SCREEN (CALLED BY ROUTER)
    # =========================================================
    def set_screen(self, screen):
        # Update active state in sidebar
        from screens.login import LoginScreen
        
        # Determine route from screen type (simplified for this design)
        # In a real app, the router would pass the name back
        route_map = {
            "DashboardScreen": "dashboard",
            "MastersScreen": "masters",
            "SalesScreen": "sales",
            "ReportsScreen": "reports",
            "YarnPOScreen": "purchases",
            "DyeingProgramScreen": "dyeing",
            "KnittingProgramScreen": "knitting",
            "ChequeEntryScreen": "cheque",
        }
        screen_name = screen.__class__.__name__
        self.active_route = route_map.get(screen_name, "dashboard")
        
        # Refresh sidebar styles
        for route, btn in self.nav_buttons.items():
            is_active = self.active_route == route
            btn.bgcolor = ft.colors.with_opacity(0.15, ft.colors.WHITE) if is_active else None
            btn.content.controls[0].color = ft.colors.WHITE if is_active else ft.colors.with_opacity(0.7, ft.colors.WHITE)
            btn.content.controls[1].color = ft.colors.WHITE if is_active else ft.colors.with_opacity(0.7, ft.colors.WHITE)
            btn.content.controls[1].weight = "bold" if is_active else "w500"

        self.sidebar.visible = not isinstance(screen, LoginScreen)
        self.content_area.content = screen
        self.update()

    def on_state_change(self, app_state):
        if app_state.current_company:
            self.company_name_text.value = app_state.current_company.get("name", "Garments ERP")
            
            import os
            import time
            logo_path = os.path.join(os.getcwd(), "assets", "logos", f"{app_state.company_id}.png")
            if os.path.exists(logo_path):
                self.sidebar_logo.src = f"logos/{app_state.company_id}.png?t={int(time.time())}"
                self.sidebar_logo.visible = True
                self.sidebar_icon.visible = False
            else:
                self.sidebar_logo.visible = False
                self.sidebar_icon.visible = True
        else:
            self.company_name_text.value = "Garments ERP"
            self.sidebar_logo.visible = False
            self.sidebar_icon.visible = True
            
        self.company_name_text.color = ft.colors.WHITE
        try:
            self.update()
        except:
            pass
