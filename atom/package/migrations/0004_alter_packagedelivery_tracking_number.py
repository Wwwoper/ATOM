# Generated by Django 4.2.9 on 2024-12-26 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("package", "0003_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="packagedelivery",
            name="tracking_number",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="Трек номер для отслеживания"
            ),
        ),
    ]
