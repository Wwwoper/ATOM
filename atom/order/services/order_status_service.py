"""
Сервис для управления статусами заказов.

Этот модуль предоставляет функциональность для управления жизненным циклом заказов
через изменение их статусов. Реализует бизнес-логику переходов между статусами
и обеспечивает валидацию этих переходов.

Основные компоненты:
    - OrderStatusService: Основной класс для работы со статусами заказов
    - process_status_change: Обработка изменения статуса заказа
    - _check_status_change: Проверка возможности изменения статуса
    - _set_initial_status: Установка начального статуса для нового заказа
    - _validate_status_change: Валидация возможности перехода между статусами

Процесс изменения статуса:
    1. Проверка текущего состояния заказа
    2. Валидация возможности перехода в новый статус
    3. Применение изменений с использованием соответствующей стратегии
    4. Обновление связанных данных заказа

Правила переходов:
    - Новый заказ получает статус по умолчанию
    - Переходы между статусами строго регламентированы
    - Некоторые переходы могут требовать дополнительных проверок
    - Запрещены циклические переходы между статусами

Примеры использования:
    service = OrderStatusService()

    # Обработка изменения статуса
    service.process_status_change(order)

    # Установка начального статуса
    service._set_initial_status(new_order)

Примечания:
    - Все изменения статусов логируются
    - Недопустимые переходы вызывают ValidationError
    - Сервис интегрирован с системой стратегий обработки заказов
    - Поддерживается асинхронная обработка изменений статусов
"""

from typing import TYPE_CHECKING

from django.forms import ValidationError
from status.models import Status
from status.services.constants import get_default_status

from .order_processor_service import OrderProcessor

if TYPE_CHECKING:
    from order.models import Order


class OrderStatusService:
    """
    Сервис для работы со статусами заказов.

    Этот класс предоставляет методы для управления жизненным циклом заказов через
    их статусы. Включает валидацию переходов между статусами, установку начальных
    статусов и обработку изменений статуса.

    Attributes:
        order_processor: Процессор для обработки заказов

    Методы:
        process_status_change: Обработка изменения статуса заказа
        _check_status_change: Проверка возможности изменения статуса
        _set_initial_status: Установка начального статуса для нового заказа
        _validate_status_change: Валидация возможности перехода между статусами

    Примеры:
        service = OrderStatusService()
        # Обработка изменения статуса
        service.process_status_change(order)
    """

    def __init__(self):
        """Инициализация сервиса."""
        self.order_processor = OrderProcessor()

    def process_status_change(
        self, order: "Order", skip_status_processing: bool = False
    ) -> bool:
        """
        Обработка изменения статуса у заказа.

        Проверяет возможность изменения статуса и, если необходимо,
        запускает соответствующую стратегию обработки.

        Args:
            order: Объект заказа для обработки
            skip_status_processing: Флаг пропуска обработки статуса

        Returns:
            bool: True если статус был изменен, False в противном случае

        Raises:
            ValidationError: Если изменение статуса невозможно
        """
        status_changed = self._check_status_change(order)

        if status_changed and not skip_status_processing:
            # Получаем старый заказ для сохранения статуса
            old_order = (
                order.__class__.objects.filter(pk=order.pk).only("status").first()
            )
            old_status = old_order.status if old_order else None

            success = self.order_processor.execute_status_strategy(order, old_status)
            if not success:
                raise ValidationError(
                    {"order": "Не удалось обработать изменение статуса заказа"}
                )

        return status_changed

    def _check_status_change(self, order: "Order") -> bool:
        """
        Проверка на изменение статуса.

        Проверяет, был ли изменен статус заказа и возможен ли такой переход.
        Для новых заказов устанавливает начальный статус.

        Args:
            order: Объект заказа для проверки

        Returns:
            bool: True если статус изменен или установлен, False в противном случае

        Raises:
            ValidationError: При невозможности установки или изменения статуса
        """
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
            # Нужно сохранить новый статус
            order.__class__.objects.filter(pk=order.pk).update(status=order.status)
            return True

        return False

    def _set_initial_status(self, order: "Order") -> bool:
        """
        Установка начального статуса для нового заказа.

        Получает и устанавливает статус по умолчанию для нового заказа.

        Args:
            order: Новый заказ без статуса

        Returns:
            bool: True после успешной установки статуса

        Raises:
            ValidationError: Если невозможно получить статус по умолчанию
        """
        default_status_code = get_default_status(
            order.__class__, group_code="ORDER_STATUS_CONFIG"
        )
        if not default_status_code:
            raise ValidationError("Невозможно создать заказ без статуса по умолчанию")

        order.status = Status.objects.get(
            code=default_status_code, group__code="ORDER_STATUS_CONFIG"
        )
        return True

    def _validate_status_change(self, order: "Order", new_status_code: str) -> None:
        """
        Валидация возможности перехода заказа в новый статус.

        Проверяет допустимость перехода между статусами согласно
        настроенным правилам переходов.

        Args:
            order: Заказ для проверки
            new_status_code: Код нового статуса

        Raises:
            ValidationError: Если переход между статусами недопустим
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
