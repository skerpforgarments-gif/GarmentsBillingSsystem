import flet as ft
from core.theme import AppColors, AppStyles


class FormBuilder(ft.Container):
    def __init__(self, fields, on_submit=None):
        super().__init__()

        self.expand = True
        self.padding = 24
        self.bgcolor = AppColors.BG_CARD
        self.border_radius = AppStyles.RADIUS
        self.shadow = AppStyles.CARD_SHADOW
        self.border = ft.border.all(1, "#F0F0F0")
        
        self.fields_config = fields
        self.on_submit = on_submit
        self.controls_map = {}

        # Build UI
        self.form_controls = self._build_controls()

        self.content = ft.Column(
            controls=self.form_controls + [
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Save Changes", 
                            icon=ft.icons.SAVE,
                            style=AppStyles.primary_button_style(),
                            on_click=self._submit,
                            height=45
                        ),
                        ft.TextButton(
                            "Clear Form", 
                            icon=ft.icons.REFRESH,
                            on_click=self.clear,
                            style=AppStyles.secondary_button_style()
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=15
                )
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO
        )

    def _build_controls(self):
        controls = []
        for field in self.fields_config:
            ctrl = self._create_control(field)
            self.controls_map[field["name"]] = ctrl
            controls.append(ctrl)
        return controls

    def _create_control(self, field):
        f_type = field.get("type", "text")
        label = field.get("label", "")
        default = field.get("default")
        
        # Consistent styling for all inputs
        style_args = AppStyles.get_input_style()
        style_args.update({
            "label": label,
            "value": default
        })

        if f_type == "text":
            return ft.TextField(**style_args, on_change=field.get("on_change"))

        elif f_type == "number":
            return ft.TextField(**style_args, keyboard_type=ft.KeyboardType.NUMBER, on_change=field.get("on_change"))

        elif f_type == "date":
            return ft.TextField(**style_args, hint_text="YYYY-MM-DD", icon=ft.icons.CALENDAR_MONTH, on_change=field.get("on_change"))

        elif f_type == "dropdown":
            options = field.get("options", [])
            return ft.Dropdown(
                **style_args,
                on_change=field.get("on_change"),
                options=[
                    ft.dropdown.Option(key=str(opt["value"]), text=opt["label"])
                    for opt in options
                ]
            )
        
        elif f_type == "info":
            return ft.Text(label, size=12, color=AppColors.TEXT_SUB, italic=True)

        return ft.TextField(**style_args)

    def get_values(self):
        data = {}
        for field in self.fields_config:
            if field.get("type") == "info": continue
            name = field["name"]
            ctrl = self.controls_map[name]
            value = ctrl.value
            data[name] = value if value not in ["", None] else None
        return data

    def set_values(self, data: dict):
        for name, value in data.items():
            if name in self.controls_map:
                ctrl = self.controls_map[name]
                if isinstance(ctrl, ft.Dropdown) and value is not None:
                    ctrl.value = str(value)
                else:
                    ctrl.value = value
        self.update()

    def load_metadata(self, *args, **kwargs):
        """Standard interface for metadata loading. Does nothing in base FormBuilder."""
        pass

    def clear(self, e=None):
        for ctrl in self.controls_map.values():
            ctrl.value = None
            ctrl.error_text = None
        self.update()

    def validate(self):
        is_valid = True
        for field in self.fields_config:
            name = field["name"]
            required = field.get("required", False)
            ctrl = self.controls_map[name]
            value = ctrl.value

            if required and not value:
                ctrl.error_text = "This field is required"
                is_valid = False
            else:
                ctrl.error_text = None

            if field.get("type") == "number" and value:
                try:
                    float(value)
                except:
                    ctrl.error_text = "Please enter a valid number"
                    is_valid = False
        self.update()
        return is_valid

    def _submit(self, e):
        if not self.validate():
            return
        data = self.get_values()
        if self.on_submit:
            self.on_submit(data)
