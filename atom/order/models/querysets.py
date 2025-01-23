"""QuerySets для моделей orders."""

from django.db import models, transaction
from django.core.exceptions import ValidationError
from status.models import Status
from status.constants import OrderStatusCode, StatusGroupCode
import logging

logger = logging.getLogger(__name__)


class OrderQuerySet(models.QuerySet):
    """QuerySet для модели Order с поддержкой массовых операций."""

    def bulk_update_status(self, new_status, comment=None):
        """Массовое обновление статуса."""
        logger.info(
            "Запуск массового обновления статуса на '%s' для %d заказов",
            new_status.name,
            self.count(),
        )
        try:
            # Валидация входных данных
            self._validate_status(new_status)

            if not self.exists():
                return 0

            with transaction.atomic():
                orders = self._lock_orders_for_update()
                self._validate_orders_status_change(orders, new_status)
                updated_count = self._perform_status_update(new_status, comment)

            logger.info(
                "Массовое обновление завершено успешно: обновлено %d заказов",
                updated_count,
            )
            return updated_count
        except Exception as e:
            logger.error(
                "Ошибка при массовом обновлении статуса: %s",
                str(e),
                exc_info=True,
            )
            raise

    def _validate_status(self, new_status):
        """Валидация статуса."""
        if not new_status:
            error_msg = "Не указан новый статус"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not isinstance(new_status, Status):
            error_msg = "Некорректный тип статуса"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if new_status.group.code != StatusGroupCode.ORDER:
            error_msg = "Статус не принадлежит группе статусов заказа"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _lock_orders_for_update(self):
        """Блокировка заказов для обновления."""
        logger.debug("Блокировка заказов для обновления")
        return list(
            self.select_for_update()
            .select_related("status", "status__group")
            .order_by("id")
        )

    def _validate_orders_status_change(self, orders, new_status):
        """Валидация изменения статуса для всех заказов."""
        logger.debug("Проверка возможности изменения статуса для заказов")
        errors = []
        for order in orders:
            try:
                if order.status.code == OrderStatusCode.PAID:
                    error_msg = f"Заказ {order.internal_number} уже оплачен"
                    logger.warning(error_msg)
                    raise ValidationError(error_msg)

                if not order.status.group.is_transition_allowed(
                    order.status.code, new_status.code
                ):
                    error_msg = (
                        f"Недопустимый переход из '{order.status.name}' "
                        f"в '{new_status.name}' для заказа {order.internal_number}"
                    )
                    logger.warning(error_msg)
                    raise ValidationError(error_msg)
            except ValidationError as e:
                errors.append(str(e))

        if errors:
            error_msg = "Невозможно обновить статусы:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValidationError(error_msg)

    def _perform_status_update(self, new_status, comment):
        """Выполнение обновления статуса."""
        logger.debug("Выполнение обновления статусов")
        update_fields = {"status": new_status}
        if comment is not None:
            update_fields["comment"] = comment
        return self.update(**update_fields)
