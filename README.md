# FitRehber Yönetim Sistemi

**BTS304 – Veritabanı Yönetim Sistemleri II / Final Sınavına Ek Ödev**
Bartın Üniversitesi · Fen Fakültesi · Bilgisayar Teknolojisi ve Bilişim Sistemleri Bölümü
Öğretim Elemanı: Dr. Öğr. Üyesi Bayram AKGÜL

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
│ 8 tablo · 41 Stored Procedure · 3 Function · 8 Trigger      │
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
| Stored Procedure | **41** | 8 tablo için 40 temel CRUD SP + 1 özel ban SP | ✅ Karşılıyor |
| User-Defined Function | **3** | En az 2 | ✅ Karşılıyor |
| Trigger | **8** | En az 2 | ✅ Karşılıyor |

**Function listesi:** `fn_IcerikYorumSayisi`, `fn_KullaniciIcerikSayisi`, `fn_IcerikEtkilesimSkoru`
**Trigger listesi:** içerik/yorum eklerken + 3 N-N tabloya ekle/güncellerken `is_active=0`, `is_banned=1` veya `timeout_until > NOW()` durumunu engelleyen 8 BEFORE INSERT/UPDATE trigger'ı.

Tam liste için: [`veritabani_proje_raporu.md`](veritabani_proje_raporu.md) ve [`sql/fitrehber_db.sql`](sql/fitrehber_db.sql).

---

## 6. Kurulum & Çalıştırma

```bash
# 1) Bağımlılıkları kur
pip install -r requirements.txt

# 2) .env oluştur (DB_HOST, DB_NAME, DB_USER, DB_PASS, SECRET_KEY)

# 3) Şema + SP/Function/Trigger kurulumu
mysql -u <user> -p <db_name> < sql/fitrehber_db.sql

# 4) Migration'lar (Django framework tabloları için)
python manage.py migrate

# 5) Superuser oluştur
python manage.py createsuperuser

# 6) Sunucuyu başlat
python manage.py runserver

# 7) Tarayıcıdan aç
http://127.0.0.1:8000/yonetim-sistemi/
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
- 🎨 `docs/er_diagram.drawio` — diagrams.net görsel ER diyagramı (XML).
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
