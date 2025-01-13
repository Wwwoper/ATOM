from ninja import Field, Schema
from decimal import Decimal
from typing import Optional
from datetime import datetime


class BalanceOut(Schema):
    """Схема ответа с информацией о балансе"""

    balance_euro: Decimal = Field(..., description="Баланс в евро")
    balance_rub: Decimal = Field(..., description="Баланс в рублях")
    average_exchange_rate: Decimal = Field(..., description="Средний курс обмена")


class TransactionCreate(Schema):
    """Схема для создания транзакции"""

    transaction_type: str = Field(
        ...,
        description="Тип транзакции: replenishment (пополнение), expense (расход), payback (возврат)",
    )
    amount_euro: Decimal = Field(..., description="Сумма в евро", gt=0)
    amount_rub: Decimal = Field(..., description="Сумма в рублях", gt=0)
    comment: Optional[str] = Field(None, description="Комментарий к транзакции")


class TransactionOut(Schema):
    """Схема ответа с информацией о транзакции"""

    id: int = Field(..., description="ID транзакции")
    transaction_type: str = Field(..., description="Тип транзакции")
    amount_euro: Decimal = Field(..., description="Сумма в евро")
    amount_rub: Decimal = Field(..., description="Сумма в рублях")
    transaction_date: datetime = Field(..., description="Дата и время транзакции")
    comment: Optional[str] = Field(None, description="Комментарий к транзакции")
