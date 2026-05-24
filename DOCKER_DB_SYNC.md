# Docker MySQL'i Local MySQL ile Esitleme

Bu projede local calisan Django icin `.env` dosyasinda `DB_HOST=localhost` kullaniliyor. Docker icindeki Django ise `localhost` yerine `db` servisine baglanmali. Bu nedenle `docker-compose.yml` icinde `web` servisi icin `DB_HOST=db` ve `DB_PORT=3306` override edildi.

## Ne saglar?

- Docker MySQL importtan once otomatik yedek alinir.
- Local MySQL'den yeni dump alinir.
- Docker MySQL veritabani temizlenir ve local dump geri yuklenir.
- Son durumda Docker verisi local ile birebir ayni olur.

## Calistirma

1. Local MySQL'in acik oldugundan emin olun.
2. Gerekirse `mysqldump.exe` yolunu not edin.
3. Proje klasorunde su komutu calistirin:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-local-mysql-to-docker.ps1
```

Eger `mysqldump` PATH icinde yoksa:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-local-mysql-to-docker.ps1 -MySqlDumpPath "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
```

Eger local veritabani icin dogru kullanici/sifre sizde var ama script ile baglanti kurmak istemiyorsaniz, once herhangi bir aracla `.sql` export alin ve sonra hazir dump'i import edin:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-local-mysql-to-docker.ps1 -ExistingDumpPath ".\backups\my-local-export.sql"
```

## Yedekler nereye gider?

SQL yedekleri `backups\db-sync\` altina yazilir:

- `local-YYYYMMDD-HHMMSS.sql`
- `docker-before-sync-YYYYMMDD-HHMMSS.sql`

## Notlar

- Script, local baglanti bilgisini `.env` icindeki `DB_*` alanlarindan okur.
- Isterseniz local kaynak icin ayri `LOCAL_DB_NAME`, `LOCAL_DB_USER`, `LOCAL_DB_PASSWORD`, `LOCAL_DB_HOST`, `LOCAL_DB_PORT` degiskenlerini tanimlayabilirsiniz.
- `DB_HOST=localhost` ise script otomatik olarak `127.0.0.1` fallback denemesi de yapar.
- `-ExistingDumpPath` verilirse local veritabanina baglanmadan mevcut `.sql` dosyasini Docker'a yukler.
- Docker icindeki MySQL root sifresini `.env` icindeki `MYSQL_ROOT_PASSWORD` alanindan alir.
- Docker'daki eski veri aktif olarak korunmaz; onun yerine importtan once SQL yedegi alinmis olur.
- Amac birebir eslesme oldugu icin Docker veritabani import oncesi silinip yeniden olusturulur.
