# Generated by Django 4.2.9 on 2025-01-22 19:05

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Site",
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
                    "name",
                    models.CharField(
                        max_length=100, unique=True, verbose_name="Название сайта"
                    ),
                ),
                ("url", models.URLField(unique=True, verbose_name="URL сайта")),
                (
                    "organizer_fee_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=5,
                        verbose_name="Ставка организатора (%)",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, null=True, verbose_name="Описание сайта"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Дата оздания"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Дата обновления"),
                ),
            ],
            options={
                "verbose_name": "Сайт",
                "verbose_name_plural": "Сайты",
                "ordering": ["name"],
                "indexes": [
                    models.Index(fields=["name"], name="order_site_name_e5c7b2_idx"),
                    models.Index(fields=["url"], name="order_site_url_fc7750_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Order",
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
                    "internal_number",
                    models.CharField(
                        db_index=True,
                        max_length=255,
                        unique=True,
                        verbose_name="Внутренний номер заказа",
                    ),
                ),
                (
                    "external_number",
                    models.CharField(
                        max_length=255, unique=True, verbose_name="Внешний номер заказа"
                    ),
                ),
                (
                    "amount_euro",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Сумма в евро"
                    ),
                ),
                (
                    "amount_rub",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Сумма в рублях"
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
                    "expense",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        verbose_name="Расходы в рублях",
                    ),
                ),
                (
                    "profit",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        verbose_name="Прибыль в рублях",
                    ),
                ),
                (
                    "comment",
                    models.TextField(blank=True, null=True, verbose_name="Комментарий"),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="order.site",
                        verbose_name="Сайт",
                    ),
                ),
            ],
            options={
                "verbose_name": "Заказ",
                "verbose_name_plural": "Заказы",
                "ordering": ["-created_at"],
            },
        ),
    ]
