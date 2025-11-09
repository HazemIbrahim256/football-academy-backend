from django.db import migrations, models
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_coach_phone"),
    ]

    operations = [
        migrations.AlterField(
            model_name="playerevaluation",
            name="dribbling",
            field=models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]),
        ),
        migrations.AlterField(
            model_name="playerevaluation",
            name="passing",
            field=models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]),
        ),
        migrations.AlterField(
            model_name="playerevaluation",
            name="shooting",
            field=models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]),
        ),
        migrations.AlterField(
            model_name="playerevaluation",
            name="defense",
            field=models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]),
        ),
        migrations.AlterField(
            model_name="playerevaluation",
            name="speed",
            field=models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]),
        ),
        migrations.AlterField(
            model_name="playerevaluation",
            name="teamwork",
            field=models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]),
        ),
    ]