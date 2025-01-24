"""
Сигналы для приложения balance.

Этот модуль содержит сигналы для автоматического создания и управления балансами пользователей.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from balance.models import Balance, Transaction, BalanceHistoryRecord
from balance.services.balance_processor import BalanceProcessor

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_balance(sender, instance, created, **kwargs):
    """
    Создает баланс для нового пользователя.

    Args:
        sender: Модель, отправившая сигнал (User)
        instance: Экземпляр пользователя
        created: Флаг, указывающий что запись создана
        **kwargs: Дополнительные аргументы
    """
    if created:
        Balance.objects.create(user=instance)


@receiver(post_save, sender=Transaction)
def create_transaction_history(sender, instance, created, **kwargs):
    """
    Создает запись в истории при создании транзакции.

    Args:
        sender: Модель, отправившая сигнал (Transaction)
        instance: Экземпляр транзакции
        created: Флаг, указывающий что запись создана
        **kwargs: Дополнительные аргументы
    """
    if created:
        # Обновляем баланс перед созданием истории
        BalanceProcessor.update_balance(instance)

        # Создаем запись в истории с актуальным балансом
        BalanceHistoryRecord.objects.create(
            balance=instance.balance,
            transaction_type=instance.transaction_type,
            amount_euro=instance.amount_euro,
            amount_rub=instance.amount_rub,
            amount_euro_after=instance.balance.balance_euro,
            amount_rub_after=instance.balance.balance_rub,
            comment=instance.comment,
        )
