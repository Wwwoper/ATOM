from jose import jwt, JWTError
from ninja.security import HttpBearer
from django.conf import settings
from django.contrib.auth import get_user_model
from ..exceptions import AuthenticationAPIError

User = get_user_model()


class AuthBearer(HttpBearer):
    """
    Класс для проверки JWT токенов в заголовке Authorization.
    Используется как декоратор @auth для защиты эндпоинтов.
    """

    def authenticate(self, request, token):
        """
        Проверяет JWT токен и возвращает пользователя.

        Args:
            request: HTTP запрос
            token: JWT токен из заголовка Authorization

        Returns:
            User: объект пользователя если токен валидный
            None: если токен невалидный

        Raises:
            AuthenticationAPIError: если токен просрочен или невалиден
        """
        try:
            # Декодируем JWT токен
            payload = jwt.decode(
                token,
                settings.JWT_AUTH["SECRET_KEY"],
                algorithms=[settings.JWT_AUTH["ALGORITHM"]],
            )

            # Проверяем тип токена (должен быть access)
            if payload.get("type") != "access":
                raise AuthenticationAPIError("Неверный тип токена")

            # Получаем ID пользователя из токена
            user_id = payload.get("sub")
            if user_id is None:
                raise AuthenticationAPIError("Токен не содержит ID пользователя")

            # Получаем пользователя из базы
            user = User.objects.filter(id=int(user_id)).first()
            if user is None:
                raise AuthenticationAPIError("Пользователь не найден")

            return user

        except JWTError:
            raise AuthenticationAPIError("Невалидный токен")


# Создаем экземпляр класса для использования в декораторах
auth = AuthBearer()
