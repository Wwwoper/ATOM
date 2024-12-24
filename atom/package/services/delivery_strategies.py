"""Стратегия для работы со статусами доставки посылок."""

from abc import ABC, abstractmethod
from decimal import Decimal

from balance.services.constants import TransactionTypeChoices
from balance.services.transaction_service import TransactionProcessor
from django.forms import ValidationError

from .delivery_service import PackageDeliveryService


class PackageDeliveryStrategy(ABC):
    """Стратегия для работы со статусами доставки посылок."""

    def __init__(self):
        """Инициализация стратегии."""
        self.transaction_service = TransactionProcessor()
        self.delivery_service = PackageDeliveryService()

    @abstractmethod
    def process_delivery(self, delivery) -> None:
        """
        Обработать доставку.

        Args:
            delivery: Объект доставки
        """
        pass

    def _validate_package_cost(self, delivery) -> None:
        """Проверка стоимости посылки."""
        if not delivery.package or delivery.package.total_cost_eur <= 0:
            raise ValidationError(
                {
                    "package": (
                        "Невозможно обработать доставку. "
                        "Сначала укажите стоимость доставки и комиссию в посылке."
                    )
                }
            )


class NewPackageDeliveryStrategy(PackageDeliveryStrategy):
    """Стратегия для обработки доставки в статусе new."""

    def process_delivery(self, delivery) -> None:
        """Обработать новую доставку."""
        print(f"Обработка новой доставки. ID: {delivery.id}, Статус: Новая")
        pass


class PaidPackageDeliveryStrategy(PackageDeliveryStrategy):
    """Стратегия для обработки доставки в статусе paid."""

    def process_delivery(self, delivery) -> None:
        """Обработать оплаченную доставку."""
        print("PaidPackageDeliveryStrategy: начало обработки")

        self._validate_package_cost(delivery)
        print(
            f"PaidPackageDeliveryStrategy: стоимость посылки: {delivery.package.total_cost_eur}"
        )

        # Рассчитать стоимость
        self.delivery_service.calculate_delivery_costs(delivery)
        print(
            f"PaidPackageDeliveryStrategy: рассчитанная стоимость: {delivery.shipping_cost_rub}"
        )

        # Обработать транзакцию
        delivery_data = self.delivery_service.serialize_delivery_data_for_transaction(
            delivery
        )
        print(f"PaidPackageDeliveryStrategy: данные для транзакции: {delivery_data}")

        if delivery_data:
            transaction = self.transaction_service.execute_transaction(delivery_data)
            print(f"PaidPackageDeliveryStrategy: транзакция создана: {transaction}")


class CancelledPackageDeliveryStrategy(PackageDeliveryStrategy):
    """Стратегия для обработки отмененной доставки."""

    def process_delivery(self, delivery) -> None:
        """Обработать отмененную доставку."""
        print("CancelledPackageDeliveryStrategy: начало обработки")

        # Сохраняем данные для транзакции до обнуления стоимости
        delivery_data = self.delivery_service.serialize_delivery_data_for_transaction(
            delivery
        )

        # Обнуляем стоимость доставки
        self.delivery_service.reset_delivery_costs(delivery)
        print(f"CancelledPackageDeliveryStrategy: стоимость обнулена")

        # Создаем транзакцию возврата используя сохраненные данные
        if delivery_data:
            transaction = self.transaction_service.execute_transaction(delivery_data)
            print(
                f"CancelledPackageDeliveryStrategy: транзакция создана: {transaction}"
            )


class ReexportPackageDeliveryStrategy(PackageDeliveryStrategy):
    """Стратегия для обработки доставки в статусе reexport."""

    def process_delivery(self, delivery) -> None:
        """Обработать переэкспортную доставку."""
        print(
            "Обработка переэкспортной доставки. "
            f"ID: {delivery.id}, Статус: Переэкспорт"
        )
        pass
