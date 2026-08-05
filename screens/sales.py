import flet as ft
import uuid
import json
import math
from datetime import date
from core.state import state
from core.theme import AppColors, AppStyles
from database.db import select, insert, update, delete, get_next_doc_no
from components.size_matrix import SizeMatrixModal, sort_sizes
from core.pdf_gen import pdf_engine, print_pdf
import os


from screens.order_entry import OrderEntryTab

class SalesScreen(ft.Column):
    def __init__(self):
        super().__init__()
        self.expand  = True
        self.spacing = 0

        self.order_tab     = OrderEntryTab()

        self.tab_bar = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            expand=True,
            label_color=AppColors.PRIMARY,
            unselected_label_color=AppColors.TEXT_SUB,
            indicator_color=AppColors.PRIMARY,
            tabs=[
                ft.Tab(text="Sales Invoice",       content=self.order_tab),
            ],
        )

        self.controls = [self.tab_bar]
