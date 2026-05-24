from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0012_alter_gunlukaktivite_tarih"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="foto",
            field=models.ImageField(blank=True, null=True, upload_to="profil_fotograflari/"),
        ),
    ]
