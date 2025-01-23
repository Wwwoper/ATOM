"""URLs для приложения order."""

from django.urls import path
from .views import download_orders_template, import_orders

app_name = "order"  # Добавляем namespace

urlpatterns = [
    path(
        "download-template/",
        download_orders_template,
        name="download_orders_template",
    ),
    path(
        "admin/order/import/",
        import_orders,
        name="import_orders",
    ),
]
