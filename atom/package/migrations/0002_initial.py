# Generated by Django 4.2.9 on 2025-01-22 19:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("order", "0002_initial"),
        ("package", "0001_initial"),
        ("status", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="packagedelivery",
            name="status",
            field=models.ForeignKey(
                limit_choices_to={"group__code": "DELIVERY_STATUS_CONFIG"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="packages_with_status",
                to="status.status",
                verbose_name="Статус",
            ),
        ),
        migrations.AddField(
            model_name="packagedelivery",
            name="transport_company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="deliveries",
                to="package.transportcompany",
                verbose_name="Транспортная компания",
            ),
        ),
        migrations.AddField(
            model_name="package",
            name="orders",
            field=models.ManyToManyField(
                related_name="packages",
                through="package.PackageOrder",
                to="order.order",
                verbose_name="Заказы",
            ),
        ),
    ]
