"""
Сервис для обработки заказов.

Этот модуль реализует обработку заказов с использованием паттерна "Стратегия".
Основная задача - выбор и применение соответствующей стратегии обработки
в зависимости от статуса заказа.

Основные компоненты:
    - OrderProcessor: Основной класс для обработки заказов
    - execute_status_strategy: Метод выполнения стратегии для текущего статуса

Процесс обработки:
    1. Получение заказа для обработки
    2. Определение текущего статуса заказа
    3. Выбор соответствующей стратегии обработки
    4. Применение выбранной стратегии

Стратегии обработки:
    - NewOrderStrategy: для новых заказов
    - PaidOrderStrategy: для оплаченных заказов
    - RefundedOrderStrategy: для возвращенных заказов

Примеры использования:
    processor = OrderProcessor()
    processor.execute_status_strategy(order)

Примечания:
    - Каждый статус заказа имеет свою стратегию обработки
    - Стратегии определяются в модуле order_strategies
    - При отсутствии стратегии для статуса возможна обработка по умолчанию
"""

from status.services.strategy_factory import OrderStatusStrategyFactory
from django.core.exceptions import ValidationError


class OrderProcessor:
    """
    Процессор для обработки заказов.

    Класс обеспечивает выбор и применение стратегий обработки заказов
    в зависимости от их текущего статуса.

    Attributes:
        strategy_factory: Фабрика для создания стратегий обработки

    Methods:
        execute_status_strategy: Выполняет стратегию обработки для текущего статуса заказа
    """

    def __init__(self):
        """Инициализация сервиса."""
        self.strategy_factory = OrderStatusStrategyFactory

    def execute_status_strategy(self, order, old_status=None) -> bool:
        """Выполнить стратегию обработки для текущего статуса заказа.

        Args:
            order: Заказ для обработки
            old_status: Предыдущий статус заказа, если был

        Returns:
            bool: True если обработка прошла успешно

        Raises:
            ValidationError: Если невозможно применить стратегию обработки
        """
        # Получаем стратегию для нового статуса
        strategy = self.strategy_factory.get_strategy(order.status)
        success = strategy.handle_order_status_config(order)

        if not success:
            # Если обработка не удалась, возвращаем старый статус
            if old_status:
                order.status = old_status
                order.save(skip_status_processing=True)
            raise ValidationError(
                {"order": "Не удалось обработать изменение статуса заказа"}
            )

        return success
