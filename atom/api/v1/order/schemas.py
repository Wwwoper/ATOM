from decimal import Decimal
from typing import Optional
from ninja import ModelSchema, Schema, Field
from order.models import Order, Site


class SiteOut(ModelSchema):
    """Схема для отображения данных сайта."""

    id: int = Field(..., description="ID сайта")
    name: str = Field(..., description="Название сайта")
    url: str = Field(..., description="URL сайта")
    organizer_fee_percentage: Decimal = Field(
        ..., description="Комиссия организатора в процентах"
    )
    total_orders: int = Field(..., description="Общее количество заказов")
    total_profit: Decimal = Field(
        ..., description="Общая прибыль от оплаченных заказов"
    )

    class Config:
        model = Site
        model_fields = ["id", "name", "url", "organizer_fee_percentage"]


class OrderOut(ModelSchema):
    """Схема для отображения данных заказа."""

    id: int = Field(..., description="ID заказа")
    internal_number: str = Field(..., description="Внутренний номер заказа")
    external_number: Optional[str] = Field(None, description="Внешний номер заказа")
    amount_euro: Decimal = Field(..., description="Сумма в евро")
    amount_rub: Decimal = Field(..., description="Сумма в рублях")
    status: str = Field(..., description="Статус заказа")
    profit: Decimal = Field(..., description="Прибыль")
    expense: Decimal = Field(..., description="Расходы")
    created_at: str = Field(..., description="Дата создания")
    paid_at: Optional[str] = Field(None, description="Дата оплаты")
    comment: Optional[str] = Field(None, description="Комментарий к заказу")
    site: SiteOut = Field(..., description="Сайт заказа")

    class Config:
        model = Order
        model_fields = [
            "id",
            "internal_number",
            "external_number",
            "amount_euro",
            "amount_rub",
            "status",
            "profit",
            "expense",
            "created_at",
            "paid_at",
            "comment",
            "site",
        ]


class OrderCreate(Schema):
    """Схема для создания заказа."""

    site_id: int = Field(..., description="ID сайта")
    external_number: Optional[str] = Field(None, description="Внешний номер заказа")
    amount_euro: Decimal = Field(..., gt=0, description="Сумма в евро")
    amount_rub: Decimal = Field(..., gt=0, description="Сумма в рублях")
    comment: Optional[str] = Field(None, description="Комментарий к заказу")


class OrderUpdate(Schema):
    """Схема для обновления заказа."""

    external_number: Optional[str] = Field(None, description="Внешний номер заказа")
    status: Optional[str] = Field(None, description="Код статуса заказа")
    comment: Optional[str] = Field(None, description="Комментарий к заказу")


class SiteCreate(Schema):
    """Схема для создания сайта."""

    name: str = Field(..., description="Название сайта")
    url: str = Field(..., description="URL сайта")
    organizer_fee_percentage: Decimal = Field(
        ..., gt=0, lt=100, description="Комиссия организатора в процентах"
    )
    description: Optional[str] = Field(None, description="Описание сайта")


class SiteUpdate(Schema):
    """Схема для обновления сайта."""

    name: Optional[str] = Field(None, description="Название сайта")
    url: Optional[str] = Field(None, description="URL сайта")
    organizer_fee_percentage: Optional[Decimal] = Field(
        None, gt=0, lt=100, description="Комиссия организатора в процентах"
    )
    description: Optional[str] = Field(None, description="Описание сайта")
