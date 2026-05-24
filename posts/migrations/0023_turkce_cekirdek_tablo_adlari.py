from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0022_mobileoauthcode'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='kategori',
            table='kategoriler',
        ),
        migrations.AlterModelTable(
            name='icerik',
            table='icerikler',
        ),
        migrations.AlterModelTable(
            name='yorum',
            table='yorumlar',
        ),
        migrations.AlterModelTable(
            name='profil',
            table='profiller',
        ),
        migrations.AlterField(
            model_name='icerik',
            name='kaydedenler',
            field=models.ManyToManyField(
                blank=True,
                db_table='icerik_kaydetmeleri',
                related_name='kaydedilen_icerikler',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='icerik',
            name='begenenler',
            field=models.ManyToManyField(
                blank=True,
                db_table='icerik_begenileri',
                related_name='begendigi_icerikler',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='yorum',
            name='begenenler',
            field=models.ManyToManyField(
                blank=True,
                db_table='yorum_begenileri',
                related_name='begendigi_yorumlar',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
