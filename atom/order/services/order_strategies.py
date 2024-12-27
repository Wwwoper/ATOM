"""
Модуль содержит стратегии обработки заказов в разных статусах.

Этот модуль реализует паттерн "Стратегия" для обработки заказов в различных состояниях.
Каждая стратегия инкапсулирует специфическую логику обработки заказа в определенном статусе.

Основные компоненты:
    - OrderStrategy: Определяет общий интерфейс для всех конкретных стратегий
    - NewOrderStrategy: Обработка заказа в статусе "new"
    - PaidOrderStrategy: Обработка заказа в статусе "paid", включая финансовые операции
    - RefundedOrderStrategy: Обработка возврата заказа и связанных финансовых операций

Процесс обработки:
    1. Выбор соответствующей стратегии на основе статуса заказа
    2. Валидация возможности выполнения операции
    3. Выполнение специфичных для статуса действий
    4. Обновление состояния заказа и связанных объектов

Финансовые операции:
    - Расчет стоимости и комиссий
    - Проведение транзакций через TransactionProcessor
    - Обновление баланса пользователя
    - Фиксация времени оплаты/возврата

Примеры использования:
    # Обработка оплаты заказа
    strategy = PaidOrderStrategy()
    strategy.handle_order_status(order)

    # Обработка возврата
    strategy = RefundedOrderStrategy()
    strategy.handle_order_status(order)

Примечания:
    - Все финансовые операции выполняются атомарно
    - Каждая стратегия содержит собственную валидацию
    - При ошибках выбрасывается ValidationError
"""

from abc import ABC, abstractmethod
from django.utils import timezone
from django.core.exceptions import ValidationError

from balance.services.transaction_service import TransactionProcessor
from order.services.order_service import OrderService


class OrderStrategy(ABC):
    """Стратегия для работы с заказами."""

    @abstractmethod
    def handle_order_status(self, order) -> None:
        """Обработать заказ согласно стратегии."""
        pass


class NewOrderStrategy(OrderStrategy):
    """Стратегия для обработки нового заказа."""

    def handle_order_status(self, order) -> None:
        """Обработать новый заказ."""
        print(f"Обработка нового заказа {order.id}")
        pass


class PaidOrderStrategy(OrderStrategy):
    """Стратегия для обработки оплаченного заказа."""

    def __init__(self):
        """Инициализация стратегии."""
        self.transaction_service = TransactionProcessor()
        self.order_service = OrderService()

    def handle_order_status(self, order) -> None:
        """Обработать оплаченный заказ."""
        # Проверка на повторную оплату
        if order.paid_at:
            raise ValidationError({"order": "Заказ уже оплачен"})

        # Рассчитать расходы и прибыль
        self.order_service.calculate_expenses_and_profit(order)

        # Сериализовать данные заказа для транзакции
        order_data = self.order_service.serialize_order_data_for_transaction(order)

        # Обработать транзакцию
        transaction = self.transaction_service.execute_transaction(order_data)

        # После успешной транзакции устанавливаем дату оплаты
        if transaction:
            order.paid_at = timezone.now()
            # Используем update для обновления поля без вызова save()
            type(order).objects.filter(pk=order.pk).update(paid_at=order.paid_at)

        return transaction


class RefundedOrderStrategy(OrderStrategy):
    """Стратегия для обработки возвращенного заказа."""

    def __init__(self):
        """Инициализация стратегии."""
        self.transaction_service = TransactionProcessor()
        self.order_service = OrderService()

    def handle_order_status(self, order):
        """Обработать возвращенный заказ."""
        print(f"Обработка возвращенного заказа {order.id}")
        # # Обнулить расчетные поля profit, expense, paid_at у заказа
        self.order_service.reset_profit_expense_paid_at(order)
        # # Подготовить данные заказа для транзакции
        order_data = self.order_service.serialize_order_data_for_transaction(order)

        return self.transaction_service.execute_transaction(order_data)
