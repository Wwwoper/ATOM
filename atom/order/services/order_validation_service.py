"""Сервис валидации заказов."""

from decimal import Decimal
from django.core.exceptions import ValidationError
from status.constants import OrderStatusCode


class OrderValidationService:
    """Сервис для валидации заказов."""

    @staticmethod
    def validate_amounts(amount_euro: Decimal, amount_rub: Decimal) -> None:
        """Валидация сумм заказа."""
        errors = {}

        if amount_euro <= 0:
            errors["amount_euro"] = "Цена в евро должна быть больше 0"
        if amount_rub <= 0:
            errors["amount_rub"] = "Цена в рублях должна быть больше 0"

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def validate_user_immutability(old_user_id: int, new_user_id: int) -> None:
        """Валидация неизменности пользователя."""
        if old_user_id != new_user_id:
            raise ValidationError(
                "Невозможно изменить пользователя после создания заказа"
            )

    @staticmethod
    def validate_paid_order_amounts(order, old_instance) -> tuple[Decimal, Decimal]:
        """Валидация сумм оплаченного заказа."""
        if old_instance.status.code == OrderStatusCode.PAID:
            if (
                order.amount_euro != old_instance.amount_euro
                or order.amount_rub != old_instance.amount_rub
            ):
                return old_instance.amount_euro, old_instance.amount_rub
        return order.amount_euro, order.amount_rub

    @staticmethod
    def validate_internal_number(
        internal_number: str, order_id: int | None = None
    ) -> None:
        """Валидация уникальности внутреннего номера."""
        from order.models import Order

        qs = Order.objects.filter(internal_number=internal_number)
        if order_id:
            qs = qs.exclude(id=order_id)
        if qs.exists():
            raise ValidationError(
                {"internal_number": "Заказ с таким внутренним номером уже существует"}
            )
