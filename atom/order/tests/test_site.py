"""Тесты модульного тестирования для модели Site.

Тесты проверяют корректность создания и удаления сайтов, а также
корректность сохранения их значений.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db import transaction
from user.services import UserService
from django.utils import timezone

from order.models import Site, Order
from status.models import Status


@pytest.mark.django_db
class TestSite:
    """Тесты для модели Site."""

    @pytest.fixture
    def valid_site_data(self):
        """Фикстура с валидными данными сайта."""
        return {
            "name": "Test Site",
            "url": "https://test-site.com",
            "organizer_fee_percentage": Decimal("10.00"),  # 10%
        }

    @pytest.fixture
    def user(self):
        """Фикстура для создания тестового пользователя."""
        user_service = UserService()
        return user_service.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_create_site(self, valid_site_data):
        """Тест создания сайта с валидными данными."""
        site = Site.objects.create(**valid_site_data)

        assert site.pk is not None
        assert site.name == valid_site_data["name"]
        assert site.url == valid_site_data["url"]
        assert (
            site.organizer_fee_percentage == valid_site_data["organizer_fee_percentage"]
        )

    def test_organizer_fee_validation(self, valid_site_data):
        """Тест валидации процента комиссии (0-100)."""
        # Тест валидных значений
        valid_fees = [Decimal("0.00"), Decimal("50.00"), Decimal("100.00")]
        for i, fee in enumerate(valid_fees):
            site_data = valid_site_data.copy()
            site_data["organizer_fee_percentage"] = fee
            site_data["name"] = f"Test Site {i}"  # Уникальное имя
            site_data["url"] = f"https://test-site-{i}.com"  # Уникальный URL
            site = Site.objects.create(**site_data)
            assert site.organizer_fee_percentage == fee

        # Тест невалидных значений
        invalid_fees = [Decimal("-1.00"), Decimal("101.00")]
        for fee in invalid_fees:
            site_data = valid_site_data.copy()
            site_data["organizer_fee_percentage"] = fee
            with pytest.raises(ValidationError):
                site = Site.objects.create(**site_data)

    def test_unique_constraints(self, valid_site_data):
        """Тест уникальности name и url."""
        Site.objects.create(**valid_site_data)

        # Попытка создать сайт с тем же именем
        duplicate_name = valid_site_data.copy()
        duplicate_name["url"] = "https://another-site.com"

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Site.objects.create(**duplicate_name)

        # Попытка создать сайт с тем же URL
        duplicate_url = valid_site_data.copy()
        duplicate_url["name"] = "Another Site"

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Site.objects.create(**duplicate_url)

    def test_total_orders_property(self, valid_site_data, user):
        """Тест подсчета общего количества заказов."""
        site = Site.objects.create(**valid_site_data)
        default_status = Status.objects.get(
            group__code="ORDER_STATUS_CONFIG", is_default=True
        )
        paid_status = Status.objects.get(group__code="ORDER_STATUS_CONFIG", code="paid")

        # Создаем заказы в разных статусах
        Order.objects.create(
            user=user,
            site=site,
            internal_number="INT-1",
            external_number="EXT-1",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            status=default_status,
        )
        Order.objects.create(
            user=user,
            site=site,
            internal_number="INT-2",
            external_number="EXT-2",
            amount_euro=Decimal("200.00"),
            amount_rub=Decimal("20000.00"),
            status=paid_status,
        )

        assert site.total_orders == 2

    def test_total_profit_property(self, user_with_balance, site, paid_status):
        """Тест подсчета общей прибыли сайта."""
        exchange_rate = Decimal("100.00")
        amount_euro = Decimal("100.00")
        amount_rub = (amount_euro * exchange_rate).quantize(Decimal("0.01"))
        profit = Decimal("10.00")

        order = Order(
            user=user_with_balance,  # Используем пользователя с балансом
            site=site,
            status=paid_status,
            internal_number="TEST-001",
            external_number="ZARA-001",
            amount_euro=amount_euro,
            amount_rub=amount_rub,
            profit=profit,
            created_at=timezone.now().date(),
        )
        order.full_clean()
        order.save()

        assert site.total_profit == profit

    def test_str_method(self, valid_site_data):
        """Тест строкового представления."""
        site = Site.objects.create(**valid_site_data)
        assert str(site) == valid_site_data["name"]

    def test_site_deletion_with_orders(self, valid_site_data, user):
        """Тест запрета удаления сайта с существующими заказами."""
        # Создаем сайт
        site = Site.objects.create(**valid_site_data)
        default_status = Status.objects.get(
            group__code="ORDER_STATUS_CONFIG", is_default=True
        )

        # Создаем заказ для сайта
        Order.objects.create(
            user=user,
            site=site,
            internal_number="INT-1",
            external_number="EXT-1",
            amount_euro=Decimal("100.00"),
            amount_rub=Decimal("10000.00"),
            status=default_status,
        )

        # Проверяем, что сайт нельзя удалить
        with pytest.raises(ValidationError) as exc_info:
            site.delete()

        assert "Невозможно удалить сайт, пока с ним связаны заказы" in str(
            exc_info.value
        )
        assert Site.objects.filter(pk=site.pk).exists()

        # Проверяем, что сайт без заказов можно удалить
        new_site = Site.objects.create(
            name="Test Site 2",
            url="https://test-site-2.com",
            organizer_fee_percentage=Decimal("10.00"),
        )
        new_site.delete()
        assert not Site.objects.filter(pk=new_site.pk).exists()
