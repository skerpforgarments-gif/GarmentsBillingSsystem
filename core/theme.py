import flet as ft

# =========================================================
# PREMIUM DESIGN SYSTEM (Theme Config)
# =========================================================

class AppColors:
    # Primary Palette
    PRIMARY = "#5A55D2"          # The dominant violet/indigo from images
    PRIMARY_LIGHT = "#EBEBFF"    # For hover/background of active items
    PRIMARY_DARK = "#4843B5"
    
    # Neutral Palette
    BG_MAIN = "#F8F9FD"          # Very soft grey/blue for main background
    BG_CARD = "#FFFFFF"          # Pure white for cards/sidebar
    
    # Text Palette
    TEXT_HEADER = "#1A1A4B"      # Deep navy for main headings
    TEXT_SUB = "#64748B"         # Muted blue-grey for secondary text
    TEXT_MUTED = "#94A3B8"       # For disabled/placeholder
    
    # Accents
    SUCCESS = "#22C55E"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"
    INFO = "#3B82F6"

class AppStyles:
    # Standard Border Radius
    RADIUS = 12
    BUTTON_RADIUS = 10
    
    # Premium Box Shadow (Soft & Subtle)
    CARD_SHADOW = ft.BoxShadow(
        blur_radius=15,
        color=ft.colors.with_opacity(0.05, "black"),
        offset=ft.Offset(0, 4),
        spread_radius=1
    )
    
    # Typography
    H1_SIZE = 28
    H2_SIZE = 22
    H3_SIZE = 18
    BODY_SIZE = 14
    SMALL_SIZE = 12

    @staticmethod
    def primary_button_style():
        return ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=AppColors.PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=AppStyles.BUTTON_RADIUS),
            padding=ft.padding.symmetric(horizontal=25, vertical=15),
        )

    @staticmethod
    def secondary_button_style():
        return ft.ButtonStyle(
            color=AppColors.TEXT_SUB,
            bgcolor=ft.colors.TRANSPARENT,
            shape=ft.RoundedRectangleBorder(radius=AppStyles.BUTTON_RADIUS),
            overlay_color=ft.colors.with_opacity(0.05, "black"),
        )

    @staticmethod
    def get_input_style():
        """Returns a standard dictionary of style arguments for TextFields and Dropdowns."""
        return {
            "dense": True,
            "text_size": 13,
            "height": 48,
            "border_radius": AppStyles.BUTTON_RADIUS,
            "border_color": "#E2E8F0",
            "focused_border_color": AppColors.PRIMARY,
            "focused_border_width": 2,
            "bgcolor": "#F8FAFC",
            "label_style": ft.TextStyle(color=AppColors.TEXT_SUB, size=12)
        }
