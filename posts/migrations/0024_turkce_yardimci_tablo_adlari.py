from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0023_turkce_cekirdek_tablo_adlari'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='aktivite',
            table='aktiviteler',
        ),
        migrations.AlterModelTable(
            name='besin',
            table='besinler',
        ),
        migrations.AlterModelTable(
            name='gunlukaktivite',
            table='gunluk_aktiviteler',
        ),
        migrations.AlterModelTable(
            name='gunlukbeslenmesu',
            table='gunluk_beslenme_su_kayitlari',
        ),
        migrations.AlterModelTable(
            name='guvenlikihlali',
            table='guvenlik_ihlalleri',
        ),
        migrations.AlterModelTable(
            name='mobileoauthcode',
            table='mobil_oauth_kodlari',
        ),
        migrations.AlterModelTable(
            name='ogunkaydi',
            table='ogun_kayitlari',
        ),
    ]
