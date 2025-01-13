from ninja import Router
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from typing import List, Optional
from user.services import UserService
from .schemas import UserOut, UserCreate, UserUpdate, TokenOut, AuthIn, RefreshIn
from user.models import User
from django.core.exceptions import ValidationError
from ninja.security import HttpBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta
from ninja.schema import Schema
from django.conf import settings

router = Router(tags=["auth"])


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
        except jwt.JWTError:
            return None
        user = User.objects.filter(username=username).first()
        if user is None:
            return None
        return user


auth = AuthBearer()


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_AUTH["SECRET_KEY"],
        algorithm=settings.JWT_AUTH["ALGORITHM"],
    )
    return encoded_jwt


def create_tokens(user_id: int) -> dict:
    """Создание пары access и refresh токенов."""
    access_token_expires = timedelta(
        minutes=settings.JWT_AUTH["ACCESS_TOKEN_EXPIRE_MINUTES"]
    )
    refresh_token_expires = timedelta(
        days=settings.JWT_AUTH["REFRESH_TOKEN_EXPIRE_DAYS"]
    )

    access_token = create_token(
        data={"sub": str(user_id), "type": "access"}, expires_delta=access_token_expires
    )

    refresh_token = create_token(
        data={"sub": str(user_id), "type": "refresh"},
        expires_delta=refresh_token_expires,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post(
    "/token",
    response=TokenOut,
    summary="Получить токен авторизации",
    description="Авторизация пользователя и получение JWT токена",
)
def login(request, auth_data: AuthIn):
    """Авторизация пользователя и получение токенов."""
    user = authenticate(username=auth_data.username, password=auth_data.password)
    if not user:
        raise ValidationError("Неверные учетные данные")

    return create_tokens(user.id)


@router.post(
    "/token/refresh",
    response=TokenOut,
    summary="Обновление access токена с помощью refresh токена",
    description="Обновление access токена с помощью refresh токена",
)
def refresh_token(request, refresh_data: RefreshIn):
    """Обновление access токена с помощью refresh токена."""
    try:
        payload = jwt.decode(
            refresh_data.refresh_token,
            settings.JWT_AUTH["SECRET_KEY"],
            algorithms=[settings.JWT_AUTH["ALGORITHM"]],
        )

        # Проверяем, что это refresh токен
        if payload.get("type") != "refresh":
            raise ValidationError("Invalid token type")

        user_id = int(payload.get("sub"))
        return create_tokens(user_id)

    except JWTError:
        raise ValidationError("Invalid refresh token")


@router.post(
    "/users",
    response=UserOut,
    summary="Регистрация пользователя",
    description="Создание нового пользователя в системе",
)
def create_user(request, user_data: UserCreate):
    """Регистрация нового пользователя"""
    try:
        user = UserService.create_user(**user_data.dict())
        return user
    except ValidationError as e:
        raise ValidationError(str(e))


@router.get(
    "/users/me",
    response=UserOut,
    auth=auth,
    summary="Профиль пользователя",
    description="Получение данных текущего авторизованного пользователя",
)
def get_current_user(request):
    """Получение данных текущего пользователя"""
    return request.auth


@router.put(
    "/users/me",
    response=UserOut,
    auth=auth,
    summary="Обновление профиля",
    description="Обновление данных текущего пользователя",
)
def update_current_user(request, user_data: UserUpdate):
    """Обновление данных текущего пользователя"""
    user = request.auth
    for field, value in user_data.dict(exclude_unset=True).items():
        setattr(user, field, value)
    user.save()
    return user


@router.get(
    "/users",
    response=List[UserOut],
    auth=auth,
    summary="Список пользователей",
    description="Получение списка всех пользователей системы",
)
def list_users(request):
    """Получение списка всех пользователей"""
    return User.objects.all()


@router.get(
    "/users/{user_id}",
    response=UserOut,
    auth=auth,
    summary="Данные пользователя",
    description="Получение данных конкретного пользователя по ID",
)
def get_user(request, user_id: int):
    """Получение данных пользователя по ID"""
    return get_object_or_404(User, id=user_id)


class TokenOut(Schema):
    access_token: str
    refresh_token: str  # Добавить refresh token
    token_type: str
