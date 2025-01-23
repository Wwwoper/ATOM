"""Views для приложения order.

Модуль содержит представления для:
- Скачивания шаблона Excel для импорта заказов
- Импорта заказов из Excel файла
"""

import pandas as pd
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import admin

from .models import Order


@staff_member_required
def download_orders_template(request):
    """Скачивание шаблона для импорта заказов."""
    # Создаем шаблон для заполнения
    template_data = [
        {
            "Внутренний номер": "ORDER-001",
            "Внешний номер": "SHOP-001",
            "Сайт": "Название существующего сайта",
            "Пользователь": "email@example.com",
            "Статус": "Название существующего статуса",
            "Сумма (EUR)": 100.00,
            "Сумма (RUB)": 10000.00,
            "Комментарий": "Пример комментария",
        }
    ]
    df = pd.DataFrame(template_data)

    # Создаем response с шаблоном
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="orders_template.xlsx"'
    df.to_excel(response, index=False, engine="openpyxl")
    return response


@staff_member_required
def import_orders(request):
    """Обработка импорта заказов."""
    from .admin import OrderAdmin

    order_admin = OrderAdmin(model=Order, admin_site=admin.site)
    return order_admin.import_from_xlsx(request)
