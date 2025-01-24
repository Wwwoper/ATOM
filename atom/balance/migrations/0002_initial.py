# Generated by Django 4.2.9 on 2025-01-24 19:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("balance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="balance",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="balance",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Пользователь",
            ),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                check=models.Q(("amount_euro__gt", 0)), name="positive_amount_euro"
            ),
        ),
        migrations.AddConstraint(
            model_name="balance",
            constraint=models.CheckConstraint(
                check=models.Q(("balance_euro__gte", 0), ("balance_rub__gte", 0)),
                name="non_negative_balance",
            ),
        ),
    ]
