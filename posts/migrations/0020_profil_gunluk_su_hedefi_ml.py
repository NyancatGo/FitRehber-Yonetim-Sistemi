from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posts', '0019_seed_default_foods'),
    ]

    operations = [
        migrations.AddField(
            model_name='profil',
            name='gunluk_su_hedefi_ml',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text='Boş bırakılırsa kilo × 35 ml formülü kullanılır.',
                verbose_name='Günlük Su Hedefi (ml)',
            ),
        ),
    ]
