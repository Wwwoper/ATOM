from ninja import ModelSchema, Schema, Field
from user.models import User


class UserOut(ModelSchema):
    """Схема для отображения данных пользователя."""

    id: int = Field(..., description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    email: str = Field(..., description="Email пользователя")
    first_name: str | None = Field(None, description="Имя")
    last_name: str | None = Field(None, description="Фамилия")
    company_name: str | None = Field(None, description="Название компании")
    phone: str | None = Field(None, description="Телефон")
    address: str | None = Field(None, description="Адрес")

    class Config:
        model = User
        model_exclude = ["password", "user_permissions", "groups"]


class UserCreate(Schema):
    """Схема для создания пользователя."""

    username: str = Field(..., description="Имя пользователя (логин)")
    email: str = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")
    company_name: str | None = Field(None, description="Название компании")
    phone: str | None = Field(None, description="Телефон")
    address: str | None = Field(None, description="Адрес")
    first_name: str | None = Field(None, description="Имя")
    last_name: str | None = Field(None, description="Фамилия")


class UserUpdate(Schema):
    """Схема для обновления данных пользователя."""

    company_name: str | None = Field(None, description="Название компании")
    phone: str | None = Field(None, description="Телефон")
    address: str | None = Field(None, description="Адрес")
    first_name: str | None = Field(None, description="Имя")
    last_name: str | None = Field(None, description="Фамилия")


class TokenOut(Schema):
    """Схема для токенов."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthIn(Schema):
    """Схема для авторизации."""

    username: str
    password: str


class RefreshIn(Schema):
    """Схема для обновления токена."""

    refresh_token: str
