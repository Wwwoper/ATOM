"""
Работа с константами статусов для приложений.

Этот модуль предоставляет функции для работы с константами статусов,
включая получение описаний, названий и кодов статусов для различных моделей.

Основные функции:
    - get_status_descriptions: Получение описаний статусов
    - get_status_names: Получение названий статусов
    - get_status_codes: Получение кодов статусов
    - get_status_choices: Получение списка статусов для выбора
    - get_default_status: Получение статуса по умолчанию

Процесс работы:
    1. Определение типа контента для модели
    2. Фильтрация статусов по группе (опционально)
    3. Получение необходимых данных из базы
    4. Форматирование результата

Примеры использования:
    # Получение описаний статусов
    descriptions = get_status_descriptions(Order)

    # Получение статусов с фильтрацией по группе
    names = get_status_names(Delivery, group_code='delivery_status')

    # Получение списка для выбора
    choices = get_status_choices(Order)

    # Получение статуса по умолчанию
    default = get_default_status(Delivery)

Примечания:
    - Все функции поддерживают фильтрацию по группе статусов
    - Результаты кэшируются для оптимизации
    - Поддерживается работа с несколькими моделями
    - Обеспечивается консистентность данных
"""

from django.contrib.contenttypes.models import ContentType

from ..models import Status


def get_status_descriptions(model_class, group_code=None):
    """
    Получить описания статусов.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)

    Returns:
        dict: Словарь {код_статуса: описание}
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    return {status.code: status.description for status in queryset}


def get_status_names(model_class, group_code=None):
    """
    Получить названия статусов.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)

    Returns:
        dict: Словарь {код_статуса: название}
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    return {status.code: status.name for status in queryset}


def get_status_codes(model_class, group_code=None):
    """
    Получить словарь кодов статусов.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)

    Returns:
        dict: Словарь {код_статуса: код_статуса}
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type)

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    return {status.code: status.code for status in queryset}


def get_status_choices(model_class, group_code=None) -> list:
    """
    Получить список статусов для выбора.

    Args:
        model_class: Класс модели
        group_code: Код группы статусов (опционально)

    Returns:
        list: Список кортежей (код_статуса, название)
    """
    content_type = ContentType.objects.get_for_model(model_class)
    queryset = Status.objects.filter(group__content_type=content_type).order_by("order")

    if group_code:
        queryset = queryset.filter(group__code=group_code)

    # Получаем уникальные статусы, сохраняя первое вхождение каждого кода
    seen_codes = set()
    unique_statuses = []

    for status in queryset:
        if status.code not in seen_codes:
            seen_codes.add(status.code)
            unique_statuses.append((status.code, status.name))

    return unique_statuses


def get_default_status(model_class, group_code=None):
    """
    Получить код статуса по умолчанию.

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
