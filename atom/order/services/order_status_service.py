"""Сервис для управления статусами заказов."""

from typing import TYPE_CHECKING

from django.forms import ValidationError
from status.models import Status
from status.services.constants import get_default_status

from .order_processor_service import OrderProcessor

if TYPE_CHECKING:
    from order.models import Order


class OrderStatusService:
    """Сервис для работы со статусами заказов."""

    def __init__(self):
        """Инициализация сервиса."""
        self.order_processor = OrderProcessor()

    def process_status_change(
        self, order: "Order", skip_status_processing: bool = False
    ) -> bool:
        """
        Обработка изменения статуса у заказа.

        Args:
            order: Объект заказа
            skip_status_processing: Флаг пропуска обработки статуса

        Returns:
            bool: Был ли изменен статус
        """
        status_changed = self._check_status_change(order)

        if status_changed and not skip_status_processing:
            self.order_processor.execute_status_strategy(order)

        return status_changed

    def _check_status_change(self, order: "Order") -> bool:
        """Проверка на изменение статуса."""
        # Для нового заказа без статуса
        if not order.pk:
            return False if order.status_id else self._set_initial_status(order)

        # Получаем старый заказ только если он существует
        old_order = order.__class__.objects.filter(pk=order.pk).only("status").first()
        if not old_order:
            return False

        # Проверяем изменение статуса
        if old_order.status != order.status:
            self._validate_status_change(old_order, order.status.code)
            return True

        return False

    def _set_initial_status(self, order: "Order") -> bool:
        """Установка начального статуса для нового заказа."""
        default_status_code = get_default_status(
            order.__class__, group_code="order_status"
        )
        if not default_status_code:
            raise ValidationError("Невозможно создать заказ без статуса по умолчанию")

        order.status = Status.objects.get(
            code=default_status_code, group__code="order_status"
        )
        return True

    def _validate_status_change(self, order: "Order", new_status_code: str) -> None:
        """Валидация возможности перехода заказа в новый статус.

        Args:
            order: Заказ
            new_status_code: Код нового статуса
        Raises:
            ValidationError: Если переход в новый статус недопустим
        """
        current_status = order.status

        # Проверяем возможность перехода
        if not current_status.group.is_transition_allowed(
            current_status.code, new_status_code
        ):
            raise ValidationError(
                f"Переход из статуса '{current_status.code}' "
                f"в '{new_status_code}' недопустим"
            )
