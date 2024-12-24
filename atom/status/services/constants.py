"""Работа с константами статусов для приложений."""

from django.contrib.contenttypes.models import ContentType

from ..models import Status


def get_status_descriptions(model_class, group_code=None):
    """Получить описания статусов.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    return {status.code: status.description for status in queryset}


def get_status_names(model_class, group_code=None):
    """Получить названия статусов.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    return {status.code: status.name for status in queryset}


def get_status_codes(model_class, group_code=None):
    """Получить словарь кодов статусов.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    return {status.code: status.code for status in queryset}


def get_status_choices(model_class, group_code=None):
    """Получить список статусов для выбора.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    return [(status.code, status.name) for status in queryset.order_by("order")]


def get_default_status(model_class, group_code=None):
    """Получить код статуса по умолчанию.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)

    Returns:
        str: Код статуса по умолчанию
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type, is_default=True)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    try:
        status = queryset.get()
        return status.code
    except Status.MultipleObjectsReturned:
        # Если несколько статусов по умолчанию, берем первый по порядку
        return queryset.order_by("order").first().code
    except Status.DoesNotExist:
        return None
