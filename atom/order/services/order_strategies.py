"""Стратегии для работы с заказами."""

from abc import ABC, abstractmethod

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
        print(f"Обработка оплаченного заказа {order.id}")
        # Рассчитать расходы и прибыль
        self.order_service.calculate_expenses_and_profit(order)

        # Сериализовать данные заказа для транзакции
        order_data = self.order_service.serialize_order_data_for_transaction(order)

        # Обработать транзакцию
        return self.transaction_service.execute_transaction(order_data)


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
