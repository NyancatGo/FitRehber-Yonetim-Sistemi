# Generated manually for mobile API content likes.

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0015_onboarding_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='icerik',
            name='begenenler',
            field=models.ManyToManyField(
                blank=True,
                related_name='begendigi_icerikler',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
