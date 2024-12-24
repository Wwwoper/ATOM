"""
Сервис для работы с историей баланса.

Этот модуль предоставляет функциональность для:
- Создания записей в истории баланса
- Получения истории операций
- Анализа изменений баланса
"""

from datetime import datetime
from typing import Optional

from django.db.models import QuerySet


class BalanceHistoryService:
    """
    Сервис для работы с историей баланса.

    Отвечает за:
    - Создание записей истории баланса
    - Получение истории операций
    - Анализ изменений баланса
    """

    @staticmethod
    def create_balance_history_record(transaction) -> "BalanceHistoryRecord":
        """
        Создает запись в истории баланса на основе транзакции.

        Args:
            transaction: Объект транзакции

        Returns:
            BalanceHistoryRecord: Созданная запись истории
        """
        from ..models import BalanceHistoryRecord

        return BalanceHistoryRecord.objects.create(
            balance=transaction.balance,
            transaction_type=transaction.transaction_type,
            amount_euro=transaction.amount_euro,
            amount_rub=transaction.amount_rub,
            amount_euro_after=transaction.balance.balance_euro,
            amount_rub_after=transaction.balance.balance_rub,
            transaction_date=transaction.transaction_date,
            comment=transaction.comment,
        )

    @staticmethod
    def get_balance_history(
        balance_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> QuerySet:
        """
        Получает историю операций по балансу за период.

        Args:
            balance_id: ID баланса
            start_date: Начальная дата периода
            end_date: Конечная дата периода

        Returns:
            QuerySet: Записи истории за указанный период
        """
        from ..models import BalanceHistoryRecord

        query = BalanceHistoryRecord.objects.filter(balance_id=balance_id)

        if start_date:
            query = query.filter(transaction_date__gte=start_date)
        if end_date:
            query = query.filter(transaction_date__lte=end_date)

        return query.order_by("-transaction_date")

    @staticmethod
    def get_last_balance_record(balance_id: int) -> Optional["BalanceHistoryRecord"]:
        """
        Получает последнюю запись истории для указанного баланса.

        Args:
            balance_id: ID баланса

        Returns:
            Optional[BalanceHistoryRecord]: Последняя запись истории или None
        """
        from ..models import BalanceHistoryRecord

        return (
            BalanceHistoryRecord.objects.filter(balance_id=balance_id)
            .order_by("-transaction_date")
            .first()
        )

    @staticmethod
    def get_balance_changes_summary(
        balance_id: int, start_date: datetime, end_date: datetime
    ) -> dict:
        """
        Получает сводку изменений баланса за период.

        Args:
            balance_id: ID баланса
            start_date: Начальная дата периода
            end_date: Конечная дата периода

        Returns:
            dict: Сводка изменений с суммами операций
        """
        from django.db.models import Sum

        from ..models import BalanceHistoryRecord

        records = BalanceHistoryRecord.objects.filter(
            balance_id=balance_id, transaction_date__range=(start_date, end_date)
        )

        return {
            "total_euro": records.aggregate(Sum("amount_euro"))["amount_euro__sum"]
            or 0,
            "total_rub": records.aggregate(Sum("amount_rub"))["amount_rub__sum"] or 0,
            "transactions_count": records.count(),
        }
