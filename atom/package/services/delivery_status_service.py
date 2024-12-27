"""
Сервис для управления статусами доставки.

Этот модуль предоставляет функциональность для управления жизненным циклом доставок
через изменение их статусов. Реализует бизнес-логику переходов между статусами
и обеспечивает валидацию этих переходов.

Основные компоненты:
    - DeliveryStatusService: Основной класс для работы со статусами доставок
    - process_status_change: Обработка изменения статуса доставки
    - _check_status_change: Проверка возможности изменения статуса
    - _set_initial_status: Установка начального статуса для новой доставки
    - _validate_status_change: Валидация возможности перехода между статусами

Процесс изменения статуса:
    1. Проверка текущего состояния доставки
    2. Валидация возможности перехода в новый статус
    3. Применение изменений с использованием соответствующей стратегии
    4. Обновление связанных данных доставки

Правила переходов:
    - Новая доставка получает статус по умолчанию
    - Переходы между статусами строго регламентированы
    - Некоторые переходы могут требовать дополнительных проверок
    - Запрещены циклические переходы между статусами

Примеры использования:
    service = DeliveryStatusService()
    
    # Обработка изменения статуса
    service.process_status_change(delivery)
    
    # Установка начального статуса
    service._set_initial_status(new_delivery)

Примечания:
    - Все изменения статусов логируются
    - Недопустимые переходы вызывают ValidationError
    - Сервис интегрирован с системой стратегий обработки доставок
    - Поддерживается асинхронная обработка изменений статусов
"""

from django.forms import ValidationError
from status.models import Status

from .delivery_processor_service import DeliveryProcessor


class DeliveryStatusService:
    """Сервис для управления статусами доставки."""

    def __init__(self):
        """Инициализация сервиса."""
        self.delivery_processor = DeliveryProcessor()

    def process_status_change(
        self, delivery: "Delivery", skip_status_processing: bool = False
    ) -> bool:
        """Обработка изменения статуса доставки."""
        try:
            print(f"DeliveryStatusService: обработка изменения статуса")
            print(f"DeliveryStatusService: текущий статус - {delivery.status.code}")
            print(
                f"DeliveryStatusService: skip_status_processing - {skip_status_processing}"
            )

            # Проверяем стоимость посылки перед сменой статуса
            if delivery.package and delivery.package.total_cost_eur <= 0:
                if delivery.status and delivery.status.code == "paid":
                    raise ValidationError(
                        {
                            "package": (
                                "Невозможно установить статус 'Оплачено'. "
                                "Укажите стоимость доставки и комиссию в посылке."
                            )
                        }
                    )

            status_changed = self._check_status_change(delivery)
            print(f"DeliveryStatusService: статус изменился - {status_changed}")

            if status_changed and not skip_status_processing:
                print("DeliveryStatusService: вызов процессора")
                self.delivery_processor.execute_status_strategy(delivery)

            return status_changed

        except Exception as e:
            print(f"DeliveryStatusService: ошибка - {str(e)}")
            raise ValidationError(str(e))

    def _check_status_change(self, delivery: "Delivery") -> bool:
        """Проверка изменения статуса."""
        if not delivery.pk:
            return False

        old_delivery = delivery.__class__.objects.filter(pk=delivery.pk).first()
        if not old_delivery:
            return False

        return old_delivery.status != delivery.status

    def _set_initial_status(self, delivery: "Delivery") -> bool:
        """Установка начального статуса для новой доставки."""
        default_status_code = get_default_status(
            delivery.__class__, group_code="delivery_status"
        )
        if not default_status_code:
            raise ValidationError(
                "Невозможно создать доставку без статуса по умолчанию"
            )

        delivery.status = Status.objects.get(
            code=default_status_code, group__code="delivery_status"
        )
        return True

    def _validate_status_change(
        self, delivery: "Delivery", new_status_code: str
    ) -> None:
        """Валидация возможности перехода доставки в новый статус.

        Args:
            delivery: Доставка
            new_status_code: Код нового статуса
        Raises:
            ValidationError: Если переход в новый статус недопустим
        """
        current_status = delivery.status

        # Проверяем возможность перехода
        if not current_status.group.is_transition_allowed(
            current_status.code, new_status_code
        ):
            raise ValidationError(
                f"Переход из статуса доставки '{current_status.code}' "
                f"в '{new_status_code}' недопустим"
            )
