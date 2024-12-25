"""Сервис доставки посылок."""

from decimal import Decimal

from balance.services.constants import TransactionTypeChoices
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


class PackageDeliveryService:
    """
    Сервис для управления доставкой посылок.

    Основные функции:
    - Расчет стоимости доставки
    - Валидация данных доставки
    - Подготовка данных для транзакций
    - Управление статусом оплаты
    """

    def serialize_delivery_data_for_transaction(self, delivery) -> dict | None:
        """
        Подготовка данных для транзакции оплаты доставки.

        Args:
            delivery: Объект доставки

        Returns:
            dict: Данные для создания транзакции
            None: Если транзакция не требуется
        """
        self._validate_delivery(delivery)

        transaction_type = self._get_transaction_type(delivery)
        if not transaction_type:
            return None

        return self._prepare_transaction_data(delivery, transaction_type)

    @transaction.atomic
    def calculate_delivery_costs(self, delivery) -> None:
        """
        Расчет и сохранение стоимости доставки.

        Args:
            delivery: Объект доставки
        """
        self._validate_delivery_for_calculation(delivery)

        shipping_cost_rub = self._calculate_shipping_cost_rub(delivery)
        self._update_delivery_costs(delivery, shipping_cost_rub)

        if self._should_mark_as_paid(delivery):
            self._mark_delivery_paid(delivery)

        delivery.save(skip_status_processing=True)

    def reset_delivery_costs(self, delivery) -> None:
        """
        Сброс стоимости доставки в начальное состояние.

        Args:
            delivery: Объект доставки
        """
        delivery.shipping_cost_rub = Decimal("0.00")
        delivery.price_rub_for_kg = Decimal("0.00")
        delivery.paid_at = None
        delivery.save(skip_status_processing=True)

    # Private methods
    def _validate_delivery(self, delivery) -> None:
        """
        Валидация доставки д��я создания транзакции.

        Args:
            delivery: Объект доставки
        """
        if not delivery.package:
            raise ValidationError({"package": "Посылка не найдена"})

        if delivery.package.total_cost_eur <= 0:
            raise ValidationError(
                {"package": "Укажите стоимость доставки и комиссию в посылке"}
            )

        if delivery.shipping_cost_rub <= 0:
            self.calculate_delivery_costs(delivery)

    def _validate_delivery_for_calculation(self, delivery) -> None:
        """
        Валидация доставки для расчета стоимости доставки.

        Args:
            delivery: Объект доставки
        """
        if not delivery.package:
            raise ValidationError({"package": "Посылка обязательна для расчета"})

        if delivery.weight <= 0:
            raise ValidationError({"weight": "Вес должен быть больше нуля"})

        if delivery.package.total_cost_eur <= 0:
            raise ValidationError({"package": "Укажите стоимость посылки"})
        # Добавляем проверку курса обмена
        if not delivery.package.user.balance.average_exchange_rate:
            raise ValidationError({"package": "Не установлен курс обмена"})

        # Проверяем, что курс обмена положительный
        if delivery.package.user.balance.average_exchange_rate <= 0:
            raise ValidationError({"package": "Некорректный курс обмена"})

    def _calculate_shipping_cost_rub(self, delivery) -> Decimal:
        shipping_cost_rub = (
            delivery.package.total_cost_eur
            * delivery.package.user.balance.average_exchange_rate
        ).quantize(Decimal("0.01"))

        if shipping_cost_rub <= 0:
            raise ValidationError(
                {"shipping_cost_rub": "Некорректная стоимость доставки"}
            )

        return shipping_cost_rub

    def _get_transaction_type(self, delivery) -> str | None:
        return delivery.status.group.get_transaction_type_by_status(
            delivery.status.code
        )

    def _prepare_transaction_data(self, delivery, transaction_type: str) -> dict:
        """
        Подготовка данных для транзакции оплаты/возврата доставки.

        Args:
            delivery: Объект доставки
            transaction_type: Тип транзакции

        Returns:
            dict: Данные для создания транзакции
        """
        comment = (
            "Возврат за отмену доставки №{}"
            if transaction_type == TransactionTypeChoices.PAYBACK
            else "Оплата доставки №{}"
        )

        return {
            "balance": delivery.package.user.balance,
            "transaction_type": transaction_type,
            "amount_euro": delivery.package.total_cost_eur,
            "amount_rub": delivery.shipping_cost_rub,
            "comment": comment.format(delivery.package.number),
        }

    def _update_delivery_costs(self, delivery, shipping_cost_rub: Decimal) -> None:
        """
        Обновление стоимости доставки.

        Args:
            delivery: Объект доставки
            shipping_cost_rub: Стоимость доставки в рублях
        """
        delivery.shipping_cost_rub = shipping_cost_rub
        delivery.price_rub_for_kg = (shipping_cost_rub / delivery.weight).quantize(
            Decimal("0.01")
        )

    def _should_mark_as_paid(self, delivery) -> bool:
        """
        Проверка, должна ли доставка быть отмечена как оплаченная.

        Args:
            delivery: Объект доставки

        Returns:
            bool: True, если доставка должна быть отмечена как оплаченная
        """
        return not delivery.paid_at and delivery.status.code == "paid"

    def _mark_delivery_paid(self, delivery) -> None:
        """
        Отметка доставки как оплаченной.

        Args:
            delivery: Объект доставки
        """
        delivery.paid_at = timezone.now()
