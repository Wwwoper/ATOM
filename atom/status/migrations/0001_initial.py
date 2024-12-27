# Generated by Django 4.2.9 on 2024-12-27 18:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="StatusGroup",
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
                    models.CharField(max_length=100, verbose_name="Название группы"),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="Код группы"
                    ),
                ),
                (
                    "allowed_status_transitions",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Разрешенные переходы между статусами",
                    ),
                ),
                (
                    "transaction_type_by_status",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Типы транзакций для статусов",
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                        verbose_name="Тип сущности",
                    ),
                ),
            ],
            options={
                "verbose_name": "Группа статусов",
                "verbose_name_plural": "Группы статусов",
                "unique_together": {("code", "content_type")},
            },
        ),
        migrations.CreateModel(
            name="Status",
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
                ("code", models.CharField(max_length=50, verbose_name="Код статуса")),
                (
                    "name",
                    models.CharField(max_length=50, verbose_name="Название статуса"),
                ),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Описание"),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False, verbose_name="Статус по умолчанию"
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(default=0, verbose_name="Порядок"),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status",
                        to="status.statusgroup",
                        verbose_name="Группа статусов",
                    ),
                ),
            ],
            options={
                "verbose_name": "Статус",
                "verbose_name_plural": "Статусы",
                "ordering": ["group", "order"],
                "unique_together": {("group", "code")},
            },
        ),
    ]