# FitRehber İçerik ve Topluluk Yönetim Sistemi — Proje Raporu

**Ders:** BTS304 – Veritabanı Yönetim Sistemleri II
**Ödev:** Final Sınavına Ek Ödev (2025–2026 Bahar)
**Öğretim Elemanı:** Dr. Öğr. Üyesi Bayram AKGÜL
**Hazırlayan:** *Baran Atıcı – 22010708007*
**Bartın Üniversitesi · Fen Fakültesi · Bilgisayar Teknolojisi ve Bilişim Sistemleri Bölümü*

---

## Ödev Kapsamı (Önemli)

Bu rapor, **`/yonetim-sistemi/`** rotası altında çalışan N-Tier yönetim panelini değerlendirme konusu olarak ele alır. Aynı repository içinde yer alan FitRehber ana sitesi (`/`, `/forum/`, `/profil/` vb.) mevcut bir platform altyapısıdır ve ödev değerlendirmesi dışındadır. Hocanın "hiçbir katmanda doğrudan SQL kullanılmayacak" maddesi, ödev olarak teslim edilen yönetim paneli içerisinde tam olarak sağlanmıştır.

---

## ADIM-1 — Senaryo (5 puan)

**FitRehber İçerik ve Topluluk Yönetim Sistemi**, sağlıklı yaşam · fitness · beslenme · supplement konularında üretilen içerikleri, bu içeriklere ilişkin yorum/beğeni/kaydetme etkileşimlerini ve sistem kullanıcılarını yönetmek üzere geliştirilmiş çok katmanlı (N-Tier) bir uygulamadır.

Sistemde üç temel kullanıcı türü vardır:

1. **Süper Yönetici (Superuser):** `/yonetim-sistemi/` paneline erişebilen tek roldür. Sekiz tablonun tamamı için CRUD işlemlerini gerçekleştirir, kullanıcıları banlar, içerikleri moderasyona alır.
2. **Kayıtlı kullanıcı:** İçerik üretir, yorum yapar, beğenir ve kaydeder. Bu kullanıcıların etkileşimleri ödev kapsamı içindeki tablolara yansır.
3. **Pasif/Banlanmış kullanıcı:** Trigger'lar sayesinde içerik ekleme, yorum yapma, beğenme veya kaydetme eylemlerinden veritabanı seviyesinde engellenir.

**İş kuralları:**

- Bir kullanıcı pasif (`is_active=0`), banlı (`is_banned=1`) veya zaman aşımı (timeout) altındaysa içerik / yorum ekleyemez, beğeni veya kaydetme işlemi yapamaz. Bu kural uygulama katmanında değil, **doğrudan veritabanı trigger'larında** zorlanır.
- Bir kullanıcı aynı içeriği iki kez beğenemez / kaydedemez (UNIQUE composite key).
- Bir yorum, başka bir yoruma cevap olabilir (öz-ilişki). `depth` alanı cevap zincirinin derinliğini tutar.
- Bir içeriğin "etkileşim skoru" `(yorum × 2) + beğeni + kaydetme` formülüyle veritabanı içinde bir function tarafından hesaplanır.

---

## ADIM-2 — Varlıklar, Nitelikler, İlişkiler, ER Diagramı (20 puan)

### 2.1 Varlıklar (Entity) ve Nitelikleri (Attribute)

#### `auth_user` — Kullanıcılar
| Alan | Tip | Kısıt | Açıklama |
|---|---|---|---|
| **id** | INT | PK, AUTO_INCREMENT | Birincil anahtar |
| username | VARCHAR(150) | NOT NULL, UNIQUE | Kullanıcı adı |
| email | VARCHAR(254) | NOT NULL | E-posta |
| password | VARCHAR(128) | NOT NULL | Hashli şifre |
| first_name, last_name | VARCHAR(150) | NOT NULL | Ad-soyad |
| is_active, is_staff, is_superuser | TINYINT(1) | NOT NULL | Yetki bayrakları |
| last_login | DATETIME(6) | NULL | Son giriş |
| date_joined | DATETIME(6) | NOT NULL | Kayıt tarihi |

#### `profiller` — Kullanıcı Profilleri (1-1 `auth_user`)
| Alan | Tip | Kısıt | Açıklama |
|---|---|---|---|
| **id** | BIGINT | PK, AUTO_INCREMENT | |
| user_id | INT | FK→auth_user.id, UNIQUE, NOT NULL | 1-1 bağ |
| hakkinda | LONGTEXT | NOT NULL | Biyografi |
| foto | VARCHAR(100) | NULL | Profil fotoğrafı yolu |
| cinsiyet | VARCHAR(1) | NOT NULL | 'E' / 'K' / 'B' |
| boy | DECIMAL(5,1) | NULL | cm |
| kilo, hedef_kilo, baslangic_kilo | DECIMAL(5,1) | NULL | kg |
| fitness_hedefi | VARCHAR(200) | NOT NULL | |
| dogum_tarihi | DATE | NULL | |
| is_onboarded | TINYINT(1) | NOT NULL, DEFAULT 0 | Onboarding tamamlandı mı |
| gunluk_su_hedefi_ml | INT UNSIGNED | NULL, CHECK ≥ 0 | |
| is_banned | TINYINT(1) | NOT NULL, DEFAULT 0 | Moderasyon |
| timeout_until | DATETIME(6) | NULL | Geçici susturma sonu |

#### `kategoriler`
| Alan | Tip | Kısıt |
|---|---|---|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| isim | VARCHAR(100) | NOT NULL |

#### `icerikler`
| Alan | Tip | Kısıt |
|---|---|---|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| baslik | VARCHAR(200) | NOT NULL |
| yazi | LONGTEXT | NOT NULL |
| resim | VARCHAR(100) | NULL |
| tur | VARCHAR(10) | NOT NULL — 'haber' veya 'soru' |
| tarih | DATETIME(6) | NOT NULL |
| yazar_id | INT | FK→auth_user.id, NOT NULL |
| kategori_id | BIGINT | FK→kategoriler.id, NULL |

#### `yorumlar` (öz-ilişki: parent-child)
| Alan | Tip | Kısıt |
|---|---|---|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| mesaj | LONGTEXT | NOT NULL |
| tarih | DATETIME(6) | NOT NULL |
| icerik_id | BIGINT | FK→icerikler.id, NOT NULL |
| yazar_id | INT | FK→auth_user.id, NOT NULL |
| parent_id | BIGINT | FK→yorumlar.id, NULL (öz-ilişki) |
| depth | INT | NOT NULL |

#### `icerik_begenileri` (N-N junction)
| Alan | Tip | Kısıt |
|---|---|---|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| icerik_id | BIGINT | FK→icerikler.id, NOT NULL |
| user_id | INT | FK→auth_user.id, NOT NULL |
| | | **UNIQUE (icerik_id, user_id)** — aynı içerik iki kez beğenilemez |

#### `icerik_kaydetmeleri` (N-N junction)
Yapı `icerik_begenileri` ile aynı; **UNIQUE (icerik_id, user_id)**.

#### `yorum_begenileri` (N-N junction)
| Alan | Tip | Kısıt |
|---|---|---|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| yorum_id | BIGINT | FK→yorumlar.id, NOT NULL |
| user_id | INT | FK→auth_user.id, NOT NULL |
| | | **UNIQUE (yorum_id, user_id)** |

### 2.2 İlişkiler

| Tip | Sol | Sağ | Açıklama |
|---|---|---|---|
| **1–1** | auth_user | profiller | Her kullanıcının tek profili (`user_id` UNIQUE) |
| **1–N** | auth_user | icerikler | Bir kullanıcı çok içerik yazar |
| **1–N** | auth_user | yorumlar | Bir kullanıcı çok yorum yazar |
| **1–N** | kategoriler | icerikler | Bir kategoride çok içerik |
| **1–N** | icerikler | yorumlar | Bir içerikte çok yorum |
| **1–N** | yorumlar | yorumlar | Cevap zinciri (öz-ilişki, `parent_id`) |
| **N–N** | auth_user | icerikler | `icerik_begenileri` junction üzerinden |
| **N–N** | auth_user | icerikler | `icerik_kaydetmeleri` junction üzerinden |
| **N–N** | auth_user | yorumlar | `yorum_begenileri` junction üzerinden |

### 2.3 ER Diyagramı

Görsel ER diyagramı `docs/er_diagram.drawio` dosyasındadır. [app.diagrams.net](https://app.diagrams.net/) üzerinden **File → Open from → Device** ile açılabilir; PNG/SVG olarak rapora gömülmüştür.

### 2.4 İlişkisel Şema (PK altı çizili, FK '+' ile gösterilmiştir)

```
auth_user              = {id, username, email, password, first_name, last_name,
                          is_active, is_staff, is_superuser, last_login, date_joined}
profiller              = {id, +user_id, hakkinda, foto, cinsiyet, boy, kilo,
                          hedef_kilo, baslangic_kilo, fitness_hedefi, dogum_tarihi,
                          is_onboarded, gunluk_su_hedefi_ml, is_banned, timeout_until}
kategoriler            = {id, isim}
icerikler              = {id, baslik, yazi, resim, tur, tarih, +yazar_id, +kategori_id}
yorumlar               = {id, mesaj, tarih, +icerik_id, +yazar_id, +parent_id, depth}
icerik_begenileri      = {id, +icerik_id, +user_id}      -- UNIQUE(icerik_id, user_id)
icerik_kaydetmeleri    = {id, +icerik_id, +user_id}      -- UNIQUE(icerik_id, user_id)
yorum_begenileri       = {id, +yorum_id, +user_id}       -- UNIQUE(yorum_id, user_id)
```

---

## ADIM-3 — Fiziksel Tasarım (MySQL)

### 3.1 Tablo Oluşturma (20 puan)

DDL tek dosyada toplanmıştır: [`sql/fitrehber_db.sql`](sql/fitrehber_db.sql). Şartların karşılanışı:

| Kısıt | Nerede |
|---|---|
| **PRIMARY KEY** | 8 tablonun her birinde `id` |
| **AUTO_INCREMENT (identity)** | Tüm `id` sütunlarında |
| **FOREIGN KEY** | 12 adet (profiller×1, icerikler×2, yorumlar×3, 3 junction tablo×2) |
| **UNIQUE** | `auth_user.username`, `profiller.user_id`, 3 junction'da composite (`icerik_id+user_id` / `yorum_id+user_id`) |
| **NULL / NOT NULL** | Her sütunda bilinçli; opsiyonel alanlar (foto, boy, kilo vb.) NULL |
| **DEFAULT** | `profiller.is_banned=0`, `profiller.is_onboarded=0` |
| **CHECK** | `profiller.gunluk_su_hedefi_ml >= 0` |
| **ENGINE / CHARSET** | InnoDB · utf8mb4 · utf8mb4_unicode_ci |

### 3.2 Stored Procedure'lar (10 puan)

**Her tablo için Listele / Bul / Ekle / Güncelle / Sil olmak üzere 40 temel CRUD SP ve `sp_ProfilBanGuncelle` özel aksiyonu ile toplam 41 SP:**

| Tablo | SP'ler |
|---|---|
| auth_user | `sp_KullaniciListele`, `sp_KullaniciBul`, `sp_KullaniciEkle`, `sp_KullaniciGuncelle`, `sp_KullaniciSil` |
| profiller | `sp_ProfilListele`, `sp_ProfilBul`, `sp_ProfilEkle`, `sp_ProfilGuncelle`, `sp_ProfilSil`, `sp_ProfilBanGuncelle` *(+ban hızlı aksiyonu)* |
| kategoriler | `sp_KategoriListele`, `sp_KategoriBul`, `sp_KategoriEkle`, `sp_KategoriGuncelle`, `sp_KategoriSil` |
| icerikler | `sp_IcerikListele`, `sp_IcerikBul`, `sp_IcerikEkle`, `sp_IcerikGuncelle`, `sp_IcerikSil` |
| yorumlar | `sp_YorumListele`, `sp_YorumBul`, `sp_YorumEkle`, `sp_YorumGuncelle`, `sp_YorumSil` |
| icerik_begenileri | `sp_IcerikBegeniListele`, `sp_IcerikBegeniBul`, `sp_IcerikBegeniEkle`, `sp_IcerikBegeniGuncelle`, `sp_IcerikBegeniSil` |
| icerik_kaydetmeleri | `sp_IcerikKaydetmeListele`, `sp_IcerikKaydetmeBul`, `sp_IcerikKaydetmeEkle`, `sp_IcerikKaydetmeGuncelle`, `sp_IcerikKaydetmeSil` |
| yorum_begenileri | `sp_YorumBegeniListele`, `sp_YorumBegeniBul`, `sp_YorumBegeniEkle`, `sp_YorumBegeniGuncelle`, `sp_YorumBegeniSil` |

Listeleme SP'leri JOIN ile zenginleştirilmiş, içerik listesi yazar adını ve kategori adını, yorum listesi içerik başlığını da döndürür. Kullanıcı listesi ayrıca `fn_KullaniciIcerikSayisi()` fonksiyonunu çağırarak kullanıcı başına içerik sayısını hesaplar.

### 3.3 Kullanıcı Tanımlı Fonksiyonlar (5 puan)

| Fonksiyon | Görev |
|---|---|
| `fn_IcerikYorumSayisi(p_icerik_id)` | Bir içeriğin toplam yorum sayısını döner |
| `fn_KullaniciIcerikSayisi(p_user_id)` | Bir kullanıcının ürettiği içerik sayısını döner |
| `fn_IcerikEtkilesimSkoru(p_icerik_id)` | `(yorum*2) + beğeni + kaydetme` formülüyle etkileşim skoru |

Şart "en az 2"; **3** adet ile sağlanır.

### 3.4 Tetikleyiciler (Trigger) — 5 puan

| Trigger | Çalıştığı Olay | Engellediği Eylem |
|---|---|---|
| `tg_icerik_ekle_engelle` | BEFORE INSERT ON `icerikler` | Pasif/banlı/timeout'lu kullanıcı içerik ekleyemez |
| `tg_yorum_ekle_engelle` | BEFORE INSERT ON `yorumlar` | Aynı kullanıcı yorum yapamaz |
| `tg_icerik_begeni_ekle_engelle` | BEFORE INSERT ON `icerik_begenileri` | İçerik beğenisi engellenir |
| `tg_icerik_begeni_guncelle_engelle` | BEFORE UPDATE ON `icerik_begenileri` | Sahteleme/güncelleme engellenir |
| `tg_icerik_kaydetme_ekle_engelle` | BEFORE INSERT ON `icerik_kaydetmeleri` | Kaydetme engellenir |
| `tg_icerik_kaydetme_guncelle_engelle` | BEFORE UPDATE ON `icerik_kaydetmeleri` | Güncelleme engellenir |
| `tg_yorum_begeni_ekle_engelle` | BEFORE INSERT ON `yorum_begenileri` | Yorum beğenisi engellenir |
| `tg_yorum_begeni_guncelle_engelle` | BEFORE UPDATE ON `yorum_begenileri` | Güncelleme engellenir |

Şart "en az 2"; **8** adet ile sağlanır. Tüm trigger'lar `SIGNAL SQLSTATE '45000'` ile hata fırlatır; BL katmanı bu hatayı yakalayıp `ValidationError` ile kullanıcıya gösterir.

---

## ADIM-4 — Uygulama Geliştirme (N-Tier Mimari) — 35 puan

Uygulama Django framework'ü altında **3 katmanlı N-Tier** yapıda geliştirilmiştir:

### 4.1 Presentation Layer (Sunum / UI)

**Dosyalar:** [`posts/views_yonetim.py`](posts/views_yonetim.py) + [`posts/templates/yonetim/*.html`](posts/templates/yonetim/)

- `@superuser_required` dekoratörü ile yetki kontrolü
- Tüm CRUD form ekranları + dashboard
- Hiçbir veritabanı çağrısı içermez; yalnızca `from posts import bl` ile BL'ye delege eder.

**Doğrulama:** `grep "\.objects\." posts/views_yonetim.py` → **0 sonuç**

### 4.2 Business Layer (İş Mantığı)

**Dosya:** [`posts/bl.py`](posts/bl.py)

- Girdi doğrulamaları (e-posta regex, parola uzunluğu, boş alan, benzersizlik vb.)
- Trigger'ın fırlattığı `OperationalError`'u yakalayıp kullanıcı dostu `ValidationError`'a çevirir
- DAL'a yalnızca temizlenmiş ve doğrulanmış parametreleri iletir.

**Doğrulama:** `grep "\.objects\." posts/bl.py` → **0 sonuç**

### 4.3 Data Access Layer (DAL)

**Dosya:** [`posts/dal.py`](posts/dal.py)

```python
def call_sp(proc_name, params=None):
    params = params or []
    placeholders = ', '.join(['%s'] * len(params))
    sql = f"CALL {proc_name}({placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _dict_fetchall(cursor)
```

DAL'da **tek SQL ifadesi** `CALL sp_...`'tır. Düz SELECT/INSERT/UPDATE/DELETE veya Django ORM kullanımı yoktur.

**Doğrulama:** `grep "\.objects\." posts/dal.py` → **0 sonuç**
**Doğrulama:** `grep -E "INSERT|UPDATE|DELETE|SELECT " posts/dal.py` → **0 sonuç** (sadece `CALL` var)

### 4.4 Akış (örnek: Kategori Ekleme)

```
Kullanıcı → /yonetim-sistemi/kategoriler/ekle/ (POST)
   ↓
views_yonetim.kategori_ekle()       [Presentation]
   ↓ bl.add_category("Beslenme")
bl.add_category()                    [Business — boş mu? benzersiz mi?]
   ↓ dal.create_category("Beslenme")
dal.create_category()                [Data Access — CALL sp_KategoriEkle(%s)]
   ↓
MySQL: sp_KategoriEkle → INSERT INTO kategoriler ...
   ↓
LAST_INSERT_ID() → BL → View → redirect + success message
```

---

## ADIM-5 — Video Sunum (5–10 dakika)

Video aşağıdaki sırayı izler:

1. Login → `/yonetim-sistemi/` dashboard'u (8 sayaç).
2. Her tabloda **Liste / Ekle / Düzenle / Sil** ekranlarının çalıştığının gösterilmesi.
3. MySQL Workbench'te paralel pencere açılarak `SHOW PROCEDURE STATUS` ve örnek `CALL sp_KategoriListele()` ile arka plandaki çalışan SP'lerin sergilenmesi.
4. **Trigger demosu:** Kullanıcı banlanır → o kullanıcıyla içerik eklenmeye çalışılır → trigger `SIGNAL` ile reddeder → BL bunu friendly mesaja çevirir.
5. **Function demosu:** Workbench'te `SELECT fn_IcerikEtkilesimSkoru(<id>)` çağrılarak hesaplanan skorun döndüğü gösterilir.
6. Kapanış: GitHub repository linki ekrana getirilir.

**Video Linki:** *Video henüz hazırlanmadı; teslim öncesinde YouTube/Drive linki eklenecektir.*

---

## Teslim Dosyaları

| Dosya | İçerik |
|---|---|
| [`README.md`](README.md) | Kısa proje tanıtımı + kurulum + ödev kapsam beyanı |
| [`veritabani_proje_raporu.md`](veritabani_proje_raporu.md) | Bu dosya (detaylı rapor) |
| [`sql/fitrehber_db.sql`](sql/fitrehber_db.sql) | Çalıştırılabilir DDL + 41 SP + 3 Function + 8 Trigger |
| `docs/er_diagram.drawio` | diagrams.net görsel ER diyagramı (XML) |
| `docs/er_diagram.png` | ER diyagramı PNG çıktısı (diagrams.net'ten export) |

**GitHub Repository:** [NyancatGo/FitRehber-Yonetim-Sistemi](https://github.com/NyancatGo/FitRehber-Yonetim-Sistemi.git)
