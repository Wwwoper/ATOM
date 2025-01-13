from ninja.errors import HttpError


class APIError(HttpError):
    """Базовый класс для API ошибок."""

    default_detail = "Произошла ошибка"
    status_code = 500


class ValidationAPIError(APIError):
    """Ошибка валидации данных."""

    default_detail = "Ошибка валидации данных"
    status_code = 400


class NotFoundAPIError(APIError):
    """Ошибка: ресурс не найден."""

    default_detail = "Запрашиваемый ресурс не найден"
    status_code = 404


class AuthenticationAPIError(APIError):
    """Ошибка аутентификации."""

    default_detail = "Ошибка аутентификации"
    status_code = 401


class PermissionAPIError(APIError):
    """Ошибка прав доступа."""

    default_detail = "Недостаточно прав для выполнения операции"
    status_code = 403


class ConflictAPIError(APIError):
    """Ошибка конфликта данных."""

    default_detail = "Конфликт при обработке данных"
    status_code = 409


class RateLimitAPIError(APIError):
    """Ошибка превышения лимита запросов."""

    default_detail = "Превышен лимит запросов"
    status_code = 429
