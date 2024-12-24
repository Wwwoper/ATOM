# Generated by Django 4.2.9 on 2024-12-24 18:43

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("order", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Package",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "number",
                    models.CharField(
                        max_length=255,
                        verbose_name="Номер посылки в сервисе у посредника",
                    ),
                ),
                (
                    "shipping_cost_eur",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        verbose_name="Стоимость отправки в евро",
                    ),
                ),
                (
                    "fee_cost_eur",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        verbose_name="Комиссия организатора за заказы в посылке",
                    ),
                ),
                (
                    "created_at",
                    models.DateField(auto_now_add=True, verbose_name="Дата создания"),
                ),
                (
                    "updated_at",
                    models.DateField(auto_now=True, verbose_name="Дата обновления"),
                ),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
            ],
            options={
                "verbose_name": "Посылка",
                "verbose_name_plural": "Посылки",
            },
        ),
        migrations.CreateModel(
            name="PackageDelivery",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tracking_number",
                    models.CharField(
                        max_length=255, verbose_name="Трек номер для отслеживания"
                    ),
                ),
                (
                    "weight",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Общий вес в кг"
                    ),
                ),
                (
                    "shipping_cost_rub",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        verbose_name="Стоимость отправки в рублях",
                    ),
                ),
                (
                    "price_rub_for_kg",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        verbose_name="Стоимость за кг в рублях",
                    ),
                ),
                (
                    "created_at",
                    models.DateField(
                        default=django.utils.timezone.now, verbose_name="Дата создания"
                    ),
                ),
                (
                    "paid_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Дата оплаты"
                    ),
                ),
                (
                    "delivery_address",
                    models.TextField(blank=True, verbose_name="Адрес доставки"),
                ),
            ],
            options={
                "verbose_name": "Доставка посылки",
                "verbose_name_plural": "Доставки посылок",
            },
        ),
        migrations.CreateModel(
            name="PackageOrder",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Дата добавления"
                    ),
                ),
            ],
            options={
                "verbose_name": "Связь с заказами",
                "verbose_name_plural": "Связи с заказами",
            },
        ),
        migrations.CreateModel(
            name="TransportCompany",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="Название")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Активна"),
                ),
                (
                    "is_default",
                    models.BooleanField(default=False, verbose_name="ТК по умолчанию"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Дата создания"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Дата обновления"),
                ),
            ],
            options={
                "verbose_name": "Транспортная компания",
                "verbose_name_plural": "Транспортные компании",
                "ordering": ("name",),
            },
        ),
        migrations.AddConstraint(
            model_name="transportcompany",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default", True)),
                fields=("is_default",),
                name="unique_default_transport_company",
            ),
        ),
        migrations.AddField(
            model_name="packageorder",
            name="order",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="order.order",
                verbose_name="Заказ",
            ),
        ),
        migrations.AddField(
            model_name="packageorder",
            name="package",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="package.package",
                verbose_name="Посылка",
            ),
        ),
        migrations.AddField(
            model_name="packagedelivery",
            name="package",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                to="package.package",
                verbose_name="Посылка",
            ),
        ),
    ]
