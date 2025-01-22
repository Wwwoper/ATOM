"""Сервис для массовых операций с заказами."""

from django.db import transaction
from django.core.exceptions import ValidationError

from .order_status_service import OrderStatusService


class OrderBulkService:
    """Сервис для массовых операций с заказами."""

    def __init__(self):
        """Инициализация сервиса."""
        self.status_service = OrderStatusService()

    def bulk_update_status(self, queryset, new_status, comment=None):
        """
        Массовое обновление статуса и комментария для заказов.

        Args:
            queryset: QuerySet заказов для обновления
            new_status: Новый статус
            comment: Опциональный комментарий

        Raises:
            ValidationError: Если хотя бы один заказ не может быть обновлен
        """
        with transaction.atomic():
            # Получаем все заказы для обновления
            orders = list(queryset.select_for_update())

            # Проверяем возможность обновления каждого заказа
            for order in orders:
                old_status = order.status
                order.status = new_status

                try:
                    # Проверяем возможность перехода через существующий сервис
                    self.status_service.process_status_change(order)
                except ValidationError as e:
                    raise ValidationError(
                        f"Невозможно изменить статус заказа {order.internal_number}: {str(e)}"
                    )

            # Если все проверки прошли, обновляем заказы
            updated_fields = ["status"]
            if comment is not None:
                updated_fields.append("comment")

            queryset.update(
                status=new_status, **({"comment": comment} if comment else {})
            )
