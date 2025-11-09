from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_player_attendance_days"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayerAttendance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField()),
                ("days", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_records",
                        to="core.player",
                    ),
                ),
            ],
            options={
                "ordering": ["-month"],
                "unique_together": {("player", "month")},
            },
        ),
    ]