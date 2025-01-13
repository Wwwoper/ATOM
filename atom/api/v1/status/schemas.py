from ninja import ModelSchema, Schema, Field
from status.models import Status, StatusGroup


class StatusGroupBase(Schema):
    """Базовая схема для группы статусов."""

    name: str = Field(..., description="Название группы статусов")
    code: str = Field(..., description="Уникальный код группы")
    allowed_status_transitions: dict = Field(
        default={}, description="Разрешенные переходы между статусами"
    )
    transaction_type_by_status: dict = Field(
        default={}, description="Типы транзакций для статусов"
    )


class StatusGroupOut(ModelSchema):
    """Схема для отображения группы статусов."""

    id: int = Field(..., description="ID группы статусов")
    name: str = Field(..., description="Название группы")
    code: str = Field(..., description="Код группы")
    allowed_status_transitions: dict = Field(..., description="Разрешенные переходы")
    transaction_type_by_status: dict = Field(..., description="Типы транзакций")
    content_type_id: int = Field(..., description="ID типа контента")

    class Config:
        model = StatusGroup
        model_fields = [
            "id",
            "name",
            "code",
            "allowed_status_transitions",
            "transaction_type_by_status",
            "content_type",
        ]


class StatusBase(Schema):
    """Базовая схема для статуса."""

    code: str = Field(..., description="Код статуса")
    name: str = Field(..., description="Название статуса")
    description: str | None = Field(None, description="Описание статуса")
    is_default: bool = Field(False, description="Является ли статусом по умолчанию")
    order: int = Field(0, description="Порядок сортировки")


class StatusOut(ModelSchema):
    """Схема для отображения статуса."""

    id: int = Field(..., description="ID статуса")
    group_id: int = Field(..., description="ID группы статусов")
    code: str = Field(..., description="Код статуса")
    name: str = Field(..., description="Название статуса")
    description: str | None = Field(None, description="Описание статуса")
    is_default: bool = Field(..., description="Статус по умолчанию")
    order: int = Field(..., description="Порядок сортировки")

    class Config:
        model = Status
        model_fields = [
            "id",
            "group",
            "code",
            "name",
            "description",
            "is_default",
            "order",
        ]


class StatusTransitionCheck(Schema):
    """Схема для проверки возможности перехода между статусами."""

    from_status: str = Field(..., description="Исходный статус")
    to_status: str = Field(..., description="Целевой статус")
