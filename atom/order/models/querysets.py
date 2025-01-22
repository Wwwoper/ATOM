"""QuerySets для моделей orders."""

from django.db import models, transaction
from django.core.exceptions import ValidationError
from status.models import Status
from status.constants import OrderStatusCode, StatusGroupCode


class OrderQuerySet(models.QuerySet):
    """QuerySet для модели Order с поддержкой массовых операций."""

    def bulk_update_status(self, new_status, comment=None):
        """Массовое обновление статуса."""
        # Валидация входных данных
        self._validate_status(new_status)

        if not self.exists():
            return 0

        with transaction.atomic():
            orders = self._lock_orders_for_update()
            self._validate_orders_status_change(orders, new_status)
            return self._perform_status_update(new_status, comment)

    def _validate_status(self, new_status):
        """Валидация статуса."""
        if not new_status:
            raise ValueError("Не указан новый статус")
        if not isinstance(new_status, Status):
            raise ValueError("Некорректный тип статуса")
        if new_status.group.code != StatusGroupCode.ORDER:
            raise ValueError("Статус не принадлежит группе статусов заказа")

    def _lock_orders_for_update(self):
        """Блокировка заказов для обновления."""
        return list(
            self.select_for_update()
            .select_related("status", "status__group")
            .order_by("id")
        )

    def _validate_orders_status_change(self, orders, new_status):
        """Валидация изменения статуса для всех заказов."""
        errors = []
        for order in orders:
            try:
                if order.status.code == OrderStatusCode.PAID:
                    raise ValidationError(f"Заказ {order.internal_number} уже оплачен")
                if not order.status.group.is_transition_allowed(
                    order.status.code, new_status.code
                ):
                    raise ValidationError(
                        f"Недопустимый переход из '{order.status.name}' "
                        f"в '{new_status.name}' для заказа {order.internal_number}"
                    )
            except ValidationError as e:
                errors.append(str(e))

        if errors:
            raise ValidationError("Невозможно обновить статусы:\n" + "\n".join(errors))

    def _perform_status_update(self, new_status, comment):
        """Выполнение обновления статуса."""
        update_fields = {"status": new_status}
        if comment is not None:
            update_fields["comment"] = comment
        return self.update(**update_fields)
