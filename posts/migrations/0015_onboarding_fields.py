from django.db import migrations, models


def backfill_onboarding_status(apps, schema_editor):
    Profil = apps.get_model('posts', 'Profil')
    complete_profiles = Profil.objects.exclude(
        boy__isnull=True,
    ).exclude(
        kilo__isnull=True,
    ).exclude(
        hedef_kilo__isnull=True,
    ).exclude(
        dogum_tarihi__isnull=True,
    ).exclude(
        fitness_hedefi='',
    )
    complete_profiles.update(is_onboarded=True)


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0014_add_biometric_fields_to_profil'),
    ]

    operations = [
        migrations.AddField(
            model_name='profil',
            name='cinsiyet',
            field=models.CharField(
                choices=[
                    ('E', 'Erkek'),
                    ('K', 'Kadın'),
                    ('B', 'Belirtmek istemiyorum'),
                ],
                default='B',
                max_length=1,
                verbose_name='Cinsiyet',
            ),
        ),
        migrations.AddField(
            model_name='profil',
            name='is_onboarded',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_onboarding_status, migrations.RunPython.noop),
    ]
