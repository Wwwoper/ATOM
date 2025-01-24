"""Сервис для обработки операций с балансом."""

from decimal import Decimal
from django.db import transaction as db_transaction
from balance.services.constants import TransactionTypeChoices


class BalanceProcessor:
    """Процессор для обработки операций с балансом."""

    @staticmethod
    def update_balance(transaction) -> None:
        """
        Обновляет баланс на основе транзакции.

        Args:
            transaction: Транзакция для обработки
        """
        with db_transaction.atomic():
            balance = transaction.balance

            if transaction.transaction_type == TransactionTypeChoices.EXPENSE:
                balance.balance_euro -= transaction.amount_euro
                balance.balance_rub -= transaction.amount_rub
            elif transaction.transaction_type in (
                TransactionTypeChoices.REPLENISHMENT,
                TransactionTypeChoices.PAYBACK,
            ):
                balance.balance_euro += transaction.amount_euro
                balance.balance_rub += transaction.amount_rub

            balance.save(allow_balance_update=True)
