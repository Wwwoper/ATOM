"""API endpoints для работы с посылками и доставками."""

from typing import List
from django.shortcuts import get_object_or_404
from ninja import Router
from django.core.exceptions import ValidationError

from package.models import Package, PackageDelivery, TransportCompany
from package.services.delivery_service import PackageDeliveryService
from .schemas import (
    PackageResponse,
    PackageCreate,
    PackageDeliveryResponse,
    PackageDeliveryCreate,
)
from ..auth.api import auth

router = Router(tags=["packages"])


@router.post(
    "/",
    response=PackageResponse,
    auth=auth,
    summary="Создание посылки",
    description="Создание новой посылки в системе",
)
def create_package(request, package: PackageCreate):
    """Создание новой посылки."""
    try:
        package = Package.objects.create(
            user=request.auth,
            number=package.number,
            shipping_cost_eur=package.shipping_cost_eur,
            fee_cost_eur=package.fee_cost_eur,
            comment=package.comment,
        )
        return package
    except ValidationError as e:
        raise ValidationError(str(e))


@router.get(
    "/{package_id}",
    response=PackageResponse,
    auth=auth,
    summary="Детали посылки",
    description="Получение информации о конкретной посылке",
)
def get_package(request, package_id: int):
    """Получение информации о посылке."""
    return get_object_or_404(Package, id=package_id, user=request.auth)


@router.post(
    "/{package_id}/delivery",
    response=PackageDeliveryResponse,
    auth=auth,
    summary="Создание доставки",
    description="Создание доставки для конкретной посылки",
)
def create_delivery(request, package_id: int, delivery: PackageDeliveryCreate):
    """Создание доставки для посылки."""
    package = get_object_or_404(Package, id=package_id, user=request.auth)

    transport_company = get_object_or_404(
        TransportCompany, id=delivery.transport_company_id, is_active=True
    )

    try:
        delivery_service = PackageDeliveryService()
        delivery = PackageDelivery.objects.create(
            package=package,
            transport_company=transport_company,
            tracking_number=delivery.tracking_number,
            weight=delivery.weight,
            shipping_cost_rub=delivery.shipping_cost_rub,
            delivery_address=delivery.delivery_address,
        )

        # Расчет стоимости доставки
        delivery_service.calculate_delivery_costs(delivery)
        delivery.save()

        return delivery
    except ValidationError as e:
        raise ValidationError(str(e))


@router.get(
    "/{package_id}/delivery",
    response=PackageDeliveryResponse,
    auth=auth,
    summary="Детали доставки",
    description="Получение информации о доставке посылки",
)
def get_delivery(request, package_id: int):
    """Получение информации о доставке посылки."""
    delivery = get_object_or_404(
        PackageDelivery.objects.select_related("package"),
        package__id=package_id,
        package__user=request.auth,
    )
    return delivery


@router.get(
    "/",
    response=List[PackageResponse],
    auth=auth,
    summary="Список посылок",
    description="Получение списка всех посылок пользователя",
)
def list_packages(request):
    """Получение списка всех посылок пользователя."""
    return Package.objects.filter(user=request.auth)
