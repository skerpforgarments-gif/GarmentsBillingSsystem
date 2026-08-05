import flet as ft
from core.state import state
from core.theme import AppColors, AppStyles
from services.supabase_client import supabase

class LoginScreen(ft.Container):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        
        self.expand = True
        self.alignment = ft.alignment.center
        
        # =========================
        # UI ELEMENTS
        # =========================
        style_args = {
            "border_radius": AppStyles.BUTTON_RADIUS,
            "border_color": "#E2E8F0",
            "focused_border_color": AppColors.PRIMARY,
            "text_size": 14,
            "height": 55,
            "bgcolor": "#F8FAFC",
            "label_style": ft.TextStyle(color=AppColors.TEXT_SUB, size=12)
        }

        self.email = ft.TextField(
            label="Corporate Email",
            prefix_icon=ft.icons.EMAIL_OUTLINED,
            on_submit=lambda _: self.password.focus(),
            **style_args
        )

        self.password = ft.TextField(
            label="Secure Password",
            prefix_icon=ft.icons.LOCK_OUTLINED,
            password=True,
            can_reveal_password=True,
            on_submit=self.handle_login,
            **style_args
        )

        self.login_btn = ft.ElevatedButton(
            "Access Systems",
            icon=ft.icons.LOCK_OPEN_ROUNDED,
            style=AppStyles.primary_button_style(),
            width=400,
            height=55,
            on_click=self.handle_login
        )

        self.error_text = ft.Text("", color=ft.colors.RED_400, size=12, weight="w500")

        # =========================
        # LAYOUT (Split Screen)
        # =========================
        self.content = ft.Row(
            expand=True,
            spacing=0,
            controls=[
                # Left Side: Branding & Gradients
                ft.Container(
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_left,
                        end=ft.alignment.bottom_right,
                        colors=[AppColors.TEXT_HEADER, AppColors.PRIMARY, AppColors.PRIMARY_DARK]
                    ),
                    content=ft.Column([
                        ft.Container(height=40),
                        ft.Icon(ft.icons.AUTO_AWESOME, size=50, color="white"),
                        ft.Text("Garments ERP", size=32, weight="bold", color="white"),
                        ft.Text("The Intelligent Transaction Engine\nfor Tirupur Apparel Cluster.", 
                                size=16, color="white", opacity=0.8, text_align=ft.TextAlign.CENTER),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40
                ),
                
                # Right Side: Login Form
                ft.Container(
                    expand=True,
                    bgcolor="white",
                    padding=60,
                    content=ft.Column([
                        ft.Text("Welcome Back", size=AppStyles.H1_SIZE, weight="bold", color=AppColors.TEXT_HEADER),
                        ft.Text("Enter your credentials to manage your business.", color=AppColors.TEXT_SUB),
                        ft.Divider(height=30, color=ft.colors.TRANSPARENT),
                        
                        self.email,
                        ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                        self.password,
                        self.error_text,
                        
                        ft.Divider(height=20, color=ft.colors.TRANSPARENT),
                        self.login_btn,
                        
                        ft.Divider(height=40, color=ft.colors.TRANSPARENT),
                        ft.Text("Powered by Antigravity v2.0", size=10, color=ft.colors.GREY_400)
                    ], alignment=ft.MainAxisAlignment.CENTER)
                )
            ]
        )

    def handle_login(self, e):
        email_val = self.email.value
        pass_val = self.password.value

        if not email_val or not pass_val:
            self.error_text.value = "Credentials required."
            self.update()
            return

        self.login_btn.disabled = True
        self.login_btn.text = "Authenticating..."
        self.update()

        try:
            res = supabase.auth.sign_in_with_password({
                "email": email_val,
                "password": pass_val
            })
            user = res.user
            if not user: raise Exception("Auth failed")

            response = supabase.table("companies").select("*").eq("user_id", user.id).execute()
            companies = response.data
            
            if not companies:
                # Try fetching any company in the database
                all_comp = supabase.table("companies").select("*").execute()
                if all_comp.data:
                    company = all_comp.data[0]
                else:
                    # Auto-create a default company profile if no companies exist yet
                    new_comp = supabase.table("companies").insert({
                        "name": "Mirthulla Exports",
                        "user_id": user.id,
                        "address": "Tirupur, Tamil Nadu",
                        "gst_details": "33AABCM1234A1Z5"
                    }).execute()
                    company = new_comp.data[0] if new_comp.data else {"name": "Garments ERP", "id": 1}
            else:
                company = companies[0]

            state.set_user(user)
            state.set_company(company)

            if self.on_login_success:
                self.on_login_success()

        except Exception as ex:
            self.error_text.value = str(ex)
            self.login_btn.disabled = False
            self.login_btn.text = "Access Systems"
            self.update()
