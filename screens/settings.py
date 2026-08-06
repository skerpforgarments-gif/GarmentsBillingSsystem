import flet as ft
from core.theme import AppColors
from core.state import state
from database.db import select, update

S = {
    "bgcolor": "#F8FAFC",
    "border_color": "#E2E8F0",
    "focused_border_color": AppColors.PRIMARY,
    "border_radius": 8,
    "content_padding": 12,
    "text_size": 13,
}

class SettingsScreen(ft.Container):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = AppColors.BG_MAIN
        self.padding = 24

        # ─── Form Fields ───────────────────────────────────────
        self.comp_name = ft.TextField(label="Company Name *", width=340, **S)
        self.comp_code = ft.TextField(label="Company Code (e.g. MIR)", width=160, **S)
        self.branch_code = ft.TextField(label="Branch Code", width=160, **S)
        
        self.address = ft.TextField(label="Address", width=480, multiline=True, min_lines=2, max_lines=3, **S)
        self.city = ft.TextField(label="City", width=200, **S)
        self.state_code = ft.TextField(label="State Code (e.g. 33)", value="33", width=140, **S)
        
        self.phone = ft.TextField(label="Phone (Landline)", width=220, **S)
        self.mobile = ft.TextField(label="Mobile / Phone (Header)", width=220, **S)
        self.email = ft.TextField(label="Email Address", width=240, **S)
        self.website = ft.TextField(label="Website", width=240, **S)

        self.gstin = ft.TextField(label="GSTIN", width=220, **S)
        self.pan_no = ft.TextField(label="PAN Number", width=180, **S)
        self.financial_period = ft.TextField(label="Financial Period (e.g. 2025-2026)", width=240, **S)

        self.status_msg = ft.Text("", size=13, weight="w500")

        # ─── UI Layout ─────────────────────────────────────────
        self.content = ft.Column([
            # Page Title
            ft.Row([
                ft.Icon(ft.icons.SETTINGS_OUTLINED, size=28, color=AppColors.PRIMARY),
                ft.Column([
                    ft.Text("Company Settings", size=22, weight="bold", color=AppColors.TEXT_HEADER),
                    ft.Text("Manage your business details, contact information, and GST settings", size=12, color=AppColors.TEXT_MUTED),
                ], spacing=2)
            ], spacing=12),

            ft.Divider(height=20, color="transparent"),

            # Scrollable Card Container
            ft.Container(
                expand=True,
                padding=24,
                bgcolor=ft.colors.WHITE,
                border_radius=12,
                border=ft.border.all(1, "#E2E8F0"),
                shadow=ft.BoxShadow(blur_radius=10, color="#0A000000"),
                content=ft.Column([
                    # Section 1: Basic Company Info
                    self._build_section_header("Basic Information", ft.icons.BUSINESS),
                    ft.Row([self.comp_name, self.comp_code, self.branch_code], spacing=16, wrap=True),
                    
                    ft.Divider(height=24, color="#F1F5F9"),

                    # Section 2: Address & Location
                    self._build_section_header("Location & Address", ft.icons.LOCATION_ON_OUTLINED),
                    ft.Row([self.address, self.city, self.state_code], spacing=16, wrap=True),

                    ft.Divider(height=24, color="#F1F5F9"),

                    # Section 3: Contact Details
                    self._build_section_header("Contact Details", ft.icons.PHONE_OUTLINED),
                    ft.Row([self.mobile, self.phone, self.email, self.website], spacing=16, wrap=True),

                    ft.Divider(height=24, color="#F1F5F9"),

                    # Section 4: Tax & Financial Info
                    self._build_section_header("Taxation & Financial", ft.icons.RECEIPT_LONG_OUTLINED),
                    ft.Row([self.gstin, self.pan_no, self.financial_period], spacing=16, wrap=True),

                    ft.Divider(height=32, color="#F1F5F9"),

                    # Save Action Button
                    ft.Row([
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.icons.SAVE, size=18, color=ft.colors.WHITE),
                                ft.Text("Save Company Settings", size=14, weight="bold", color=ft.colors.WHITE)
                            ], spacing=8),
                            style=ft.ButtonStyle(
                                bgcolor=AppColors.PRIMARY,
                                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                            on_click=self.save_settings
                        ),
                        self.status_msg
                    ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                ], scroll=ft.ScrollMode.AUTO, spacing=12)
            )
        ])

    def did_mount(self):
        self.load_company_data()

    def _build_section_header(self, title, icon):
        return ft.Row([
            ft.Icon(icon, size=18, color=AppColors.PRIMARY),
            ft.Text(title, size=15, weight="bold", color=AppColors.PRIMARY)
        ], spacing=8)

    def load_company_data(self):
        if not state.company_id:
            return

        c_data = select("companies", {"id": state.company_id})
        if not c_data:
            return

        c = c_data[0]
        self.comp_name.value = c.get("name", "")
        self.comp_code.value = c.get("company_code", "")
        self.branch_code.value = c.get("branch_code", "")
        
        self.address.value = c.get("address", "")
        self.city.value = c.get("city", "")
        self.state_code.value = c.get("state_code", "33") or "33"
        
        self.phone.value = c.get("phone", "")
        self.mobile.value = c.get("mobile", "")
        self.email.value = c.get("email", "")
        self.website.value = c.get("website", "")
        
        self.gstin.value = c.get("gst_details", "")
        self.pan_no.value = c.get("pan_no", "")
        self.financial_period.value = c.get("financial_period", "")
        
        if self.page:
            self.update()

    def save_settings(self, e):
        if not self.comp_name.value:
            self.comp_name.error_text = "Company Name is required"
            self.update()
            return

        self.comp_name.error_text = None
        
        payload = {
            "name": self.comp_name.value.strip(),
            "company_code": self.comp_code.value.strip(),
            "branch_code": self.branch_code.value.strip(),
            "address": self.address.value.strip(),
            "city": self.city.value.strip(),
            "state_code": self.state_code.value.strip(),
            "phone": self.phone.value.strip(),
            "mobile": self.mobile.value.strip(),
            "email": self.email.value.strip(),
            "website": self.website.value.strip(),
            "gst_details": self.gstin.value.strip(),
            "pan_no": self.pan_no.value.strip(),
            "financial_period": self.financial_period.value.strip(),
        }

        res = update("companies", payload, {"id": state.company_id})
        if res:
            # Sync company state globally
            c_dict = dict(res[0]) if isinstance(res, list) and res else payload
            c_dict["id"] = state.company_id
            state.set_company(c_dict)

            self.status_msg.value = "✅ Settings saved successfully!"
            self.status_msg.color = "green"
            
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text("✅ Company Details Updated Successfully!"), bgcolor="green")
                self.page.snack_bar.open = True
                self.page.update()
        else:
            self.status_msg.value = "❌ Failed to save settings. Please try again."
            self.status_msg.color = "red"
            if self.page:
                self.page.update()
