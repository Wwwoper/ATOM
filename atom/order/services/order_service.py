"""Сервис для работы с расширенными методами обработки заказов."""

from decimal import Decimal

from django.utils import timezone


class OrderService:
    """Сервис для работы с заказами вне модели."""

    def calculate_expenses_and_profit(self, order) -> None:
        """Рассчитывает расходы и прибыль для заказа.

        Вычисляет расходы на основе цены в евро и среднего курса обмена.
        Вычисляет прибыль как разницу между ценой в рублях и расходами.
        Устанавливает дату оплаты, если она не задана.

        Args:
            order: Объект заказа для расчета
        """
        # Расчет расходов и прибыли
        two_places = Decimal("0.00")
        order.expense = (
            order.amount_euro * order.user.balance.average_exchange_rate
        ).quantize(two_places)
        order.profit = (order.amount_rub - order.expense).quantize(two_places)

        # Установка даты оплаты, если её еще нет
        if not order.paid_at:
            order.paid_at = timezone.now()

        # Сохраняем изменения, но пропускаем валидацию, так как она будет выполнена в модели
        order.save(
            update_fields=["expense", "profit", "paid_at"],
            skip_status_processing=True,
        )

    def calculate_amount_rub(self, order) -> Decimal:
        """Рассчитывает сумму в рублях на основе суммы в евро и среднего курса обмена.

        Args:
            order: Объект заказа

        Returns:
            Decimal: Сумма в рублях
        """
        return order.amount_euro * order.user.balance.average_exchange_rate

    def reset_profit_expense_paid_at(self, order) -> None:
        """Обнулить расчетные поля profit, expense, paid_at у заказа."""
        order.profit = Decimal("0.00")
        order.expense = Decimal("0.00")
        order.paid_at = None
        order.save(
            update_fields=["profit", "expense", "paid_at"],
            skip_status_processing=True,
        )

    def serialize_order_data_for_transaction(self, order) -> dict | None:
        """Подготовить данные заказа для транзакции.

        Args:
            order: Объект заказа

        Returns:
            dict | None: Словарь с данными для создания транзакции или None
        """
        transaction_type = order.status.group.get_transaction_type_by_status(
            order.status.code
        )
        if not transaction_type:
            return None

        return {
            "balance": order.user.balance,
            "transaction_type": transaction_type,
            "amount_euro": order.amount_euro,
            "amount_rub": self.calculate_amount_rub(order),
            "comment": f"Оплата заказа №{order.internal_number} на сайте {order.site.name}",
        }
