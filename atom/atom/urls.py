"""Конфигурация URL маршрутов проекта ATOM.

Этот модуль определяет основные URL маршруты проекта:
- Административный интерфейс
- API endpoints
- Статические файлы
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("order/", include("order.urls", namespace="order")),  # Добавляем namespace
]
