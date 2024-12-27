"""
Сервис для обработки доставок.

Этот модуль реализует обработку доставок с использованием паттерна "Стратегия".
Основная задача - выбор и применение соответствующей стратегии обработки
в зависимости от статуса доставки.

Основные компоненты:
    - DeliveryProcessor: Основной класс для обработки доставок
    - execute_status_strategy: Метод выполнения стратегии для текущего статуса

Процесс обработки:
    1. Получение доставки для обработки
    2. Определение текущего статуса доставки
    3. Выбор соответствующей стратегии обработки
    4. Применение выбранной стратегии

Стратегии обработки:
    - NewDeliveryStrategy: для новых доставок
    - PaidDeliveryStrategy: для оплаченных доставок
    - CanceledDeliveryStrategy: для отмененных доставок
    - RefundedDeliveryStrategy: для возвращенных доставок

Примеры использования:
    processor = DeliveryProcessor()
    processor.execute_status_strategy(delivery)

Примечания:
    - Каждый статус доставки имеет свою стратегию обработки
    - Стратегии определяются в модуле delivery_strategies
    - При отсутствии стратегии для статуса возможна обработка по умолчанию
    - Все операции с доставкой выполняются атомарно
"""

from status.services.strategy_factory import DeliveryStatusStrategyFactory


class DeliveryProcessor:
    """
    Процессор для обработки доставки.

    Класс обеспечивает выбор и применение стратегий обработки доставок
    в зависимости от их текущего статуса.

    Attributes:
        strategy_factory: Фабрика для создания стратегий обработки

    Methods:
        execute_status_strategy: Выполняет стратегию обработки для текущего статуса доставки
    """

    def __init__(self):
        """Инициализация сервиса."""
        self.strategy_factory = DeliveryStatusStrategyFactory

    def execute_status_strategy(self, delivery) -> None:
        """
        Выполнить стратегию обработки для текущего статуса доставки.

        Args:
            delivery: Доставка для обработки

        Raises:
            ValidationError: Если невозможно применить стратегию обработки
        """
        strategy = self.strategy_factory.get_strategy(delivery.status)
        strategy.process_delivery(delivery)
