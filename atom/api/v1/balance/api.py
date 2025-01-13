from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from balance.services.transaction_service import TransactionProcessor
from .schemas import BalanceOut, TransactionCreate, TransactionOut
from ..auth.api import auth

router = Router(tags=["balance"])


@router.get(
    "/me",
    response=BalanceOut,
    auth=auth,
    summary="Получить баланс",
    description="Возвращает текущий баланс пользователя в евро и рублях",
)
def get_balance(request):
    """Получить баланс текущего пользователя"""
    return request.auth.balance


@router.post(
    "/transaction",
    response=TransactionOut,
    auth=auth,
    summary="Создать транзакцию",
    description="""
    Создает новую транзакцию.
    
    Типы транзакций:
    * replenishment - пополнение
    * expense - расход
    * payback - возврат
    
    Суммы указываются в евро и рублях.
    """,
)
def create_transaction(request, transaction_data: TransactionCreate):
    """Создать новую транзакцию"""
    try:
        transaction = TransactionProcessor.execute_transaction(
            {
                "balance": request.auth.balance,
                "transaction_type": transaction_data.transaction_type,
                "amount_euro": transaction_data.amount_euro,
                "amount_rub": transaction_data.amount_rub,
                "comment": transaction_data.comment,
            }
        )
        return transaction
    except ValidationError as e:
        raise ValidationError(str(e))


@router.get(
    "/transactions",
    response=List[TransactionOut],
    auth=auth,
    summary="Список транзакций",
    description="Возвращает список всех транзакций текущего пользователя",
)
def get_transactions(request):
    """Получить список транзакций текущего пользователя"""
    return request.auth.balance.transactions.all().order_by("-transaction_date")
