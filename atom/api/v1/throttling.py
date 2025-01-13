from functools import wraps
from django.core.cache import cache
from .exceptions import RateLimitAPIError


def rate_limit(calls: int = 100, period: int = 3600):
    """
    Декоратор для ограничения количества запросов к API.

    Args:
        calls: Максимальное количество запросов
        period: Период в секундах (по умолчанию 1 час)

    Raises:
        RateLimitAPIError: Если превышен лимит запросов

    Example:
        @router.get("/endpoint")
        @rate_limit(calls=100, period=3600)  # 100 запросов в час
        def my_endpoint(request):
            return {"message": "Hello"}
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Формируем ключ для кэша
            if request.auth:
                # Для авторизованных пользователей
                key = f"ratelimit:{request.auth.id}:{func.__name__}"
            else:
                # Для анонимных пользователей используем IP
                key = f"ratelimit:{request.client.host}:{func.__name__}"

            # Получаем текущее количество запросов
            calls_made = cache.get(key, 0)

            # Проверяем лимит
            if calls_made >= calls:
                raise RateLimitAPIError(
                    f"Превышен лимит запросов. "
                    f"Максимум {calls} запросов за {period} секунд."
                )

            # Увеличиваем счетчик
            pipe = cache.pipeline()
            pipe.incr(key)

            # Устанавливаем время жизни ключа, если его еще нет
            if calls_made == 0:
                pipe.expire(key, period)

            pipe.execute()

            # Выполняем оригинальную функцию
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
