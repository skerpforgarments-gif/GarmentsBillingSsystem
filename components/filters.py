import flet as ft
from core.theme import AppColors, AppStyles



class FilterBar(ft.Container):
    def __init__(self, filters, on_apply=None):
        """
        filters: [
            {
                "name": "party_id",
                "label": "Party",
                "type": "dropdown",
                "options": [{"label": "ABC", "value": 1}],
                "default": None
            },
            {
                "name": "from_date",
                "label": "From Date",
                "type": "date"
            }
        ]

        on_apply: function(dict)
        """
        super().__init__()

        self.expand = True
        self.padding = 10

        self.filters_config = filters
        self.on_apply = on_apply

        self.controls_map = {}

        # Build UI
        self.filter_controls = self._build_controls()

        self.content = ft.Column(
            controls=[
                ft.Row(self.filter_controls, wrap=True, spacing=10),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Apply Filters", 
                            icon=ft.icons.FILTER_LIST, 
                            on_click=self._apply,
                            style=AppStyles.primary_button_style(),
                            height=40
                        ),
                        ft.TextButton(
                            "Reset", 
                            on_click=self._reset,
                            style=AppStyles.secondary_button_style()
                        ),
                    ],
                    spacing=12
                )
            ],
            spacing=10
        )

    # =========================================================
    # BUILD CONTROLS
    # =========================================================
    def _build_controls(self):
        controls = []

        for f in self.filters_config:
            ctrl = self._create_control(f)
            self.controls_map[f["name"]] = ctrl
            controls.append(ctrl)

        return controls

    # =========================================================
    # CONTROL FACTORY
    # =========================================================
    def _create_control(self, f):
        f_type = f.get("type", "text")
        label = f.get("label", "")
        default = f.get("default")

        style_args = {
            "dense": True,
            "text_size": 13,
            "height": 45,
            "border_radius": AppStyles.BUTTON_RADIUS,
            "border_color": "#E2E8F0",
            "focused_border_color": AppColors.PRIMARY,
            "bgcolor": "#F8FAFC",
            "label_style": ft.TextStyle(color=AppColors.TEXT_SUB, size=12)
        }

        # TEXT
        if f_type == "text":
            ctrl = ft.TextField(label=label, width=200, value=default, **style_args)

        # NUMBER
        elif f_type == "number":
            ctrl = ft.TextField(
                label=label,
                width=150,
                value=default,
                keyboard_type=ft.KeyboardType.NUMBER,
                **style_args
            )

        # DATE
        elif f_type == "date":
            ctrl = ft.TextField(
                label=label,
                width=180,
                hint_text="YYYY-MM-DD",
                value=default,
                **style_args
            )

        # DROPDOWN
        elif f_type == "dropdown":
            options = f.get("options", [])

            ctrl = ft.Dropdown(
                label=label,
                width=200,
                value=default,
                options=[
                    ft.dropdown.Option(
                        key=str(opt["value"]),
                        text=opt["label"]
                    )
                    for opt in options
                ],
                **style_args
            )

        else:
            ctrl = ft.TextField(label=label, width=200, value=default)

        return ctrl

    # =========================================================
    # GET VALUES
    # =========================================================
    def get_values(self):
        data = {}

        for name, ctrl in self.controls_map.items():
            value = ctrl.value

            # normalize empty
            if value in ["", None]:
                data[name] = None
            else:
                data[name] = value

        return data

    # =========================================================
    # APPLY
    # =========================================================
    def _apply(self, e):
        values = self.get_values()

        if self.on_apply:
            self.on_apply(values)

    # =========================================================
    # RESET
    # =========================================================
    def _reset(self, e):
        for ctrl in self.controls_map.values():
            ctrl.value = None

        self.update()

        if self.on_apply:
            self.on_apply({})

    # =========================================================
    # SET VALUES (for presets / saved filters)
    # =========================================================
    def set_values(self, values: dict):
        for name, value in values.items():
            if name in self.controls_map:
                self.controls_map[name].value = value

        self.update()
