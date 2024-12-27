"""Сервис для работы с расширенными методами обработки заказов."""

from decimal import Decimal
from django.core.exceptions import ValidationError


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

        # Сохраняем изменения, но пропускаем валидацию, так как она будет выполнена в модели
        order.save(
            update_fields=["expense", "profit"],
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

    def validate_transaction_data(self, order) -> None:
        """
        Валидация данных заказа перед создание�� транзакции.

        Args:
            order: Объект заказа

        Raises:
            ValidationError: Если данные не прошли валидацию
        """
        if not order.amount_euro or not order.amount_rub:
            raise ValidationError({"order": "Не указаны суммы для транзакции"})

        if order.amount_euro <= 0 or order.amount_rub <= 0:
            raise ValidationError(
                {"order": "Суммы транзакции должны быть положительными"}
            )

        if not order.user.balance:
            raise ValidationError({"order": "У пользователя не создан баланс"})

    def validate_serialized_transaction_data(self, data: dict) -> None:
        """
        Валидация сериализованных данных для транзакции.

        Args:
            data: Словарь с данными для транзакции

        Raises:
            ValidationError: Если данные не прошли валидацию
        """
        if not data:
            raise ValidationError({"order": "Невозможно создать транзакцию для заказа"})

        # Проверяем обязательные поля
        required_fields = ["balance", "transaction_type", "amount_euro", "amount_rub"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(
                    {"order": f"Отсутствует обязательное поле {field}"}
                )

        # Проверяем суммы
        if data["amount_euro"] <= 0 or data["amount_rub"] <= 0:
            raise ValidationError(
                {"order": "Суммы транзакции должны быть положительными"}
            )

    def serialize_order_data_for_transaction(self, order) -> dict | None:
        """Подготовить данные заказа для транзакции.

        Args:
            order: Объект заказа

        Returns:
            dict | None: Словарь с данными для создания транзакции или None
        """
        # Валидация данных заказа
        self.validate_transaction_data(order)

        transaction_type = order.status.group.get_transaction_type_by_status(
            order.status.code
        )
        if not transaction_type:
            return None

        data = {
            "balance": order.user.balance,
            "transaction_type": transaction_type,
            "amount_euro": order.amount_euro,
            "amount_rub": self.calculate_amount_rub(order),
            "comment": f"Оплата заказа №{order.internal_number} на сайте {order.site.name}",
        }

        # Валидация сериализованных данных
        self.validate_serialized_transaction_data(data)

        return data
