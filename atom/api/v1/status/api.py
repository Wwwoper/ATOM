from typing import List
from django.shortcuts import get_object_or_404
from ninja import Router
from django.contrib.contenttypes.models import ContentType

from status.models import Status, StatusGroup
from status.services.constants import (
    get_status_choices,
    get_default_status,
    get_status_descriptions,
)
from .schemas import StatusGroupOut, StatusOut, StatusTransitionCheck
from ..auth.api import auth

router = Router(tags=["status"])


@router.get(
    "/groups",
    response=List[StatusGroupOut],
    auth=auth,
    summary="Список групп статусов",
    description="Получение списка всех групп статусов",
)
def list_status_groups(request):
    """Получение списка групп статусов."""
    return StatusGroup.objects.all()


@router.get(
    "/groups/{group_id}",
    response=StatusGroupOut,
    auth=auth,
    summary="Детали группы статусов",
    description="Получение информации о конкретной группе статусов",
)
def get_status_group(request, group_id: int):
    """Получение информации о группе статусов."""
    return get_object_or_404(StatusGroup, id=group_id)


@router.get(
    "/groups/{group_id}/statuses",
    response=List[StatusOut],
    auth=auth,
    summary="Статусы группы",
    description="Получение списка статусов для конкретной группы",
)
def list_group_statuses(request, group_id: int):
    """Получение списка статусов группы."""
    group = get_object_or_404(StatusGroup, id=group_id)
    return Status.objects.filter(group=group)


@router.post(
    "/groups/{group_id}/check-transition",
    response=bool,
    auth=auth,
    summary="Проверка перехода",
    description="Проверка возможности перехода между статусами",
)
def check_status_transition(request, group_id: int, transition: StatusTransitionCheck):
    """Проверка возможности перехода между статусами."""
    group = get_object_or_404(StatusGroup, id=group_id)
    return group.is_transition_allowed(transition.from_status, transition.to_status)


@router.get(
    "/model/{app_label}/{model_name}/choices",
    response=List[tuple[str, str]],
    auth=auth,
    summary="Варианты статусов",
    description="Получение списка возможных статусов для модели",
)
def get_model_status_choices(request, app_label: str, model_name: str):
    """Получение списка возможных статусов для модели."""
    model = ContentType.objects.get(app_label=app_label, model=model_name).model_class()
    return get_status_choices(model)


@router.get(
    "/model/{app_label}/{model_name}/default",
    response=str,
    auth=auth,
    summary="Статус по умолчанию",
    description="Получение статуса по умолчанию для модели",
)
def get_model_default_status(request, app_label: str, model_name: str):
    """Получение статуса по умолчанию для модели."""
    model = ContentType.objects.get(app_label=app_label, model=model_name).model_class()
    return get_default_status(model)


@router.get(
    "/model/{app_label}/{model_name}/descriptions",
    response=dict,
    auth=auth,
    summary="Описания статусов",
    description="Получение описаний всех статусов для модели",
)
def get_model_status_descriptions(request, app_label: str, model_name: str):
    """Получение описаний статусов для модели."""
    model = ContentType.objects.get(app_label=app_label, model=model_name).model_class()
    return get_status_descriptions(model)
