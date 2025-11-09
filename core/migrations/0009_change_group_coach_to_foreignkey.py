from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_player_attendance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="group",
            name="coach",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="groups",
                to="core.coach",
                null=True,
                blank=True,
            ),
        ),
    ]