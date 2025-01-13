from typing import List
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from ninja import Router
from order.models import Order, Site
from .schemas import OrderOut, OrderCreate, OrderUpdate, SiteOut, SiteCreate, SiteUpdate
from ..auth.api import auth

router = Router(tags=["orders"])


# Эндпоинты для заказов
@router.get(
    "/orders",
    response=List[OrderOut],
    auth=auth,
    summary="Список заказов",
    description="Получение списка всех заказов текущего пользователя",
)
def list_orders(request):
    """Получение списка заказов пользователя."""
    return Order.objects.filter(user=request.auth)


@router.get(
    "/orders/{order_id}",
    response=OrderOut,
    auth=auth,
    summary="Детали заказа",
    description="Получение подробной информации о конкретном заказе",
)
def get_order(request, order_id: int):
    """Получение информации о заказе."""
    return get_object_or_404(Order, id=order_id, user=request.auth)


@router.post(
    "/orders",
    response=OrderOut,
    auth=auth,
    summary="Создание заказа",
    description="Создание нового заказа в системе",
)
def create_order(request, order_data: OrderCreate):
    """Создание нового заказа."""
    try:
        site = get_object_or_404(Site, id=order_data.site_id)
        order = Order.objects.create(
            user=request.auth, site=site, **order_data.dict(exclude={"site_id"})
        )
        return order
    except ValidationError as e:
        raise ValidationError(str(e))


@router.put(
    "/orders/{order_id}",
    response=OrderOut,
    auth=auth,
    summary="Обновление заказа",
    description="Обновление существующего заказа",
)
def update_order(request, order_id: int, order_data: OrderUpdate):
    """Обновление существующего заказа."""
    order = get_object_or_404(Order, id=order_id, user=request.auth)

    for field, value in order_data.dict(exclude_unset=True).items():
        setattr(order, field, value)

    try:
        order.save()
        return order
    except ValidationError as e:
        raise ValidationError(str(e))


# Эндпоинты для сайтов
@router.get(
    "/sites",
    response=List[SiteOut],
    auth=auth,
    summary="Список сайтов",
    description="Получение списка всех доступных сайтов",
)
def list_sites(request):
    """Получение списка всех сайтов."""
    return Site.objects.all()


@router.get(
    "/sites/{site_id}",
    response=SiteOut,
    auth=auth,
    summary="Детали сайта",
    description="Получение подробной информации о конкретном сайте",
)
def get_site(request, site_id: int):
    """Получение информации о сайте."""
    return get_object_or_404(Site, id=site_id)


@router.post(
    "/sites",
    response=SiteOut,
    auth=auth,
    summary="Создание сайта",
    description="Создание нового сайта в системе",
)
def create_site(request, site_data: SiteCreate):
    """Создание нового сайта."""
    try:
        site = Site.objects.create(**site_data.dict())
        return site
    except ValidationError as e:
        raise ValidationError(str(e))


@router.put(
    "/sites/{site_id}",
    response=SiteOut,
    auth=auth,
    summary="Обновление сайта",
    description="Обновление существующего сайта",
)
def update_site(request, site_id: int, site_data: SiteUpdate):
    """Обновление существующего сайта."""
    site = get_object_or_404(Site, id=site_id)

    for field, value in site_data.dict(exclude_unset=True).items():
        setattr(site, field, value)

    try:
        site.save()
        return site
    except ValidationError as e:
        raise ValidationError(str(e))
