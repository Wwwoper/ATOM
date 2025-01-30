"""
Глобальная конфигурация pytest для проекта.

Содержит:
- Настройку PYTHONPATH
- Базовую конфигурацию тестовой БД
- Очистку таблиц перед тестами
"""

import os
import sys
import pytest
from django.core.management import call_command


# Добавляем корневую директорию проекта в PYTHONPATH
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)


@pytest.fixture(scope="session")
def my_django_db_setup(django_db_setup, django_db_blocker):
    """
    Настройка базы данных для тестов.

    Применяет миграции один раз за сессию тестов.
    """
    with django_db_blocker.unblock():
        call_command("migrate")


@pytest.fixture(scope="function", autouse=True)
def clean_tables(django_db_setup, db):
    """
    Очистка таблиц перед каждым тестом.

    Удаляет данные из всех связанных таблиц в правильном порядке,
    чтобы избежать проблем с внешними ключами.
    """
    from order.models import Order
    from package.models import Package, PackageDelivery, PackageOrder
    from balance.models import Transaction

    # Очищаем все связанные таблицы в правильном порядке
    PackageDelivery.objects.all().delete()
    PackageOrder.objects.all().delete()
    Package.objects.all().delete()
    Transaction.objects.all().delete()
    Order.objects.all().delete()
