from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Veritabanı ve tabloları utf8mb4_unicode_ci (Türkçe karakter desteği) yapar.'

    def handle(self, *args, **options):
        db_name = connection.settings_dict['NAME']
        
        with connection.cursor() as cursor:
            # 1. Veritabanı seviyesinde ayar
            self.stdout.write(f"Veritabanı ayarlanıyor: {db_name}...")
            cursor.execute(f"ALTER DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            
            # 2. Tüm tabloları listeleyip güncelle
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                self.stdout.write(f"Tablo güncelleniyor: {table}...")
                cursor.execute(f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                
        self.stdout.write(self.style.SUCCESS('Tebrikler knk! Tüm veritabanı artık Türkçe karakter dostu. ✅'))
