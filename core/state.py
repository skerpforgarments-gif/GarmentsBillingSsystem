import json
import os

class AppState:
    def __init__(self):
        # =========================
        # AUTH / USER
        # =========================
        self.current_user = None

        # =========================
        # MULTI-COMPANY (CRITICAL)
        # =========================
        self.current_company = None
        self.company_id = None
        self.page = None  # Reference to ft.Page for dynamic title updates

        # =========================
        # APP CONTEXT & SETTINGS
        # =========================
        self.sales_mode = "order"  # order / packing / transport / invoice
        self.settings = {"direct_invoice": False}
        self.load_settings()

        # =========================
        # SUBSCRIBERS
        # =========================
        self._subscribers = []

    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    self.settings.update(json.load(f))
        except:
            pass
            
    def save_settings(self):
        try:
            with open("settings.json", "w") as f:
                json.dump(self.settings, f)
            self._notify()
        except:
            pass

    # =========================================================
    # SUBSCRIBE
    # =========================================================
    def subscribe(self, callback):
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    # =========================================================
    # UNSUBSCRIBE
    # =========================================================
    def unsubscribe(self, callback):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    # =========================================================
    # NOTIFY ALL
    # =========================================================
    def _notify(self):
        for callback in self._subscribers:
            callback(self)

    # =========================================================
    # SET USER
    # =========================================================
    def set_user(self, user):
        """
        user: dict from Supabase auth
        """
        self.current_user = user
        self._notify()

    # =========================================================
    # SET COMPANY (CRITICAL)
    def set_company(self, company: dict):
        """
        company: {
            "id": 1,
            "name": "ABC Garments",
            "logo_base64": "..."
        }
        """
        self.current_company = company
        self.company_id = company.get("id")
        
        # Sync logo from base64 if present
        import base64
        import os
        logo_b64 = company.get("logo_base64")
        logo_path = os.path.join(os.getcwd(), "assets", "logos", f"{self.company_id}.png")
        if logo_b64:
            try:
                os.makedirs(os.path.dirname(logo_path), exist_ok=True)
                with open(logo_path, "wb") as f:
                    f.write(base64.b64decode(logo_b64))
            except Exception as e:
                print("Error syncing logo:", e)
        else:
            # Remove stale local logo if it exists
            if os.path.exists(logo_path):
                try: os.remove(logo_path)
                except: pass

        # Dynamically update the window title with the company name
        if self.page and company.get("name"):
            self.page.title = f"{company['name']} | ERP System"
            try:
                self.page.update()
            except Exception:
                pass
        self._notify()

    # =========================================================
    # SET SALES MODE
    # =========================================================
    def set_sales_mode(self, mode: str):
        self.sales_mode = mode
        self._notify()

    # =========================================================
    # CLEAR SESSION (LOGOUT)
    # =========================================================
    def clear(self):
        self.current_user = None
        self.current_company = None
        self.company_id = None
        self.sales_mode = "order"
        # Reset title on logout
        if self.page:
            self.page.title = "Garments ERP | Login"
            try:
                self.page.update()
            except Exception:
                pass
        self._notify()


# =========================================================
# SINGLETON INSTANCE
# =========================================================
state = AppState()
