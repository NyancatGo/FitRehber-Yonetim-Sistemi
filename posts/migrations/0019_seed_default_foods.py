from decimal import Decimal

from django.db import migrations


def seed_foods(apps, schema_editor):
    Besin = apps.get_model('posts', 'Besin')
    default_foods = [
        {'isim': 'Yumurta (Haşlanmış)', 'kalori_100g': 155, 'protein_100g': Decimal('12.6'), 'karbonhidrat_100g': Decimal('1.1'), 'yag_100g': Decimal('10.6'), 'is_verified': True},
        {'isim': 'Yulaf Ezmesi', 'kalori_100g': 389, 'protein_100g': Decimal('16.9'), 'karbonhidrat_100g': Decimal('66.3'), 'yag_100g': Decimal('6.9'), 'is_verified': True},
        {'isim': 'Tavuk Göğsü (Izgara)', 'kalori_100g': 165, 'protein_100g': Decimal('31.0'), 'karbonhidrat_100g': Decimal('0.0'), 'yag_100g': Decimal('3.6'), 'is_verified': True},
        {'isim': 'Pirinç Pilavı', 'kalori_100g': 130, 'protein_100g': Decimal('2.7'), 'karbonhidrat_100g': Decimal('28.0'), 'yag_100g': Decimal('0.3'), 'is_verified': True},
        {'isim': 'Muz', 'kalori_100g': 89, 'protein_100g': Decimal('1.1'), 'karbonhidrat_100g': Decimal('22.8'), 'yag_100g': Decimal('0.3'), 'is_verified': True},
        {'isim': 'Süzme Yoğurt', 'kalori_100g': 97, 'protein_100g': Decimal('9.0'), 'karbonhidrat_100g': Decimal('4.0'), 'yag_100g': Decimal('5.0'), 'is_verified': True},
        {'isim': 'Tam Buğday Ekmeği', 'kalori_100g': 247, 'protein_100g': Decimal('13.0'), 'karbonhidrat_100g': Decimal('41.0'), 'yag_100g': Decimal('3.4'), 'is_verified': True},
        {'isim': 'Zeytinyağı', 'kalori_100g': 884, 'protein_100g': Decimal('0.0'), 'karbonhidrat_100g': Decimal('0.0'), 'yag_100g': Decimal('100.0'), 'is_verified': True},
    ]

    for food in default_foods:
        Besin.objects.get_or_create(isim=food['isim'], defaults=food)


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0018_besin_ogunkaydi'),
    ]

    operations = [
        migrations.RunPython(seed_foods, migrations.RunPython.noop),
    ]
