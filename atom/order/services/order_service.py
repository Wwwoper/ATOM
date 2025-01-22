"""Сервис для работы с расширенными методами обработки заказов."""

from decimal import Decimal
from django.core.exceptions import ValidationError
from order.models import Order


class OrderService:
    """Сервис для работы с заказами вне модели."""

    def calculate_expenses_and_profit(self, order) -> None:
        """Рассчитывает расходы и прибыль для заказа.

        Расходы вычисляются на основе суммы в евро и среднего курса обмена из баланса пользователя.
        Прибыль вычисляется как разница между фактической суммой в рублях и расходами.

        Args:
            order: Объект заказа

        Note:
            Дата оплаты (paid_at) устанавливается отдельно при смене статуса
            заказа на "оплачен" через соответствующую стратегию.
        """
        # Обновляем объект заказа из базы для получения актуальных данных
        order.refresh_from_db()

        # Получаем актуальный баланс пользователя
        user_balance = order.user.balance
        user_balance.refresh_from_db()

        # Расчет расходов и прибыли с округлением до 2 знаков
        two_places = Decimal("0.00")

        # Расходы считаем по среднему курсу из баланса
        expense = (order.amount_euro * user_balance.average_exchange_rate).quantize(
            two_places
        )

        # Прибыль - разница между фактической суммой в рублях и расходами
        profit = (order.amount_rub - expense).quantize(two_places)

        print(f"DEBUG: amount_euro={order.amount_euro}")
        print(f"DEBUG: exchange_rate={user_balance.average_exchange_rate}")
        print(f"DEBUG: amount_rub={order.amount_rub}")  # Используем существующую сумму
        print(f"DEBUG: expense={expense}")
        print(f"DEBUG: profit={profit}")

        # Сохраняем все изменения атомарно
        Order.objects.filter(pk=order.pk).update(
            expense=expense,
            profit=profit,
        )
        order.refresh_from_db()

    def calculate_amount_rub(self, order) -> Decimal:
        """Рассчитывает сумму в рублях на основе суммы в евро и среднего курса обмена.

        Args:
            order: Объект заказа

        Returns:
            Decimal: Сумма в рублях
        """
        # Получаем актуальный баланс пользователя
        user_balance = order.user.balance
        user_balance.refresh_from_db()

        # Расчет с округлением до 2 знаков
        two_places = Decimal("0.00")
        return (order.amount_euro * user_balance.average_exchange_rate).quantize(
            two_places
        )

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
        Валидация данных заказа перед созданием транзакции.

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
            "amount_rub": order.amount_rub,  # Используем фактическую сумму из заказа
            "comment": f"Оплата заказа №{order.internal_number} на сайте {order.site.name}",
        }

        # Валидация сериализованных данных
        self.validate_serialized_transaction_data(data)

        return data

    def set_calculated_fields(
        self, order, expense: Decimal, profit: Decimal, paid_at=None
    ) -> None:
        """Установка расчетных полей заказа.

        Args:
            order: Объект заказа
            expense: Расходы по заказу
            profit: Прибыль по заказу
            paid_at: Дата и время оплаты заказа
        """
        update_fields = {"expense": expense, "profit": profit}
        if paid_at is not None:
            update_fields["paid_at"] = paid_at

        # Используем update для атомарного обновления полей
        Order.objects.filter(pk=order.pk).update(**update_fields)
        order.refresh_from_db()
