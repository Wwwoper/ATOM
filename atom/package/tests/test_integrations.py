"""Тесты для посылок и доставки."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from package.models import Package, PackageDelivery, TransportCompany
from package.services.delivery_service import PackageDeliveryService


@pytest.mark.django_db
class TestPackageIntegrations:
    """Тесты интеграций для посылок."""

    def test_create_package(self, user):
        """Тест создания посылки."""
        package = Package.objects.create(
            user=user,
            number="TEST001",
            shipping_cost_eur=Decimal("10.00"),
            fee_cost_eur=Decimal("2.00"),
        )

        assert package.number == "TEST001"
        assert package.shipping_cost_eur == Decimal("10.00")
        assert package.fee_cost_eur == Decimal("2.00")
        assert package.total_cost_eur == Decimal("12.00")

    def test_package_validation(self, user):
        """Тест валидации посылки."""
        # Тест пустого номера
        with pytest.raises(ValidationError) as exc:
            Package.objects.create(
                user=user,
                number="",
                shipping_cost_eur=Decimal("10.00"),
                fee_cost_eur=Decimal("2.00"),
            )
        error_dict = exc.value.message_dict
        assert "number" in error_dict
        assert any("не может быть пустым" in msg for msg in error_dict["number"])

        # Тест отрицательной стоимости
        with pytest.raises(ValidationError) as exc:
            Package.objects.create(
                user=user,
                number="TEST002",
                shipping_cost_eur=Decimal("-10.00"),
                fee_cost_eur=Decimal("2.00"),
            )
        error_dict = exc.value.message_dict
        assert "shipping_cost_eur" in error_dict
        assert any(
            "не может быть отрицательной" in msg
            for msg in error_dict["shipping_cost_eur"]
        )

    def test_package_unique_constraint(self, user):
        """Тест уникальности номера посылки для пользователя."""
        Package.objects.create(
            user=user,
            number="TEST003",
            shipping_cost_eur=Decimal("10.00"),
            fee_cost_eur=Decimal("2.00"),
        )

        with pytest.raises(ValidationError):
            Package.objects.create(
                user=user,
                number="TEST003",
                shipping_cost_eur=Decimal("15.00"),
                fee_cost_eur=Decimal("3.00"),
            )


@pytest.mark.django_db
class TestDeliveryIntegrations:
    """Тесты интеграций для доставок."""

    @pytest.fixture
    def transport_company(self):
        """Фикстура для создания транспортной компании."""
        return TransportCompany.objects.create(
            name="Test Company",
            is_active=True,
            is_default=True,
        )

    @pytest.fixture
    def package(self, user):
        """Фикстура для создания посылки."""
        from django.db import transaction
        from balance.models import Balance, Transaction
        from balance.services.constants import TransactionTypeChoices
        from decimal import Decimal

        with transaction.atomic():
            # Создаем транзакцию для установки начального баланса
            initial_transaction = Transaction(
                balance=user.balance,
                transaction_type=TransactionTypeChoices.REPLENISHMENT,
                amount_euro=Decimal("100.00"),
                amount_rub=Decimal("10000.00"),  # 100 EUR * 100 RUB/EUR
                comment="Initial balance for test",
            )
            initial_transaction.save(
                process_transaction=True
            )  # Сохраняем с флагом process_transaction

            # Создаем посылку
            package = Package.objects.create(
                user=user,
                number="TEST004",
                shipping_cost_eur=Decimal("10.00"),
                fee_cost_eur=Decimal("2.00"),
            )

            # Проверяем, что курс обмена установлен правильно
            package.refresh_from_db()
            if package.user.balance.average_exchange_rate != Decimal("100.00"):
                raise ValueError(
                    f"Курс обмена не установлен. Текущее значение: {package.user.balance.average_exchange_rate}"
                )

            return package

    def test_create_delivery(self, package, transport_company, delivery_status):
        """Тест создания доставки."""
        delivery = PackageDelivery.objects.create(
            package=package,
            transport_company=transport_company,
            status=delivery_status,
            tracking_number="TRACK001",
            weight=Decimal("1.5"),
        )

        assert delivery.tracking_number == "TRACK001"
        assert delivery.weight == Decimal("1.5")
        assert delivery.shipping_cost_rub == Decimal("0.00")
        assert delivery.price_rub_for_kg == Decimal("0.00")

    def test_delivery_validation(self, package, transport_company, delivery_status):
        """Тест валидации доставки."""
        # Тест пустого трек-номера
        with pytest.raises(ValidationError) as exc:
            delivery = PackageDelivery(
                package=package,
                transport_company=transport_company,
                status=delivery_status,
                tracking_number="",
                weight=Decimal("1.5"),
            )
            delivery.full_clean()  # Явно вызываем валидацию
        assert "Трек номер не может быть пустым" in str(exc.value)

        # Тест отрицательного веса
        with pytest.raises(ValidationError) as exc:
            delivery = PackageDelivery(
                package=package,
                transport_company=transport_company,
                status=delivery_status,
                tracking_number="TRACK002",
                weight=Decimal("-1.5"),
            )
            delivery.full_clean()  # Явно вызываем валидацию
        assert "Вес не может быть отрицательным" in str(exc.value)

    def test_delivery_cost_calculation(
        self, package, transport_company, delivery_status
    ):
        """Тест расчета стоимости доставки."""
        # Проверяем начальные условия
        assert package.total_cost_eur == Decimal("12.00")
        assert package.user.balance.average_exchange_rate == Decimal("100.00")

        delivery = PackageDelivery.objects.create(
            package=package,
            transport_company=transport_company,
            status=delivery_status,
            tracking_number="TRACK003",
            weight=Decimal("2.0"),
        )

        # Проверяем начальные значения
        assert delivery.shipping_cost_rub == Decimal("0.00")
        assert delivery.price_rub_for_kg == Decimal("0.00")

        # Пересчитываем стоимость
        delivery_service = PackageDeliveryService()
        delivery_service.calculate_delivery_costs(delivery)

        # Пеезагружаем объект из базы
        delivery.refresh_from_db()

        # Проверяем результаты
        expected_cost_rub = (
            package.total_cost_eur * package.user.balance.average_exchange_rate
        ).quantize(Decimal("0.01"))
        expected_price_per_kg = (expected_cost_rub / delivery.weight).quantize(
            Decimal("0.01")
        )

        assert delivery.shipping_cost_rub == expected_cost_rub
        assert delivery.price_rub_for_kg == expected_price_per_kg

    def test_delivery_status_transitions(
        self, package, transport_company, paid_delivery_status, delivery_status
    ):
        """Тест переходов между статусами доставки."""
        from package.services.delivery_service import PackageDeliveryService

        # Создаем доставку с пропуском обработки статуса
        delivery = PackageDelivery.objects.create(
            package=package,
            transport_company=transport_company,
            status=paid_delivery_status,
            tracking_number="TRACK004",
            weight=Decimal("1.0"),
        )

        # Используем сервис для расчета стоимости и обработки статуса
        delivery_service = PackageDeliveryService()
        delivery_service.calculate_delivery_costs(delivery)

        # Перезагружаем объект из базы
        delivery.refresh_from_db()

        # Проверяем, что доставка помечена как оплаченная
        assert delivery.paid_at is not None
        assert delivery.shipping_cost_rub > 0

        # Проверяем, что после отмены доставки стоимость обнуляется
        delivery.status = delivery_status  # статус "отменен"
        delivery.save(skip_status_processing=True)  # Пропускаем обработку статуса

        # Сбрасываем стоимость доставки через сервис
        delivery_service.reset_delivery_costs(delivery)

        # Перезагружаем объект
        delivery.refresh_from_db()

        assert delivery.paid_at is None
        assert delivery.shipping_cost_rub == Decimal("0.00")
        assert delivery.price_rub_for_kg == Decimal("0.00")
