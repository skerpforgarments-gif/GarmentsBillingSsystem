import flet as ft
from core.layout import MainLayout
from core.state import state
from core.theme import AppColors

# Supabase client (ensures connection is initialized)
from services.supabase_client import supabase


# =========================================================
# APP START
# =========================================================
def main(page: ft.Page):
    # -----------------------------
    # PAGE CONFIG
    # -----------------------------
    page.title = "Garments ERP (SaaS) | Premium Edition"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=AppColors.PRIMARY,
        visual_density=ft.ThemeVisualDensity.COMPACT,
    )
    page.window_width = 1300
    page.window_height = 900
    page.window_maximized = True
    page.padding = 0
    page.bgcolor = ft.colors.WHITE

    # -----------------------------
    # GLOBAL STATE INIT
    # -----------------------------
    state.current_user = None
    state.current_company = None
    state.company_id = None
    state.page = page  # Allow state to update page title dynamically

    # -----------------------------
    # BASIC CONNECTION CHECK
    # -----------------------------
    if supabase:
        print("[SUCCESS] Supabase client initialized")
    else:
        print("[ERROR] Supabase client initialization failed")

    # -----------------------------
    # LOAD MAIN LAYOUT
    # -----------------------------
    layout = MainLayout(page)

    # Attach router (important)
    page.add(layout)

    # -----------------------------
    # INITIAL ROUTE
    # -----------------------------
    layout.router.go("login")

    # -----------------------------
    # RENDER
    # -----------------------------
    page.update()


# =========================================================
# RUN APP
# =========================================================
if __name__ == "__main__":
    import os
    os.makedirs(os.path.join("assets", "logos"), exist_ok=True)
    ft.app(target=main, assets_dir="assets")
