# Generated for the advanced meal tracking module.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0017_gunlukbeslenmesu'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Besin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('isim', models.CharField(max_length=150, verbose_name='Besin Adı')),
                ('marka', models.CharField(blank=True, max_length=100, null=True, verbose_name='Marka / Üretici')),
                ('barkod', models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='Barkod No')),
                ('kalori_100g', models.IntegerField(verbose_name='Kalori (kcal/100g)')),
                ('protein_100g', models.DecimalField(decimal_places=1, max_digits=5, verbose_name='Protein (g/100g)')),
                ('karbonhidrat_100g', models.DecimalField(decimal_places=1, max_digits=5, verbose_name='Karb (g/100g)')),
                ('yag_100g', models.DecimalField(decimal_places=1, max_digits=5, verbose_name='Yağ (g/100g)')),
                ('is_verified', models.BooleanField(default=False, verbose_name='Onaylı Besin')),
            ],
            options={
                'verbose_name': 'Besin',
                'verbose_name_plural': 'Besinler',
                'indexes': [
                    models.Index(fields=['isim'], name='posts_besin_isim_idx'),
                    models.Index(fields=['barkod'], name='posts_besin_barkod_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='OgunKaydi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tarih', models.DateField(verbose_name='Kayıt Tarihi')),
                ('ogun_tipi', models.CharField(choices=[('sabah', 'Sabah Kahvaltısı'), ('ogle', 'Öğle Yemeği'), ('aksam', 'Akşam Yemeği'), ('atistirmalik', 'Atıştırmalık / Diğer')], max_length=15, verbose_name='Öğün')),
                ('besin_isim', models.CharField(max_length=150, verbose_name='Besin / Öğün Adı')),
                ('miktar', models.DecimalField(decimal_places=1, max_digits=6, verbose_name='Miktar')),
                ('miktar_birimi', models.CharField(default='g', max_length=20, verbose_name='Birim')),
                ('kalori', models.IntegerField(verbose_name='Toplam Kalori (kcal)')),
                ('protein', models.DecimalField(decimal_places=1, max_digits=5, verbose_name='Toplam Protein (g)')),
                ('karbonhidrat', models.DecimalField(decimal_places=1, max_digits=5, verbose_name='Toplam Karb (g)')),
                ('yag', models.DecimalField(decimal_places=1, max_digits=5, verbose_name='Toplam Yağ (g)')),
                ('besin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kayitlar', to='posts.besin')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ogun_kayitlari', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Öğün Kaydı',
                'verbose_name_plural': 'Öğün Kayıtları',
                'ordering': ['tarih', 'ogun_tipi'],
                'indexes': [
                    models.Index(fields=['user', 'tarih'], name='posts_ogunkaydi_user_tarih_idx'),
                    models.Index(fields=['tarih'], name='posts_ogunkaydi_tarih_idx'),
                ],
            },
        ),
    ]
