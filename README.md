# FitRehber Yönetim Sistemi

**BTS304 – Veritabanı Yönetim Sistemleri II / Final Sınavına Ek Ödev**
Bartın Üniversitesi · Fen Fakültesi · Bilgisayar Teknolojisi ve Bilişim Sistemleri Bölümü
Öğretim Elemanı: Dr. Öğr. Üyesi Bayram AKGÜL

---

## Hızlı Kurulum (Hocanın İndirdiği ZIP İçin)

Bu repository, GitHub'dan indirildikten sonra Windows üzerinde lokal olarak kurulup çalıştırılabilecek şekilde hazırlanmıştır.

### 1) Windows + MySQL Workbench / MySQL Server

Ön koşullar:
- Python 3 kurulu olmalıdır.
- MySQL Server 8.x veya MySQL Workbench kurulu olmalıdır.
- MySQL servisinin çalışıyor olması gerekir.

Kurulum:

```bat
kurulum.bat
baslat.bat
```

Kurulum sırasında MySQL yönetici kullanıcısı sorulur. Varsayılan değerler:

```text
MySQL yönetici kullanıcısı: root
MySQL yönetici şifresi: 123
```

Kurulum tamamlanınca:

```text
Ana site : http://127.0.0.1:8001/
Panel    : http://127.0.0.1:8001/yonetim-sistemi/
Giriş    : Nyancat / demo1234
```

`8001` portu başka bir program tarafından kullanılıyorsa `baslat.bat` otomatik olarak `8002-8010` aralığında boş port seçer ve doğru adresi ekrana yazar. Elle port seçmek için:

```bat
set APP_PORT=8020
baslat.bat
```

MySQL Workbench bağlantısı:

```text
Host: 127.0.0.1
Port: 3306
Schema: fitrehber_yonetim_demo
Uygulama kullanıcısı: fitrehber_demo
Uygulama şifresi: FitRehberDemo2026!
```

İstenirse Workbench'e kendi `root` kullanıcınızla da bağlanıp `fitrehber_yonetim_demo` şemasını inceleyebilirsiniz.

### 2) Docker Alternatifi

Docker Desktop kuruluysa:

```bat
docker-kurulum.bat
```

Docker kullanımında uygulama varsayılan olarak `http://127.0.0.1:8001/` adresinden açılır. `8001` doluysa `docker-kurulum.bat` boş port arar veya `APP_PORT` ile elle seçilebilir. MySQL container portu dışarıya `3307` olarak açılır:

```text
Host: 127.0.0.1
Port: 3307
Kullanıcı: root
Şifre: 123
Schema: fitrehber_yonetim_demo
```

### Paketlenen Demo Verisi

`sql/demo_data.sql` dosyası yalnızca ödev demosu için sanitize edilmiş verileri içerir. Session, cache, email confirmation, social login token ve gerçek secret değerleri dahil edilmemiştir. Demo görselleri için seçili `media/` dosyaları repository içinde tutulur.

---

## 1. Ödev Kapsamı (Değerlendirme Sınırı)

Bu repository iki ayrı katmandan oluşur. **Ödev değerlendirmesi yalnızca aşağıdaki "Ödev Modülü" kapsamında yapılacaktır.**

| Katman | Rota | Durum | Açıklama |
|---|---|---|---|
| **Ödev Modülü** | `/yonetim-sistemi/...` | **Değerlendirme kapsamında** | N-Tier mimari · Tüm DB erişimi DAL üzerinden Stored Procedure ile yapılır · ORM/düz SQL yoktur. |
| Mevcut platform altyapısı | `/`, `/forum/`, `/profil/...` vb. | Kapsam dışı | FitRehber ana sitesi; daha önce Django ORM ile geliştirilmiş üretim kodudur, ödev değerlendirmesinde dikkate alınmaz. |

> **Önemli:** Hocanın "Uygulamanın hiçbir katmanında SELECT/INSERT/UPDATE/DELETE gibi SQL komutları doğrudan kullanılmayacaktır" maddesi, ödev olarak teslim edilen `/yonetim-sistemi/` modülü için tam olarak sağlanmıştır. Video sunum, rapor ve ekran görüntüleri tamamen bu modül üzerinden hazırlanmıştır.

---

## 2. Senaryo

**FitRehber İçerik ve Topluluk Yönetim Sistemi**, sağlıklı yaşam / fitness / beslenme konularında haber-blog yazıları ve forum sorularının yönetildiği, kullanıcıların içerik beğenme, kaydetme ve çok seviyeli (parent-child) yorum yapabildiği bir topluluk platformudur. Süper yönetici (`is_superuser=True`) rolündeki kullanıcılar `/yonetim-sistemi/` paneli üzerinden tüm CRUD işlemlerini yürütür.

---

## 3. Mimari (N-Tier)

```
┌─────────────────────────────────────────────────────────────┐
│ Presentation Layer (UI)                                     │
│ posts/views_yonetim.py · posts/templates/yonetim/*.html     │
└──────────────────────────┬──────────────────────────────────┘
                           │  function call
┌──────────────────────────▼──────────────────────────────────┐
│ Business Layer (BL) — posts/bl.py                           │
│ Doğrulama · iş kuralları · trigger hatalarının yakalanması  │
└──────────────────────────┬──────────────────────────────────┘
                           │  function call
┌──────────────────────────▼──────────────────────────────────┐
│ Data Access Layer (DAL) — posts/dal.py                      │
│ Yalnızca  `CALL sp_...`  çağrıları (ORM/düz SQL yok)        │
└──────────────────────────┬──────────────────────────────────┘
                           │  MySQL Stored Procedure
┌──────────────────────────▼──────────────────────────────────┐
│ MySQL — sql/fitrehber_db.sql                                │
│ 8 tablo · 44 Stored Procedure · 3 Function · 8 Trigger      │
└─────────────────────────────────────────────────────────────┘
```

Doğrulama (kanıt):
- `grep "\.objects\." posts/views_yonetim.py` → **0 sonuç**
- `grep "\.objects\." posts/bl.py` → **0 sonuç**
- `grep "\.objects\." posts/dal.py` → **0 sonuç**
- `posts/dal.py` içindeki her DAL fonksiyonu yalnızca `dal.call_sp('sp_...', [...])` çağırır.

---

## 4. Veritabanı Tasarımı (Özet)

### 4.1 Varlıklar (8 tablo)

| # | Tablo | Açıklama |
|---|---|---|
| 1 | `auth_user` | Sisteme kayıtlı kullanıcılar (kimlik doğrulama) |
| 2 | `profiller` | `auth_user` ile 1-1, biyometrik + moderasyon (ban / timeout) |
| 3 | `kategoriler` | İçerik kategorileri |
| 4 | `icerikler` | Haber/blog yazısı (`tur='haber'`) veya forum sorusu (`tur='soru'`) |
| 5 | `yorumlar` | İçeriklere yapılan yorumlar; `parent_id` ile öz-ilişki (cevap zinciri) |
| 6 | `icerik_begenileri` | `auth_user` × `icerikler` N-N junction (UNIQUE: icerik_id, user_id) |
| 7 | `icerik_kaydetmeleri` | `auth_user` × `icerikler` N-N junction (UNIQUE: icerik_id, user_id) |
| 8 | `yorum_begenileri` | `auth_user` × `yorumlar` N-N junction (UNIQUE: yorum_id, user_id) |

### 4.2 Kısıtlar (DDL kanıtı: `sql/fitrehber_db.sql`)

- **PRIMARY KEY:** her tabloda
- **AUTO_INCREMENT (identity):** her tabloda `id`
- **FOREIGN KEY:** 12 adet (cross-table referans bütünlüğü)
- **UNIQUE:** `auth_user.username`, `profiller.user_id`, junction tablolarda çift sütun UNIQUE
- **NOT NULL / NULL:** her sütunda bilinçli ayarlandı
- **DEFAULT:** `profiller.is_banned=0`, `profiller.is_onboarded=0` vb.
- **CHECK:** `profiller.gunluk_su_hedefi_ml >= 0`

### 4.3 İlişkiler

- `auth_user` **1–1** `profiller`
- `auth_user` **1–N** `icerikler` · `yorumlar`
- `kategoriler` **1–N** `icerikler`
- `icerikler` **1–N** `yorumlar`
- `yorumlar` **1–N** `yorumlar` *(öz-ilişki: parent–child cevap zinciri)*
- `auth_user` **N–N** `icerikler` (via `icerik_begenileri` ve `icerik_kaydetmeleri`)
- `auth_user` **N–N** `yorumlar` (via `yorum_begenileri`)

ER diyagramı görseli: `docs/er_diagram.drawio` (diagrams.net'te aç) ve `docs/er_diagram.png`.

---

## 5. Stored Procedure / Function / Trigger Envanteri

| Kategori | Adet | Şart | Durum |
|---|---|---|---|
| Stored Procedure | **44** | 8 tablo için 40 temel CRUD SP + 1 özel ban SP + 1 kullanıcı çakışma kontrol SP + 2 BI raporlama SP | ✅ Karşılıyor |
| User-Defined Function | **3** | En az 2 | ✅ Karşılıyor |
| Trigger | **8** | En az 2 | ✅ Karşılıyor |

**Function listesi:** `fn_IcerikYorumSayisi`, `fn_KullaniciIcerikSayisi`, `fn_IcerikEtkilesimSkoru`
**Trigger listesi:** içerik/yorum eklerken + 3 N-N tabloya ekle/güncellerken `is_active=0`, `is_banned=1` veya `timeout_until > NOW()` durumunu engelleyen 8 BEFORE INSERT/UPDATE trigger'ı.
**BI raporlama SP'leri:** `sp_AylikEtkilesimAnalizi`, `sp_KategoriDagilimiRaporu`

**Tasarım notu:** Junction tablo güncelleme SP'leri normal kullanıcı akışı için değil, yönetim panelinde hatalı ilişki kaydını düzeltmek için tutulmuştur. DELETE işlemleri ise `/yonetim-sistemi/` tarafında `superuser_required` yetkilendirmesiyle korunur.

Tam liste için: [`veritabani_proje_raporu.md`](veritabani_proje_raporu.md) ve [`sql/fitrehber_db.sql`](sql/fitrehber_db.sql).

---

## 6. Manuel Kurulum & Çalıştırma

```bash
# 1) Bağımlılıkları kur
pip install -r requirements.txt

# 2) .env oluştur
# Fresh kurulum için .env.example dosyasını .env olarak kopyalayabilirsiniz.

# 3) Migration'lar (Django framework tabloları için)
python manage.py migrate

# 4) Cache tablosu
python manage.py createcachetable rate_limit_cache_table

# 5) Şema + SP/Function/Trigger kurulumu
mysql -u <user> -p <db_name> < sql/fitrehber_db.sql

# 6) Demo verisi
mysql -u <user> -p <db_name> < sql/demo_data.sql

# 7) Sunucuyu başlat
python manage.py runserver 127.0.0.1:8001

# 8) Tarayıcıdan aç
http://127.0.0.1:8001/yonetim-sistemi/
```

---

## 7. Yönetim Paneli URL Haritası

| Tablo | Liste | Ekle | Düzenle | Sil | Tetiklenen SP |
|---|---|---|---|---|---|
| auth_user | `/yonetim-sistemi/kullanicilar/` | `.../ekle/` | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_Kullanici*` |
| profiller | `/yonetim-sistemi/profiller/` | `.../ekle/` | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_Profil*` |
| kategoriler | `/yonetim-sistemi/kategoriler/` | `.../ekle/` | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_Kategori*` |
| icerikler | `/yonetim-sistemi/icerikler/` | `.../ekle/` | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_Icerik*` |
| yorumlar | `/yonetim-sistemi/yorumlar/` | `.../ekle/` | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_Yorum*` |
| icerik_begenileri | `/yonetim-sistemi/icerik-begenileri/` | (liste sayfasında) | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_IcerikBegeni*` |
| icerik_kaydetmeleri | `/yonetim-sistemi/icerik-kaydetmeleri/` | (liste sayfasında) | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_IcerikKaydetme*` |
| yorum_begenileri | `/yonetim-sistemi/yorum-begenileri/` | (liste sayfasında) | `.../duzenle/<id>/` | `.../sil/<id>/` | `sp_YorumBegeni*` |

---

## 8. Teslim Dosyaları

- 📄 [`veritabani_proje_raporu.md`](veritabani_proje_raporu.md) — Detaylı ödev raporu (senaryo · ER · DDL · SP/Function/Trigger · N-Tier mimari).
- 🗂️ [`sql/fitrehber_db.sql`](sql/fitrehber_db.sql) — Çalıştırılabilir tek dosyalık DDL + SP + Function + Trigger betiği.
- 🗃️ [`sql/demo_data.sql`](sql/demo_data.sql) — Sanitize edilmiş demo verisi.
- 🎨 `docs/er_diagram.drawio` — diagrams.net görsel ER diyagramı (XML).
- ⚙️ `kurulum.bat`, `baslat.bat`, `docker-kurulum.bat` — Fresh-install kurulum ve çalıştırma yardımcıları.
- 🎥 Sunum videosu (link rapora eklenecek).

---

## 9. Demo / Sunum Sırası (Video Senaryosu)

1. `http://.../yonetim-sistemi/` → superuser ile login → Dashboard ekranı (8 tablo sayacı görünür).
2. **Kategori CRUD:** ekle → düzenle → listele → sil.
3. **Kullanıcı CRUD:** ekle → düzenle → sil.
4. **İçerik ekle**, ardından MySQL Workbench'te `CALL sp_IcerikEkle(...)` çağrısının log'unu göster.
5. **Trigger demosu:** önce bir kullanıcıyı banla (`Profil → Ban`), sonra o kullanıcı adına içerik eklemeyi dene → trigger `SIGNAL SQLSTATE '45000'` ile engeller, BL friendly mesaja çevirir.
6. **Function demosu:** Workbench'te `SELECT fn_IcerikEtkilesimSkoru(<icerik_id>)` çağrısını göster.
7. Yorum / Beğeni / Kaydetme tablolarında benzer CRUD gösterimi.
