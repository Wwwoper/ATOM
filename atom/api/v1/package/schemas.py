"""Схемы для сериализации данных пакета."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PackageBase(BaseModel):
    """Базовая схема для посылки."""

    number: str = Field(..., description="Номер посылки в сервисе у посредника")
    shipping_cost_eur: Decimal = Field(..., description="Стоимость отправки в евро")
    fee_cost_eur: Decimal = Field(..., description="Комиссия организатора")
    comment: Optional[str] = Field(None, description="Комментарий к посылке")

    @field_validator("shipping_cost_eur", "fee_cost_eur")
    @classmethod
    def validate_costs(cls, v):
        """Валидация стоимости."""
        if v < 0:
            raise ValueError("Стоимость не может быть отрицательной")
        return v


class PackageCreate(PackageBase):
    """Схема для создания посылки."""

    pass


class PackageUpdate(BaseModel):
    """Схема для обновления посылки."""

    shipping_cost_eur: Optional[Decimal] = Field(
        None, description="Стоимость отправки в евро"
    )
    fee_cost_eur: Optional[Decimal] = Field(None, description="Комиссия организатора")
    comment: Optional[str] = Field(None, description="Комментарий к посылке")


class PackageResponse(PackageBase):
    """Схема для ответа с данными посылки."""

    id: int
    total_cost_eur: Decimal = Field(..., description="Общая стоимость в евро")
    orders_count: int = Field(..., description="Количество заказов")

    class Config:
        """Конфигурация схемы."""

        from_attributes = True


class PackageDeliveryBase(BaseModel):
    """Базовая схема для доставки посылки."""

    tracking_number: str = Field(..., description="Трек номер для отслеживания")
    weight: Decimal = Field(..., description="Общий вес в кг")
    shipping_cost_rub: Decimal = Field(..., description="Стоимость доставки в рублях")
    delivery_address: Optional[str] = Field(None, description="Адрес доставки")

    @field_validator("weight", "shipping_cost_rub")
    @classmethod
    def validate_positive(cls, v):
        """Валидация положительных значений."""
        if v <= 0:
            raise ValueError("Значение должно быть больше нуля")
        return v


class PackageDeliveryCreate(PackageDeliveryBase):
    """Схема для создания доставки."""

    transport_company_id: int = Field(..., description="ID транспортной компании")


class PackageDeliveryUpdate(BaseModel):
    """Схема для обновления доставки."""

    tracking_number: Optional[str] = None
    weight: Optional[Decimal] = None
    shipping_cost_rub: Optional[Decimal] = None
    delivery_address: Optional[str] = None
    transport_company_id: Optional[int] = None


class PackageDeliveryResponse(PackageDeliveryBase):
    """Схема для ответа с данными доставки."""

    id: int
    status: str = Field(..., description="Статус доставки")
    price_rub_for_kg: Decimal = Field(..., description="Цена за килограмм в рублях")
    paid_at: Optional[str] = Field(None, description="Дата оплаты")
    transport_company_name: str = Field(
        ..., description="Название транспортной компании"
    )

    class Config:
        """Конфигурация схемы."""

        from_attributes = True
