import re

from django.db import connection

# DAL katmanı yalnızca stored procedure ve function çağırır.
# İsim doğrulaması, dinamik CALL/SELECT kullanımında ek güvenlik sağlar.
_SP_NAME_RE = re.compile(r'^sp_[A-Za-z_][A-Za-z0-9_]*$')
_FN_NAME_RE = re.compile(r'^fn_[A-Za-z_][A-Za-z0-9_]*$')


def _dict_fetchall(cursor):
    """Cursor sonuçlarını sözlük listesi olarak döndürür."""
    if cursor.description is None:
        return None
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def call_sp(proc_name, params=None):
    """
    Belirtilen saklı yordamı (Stored Procedure) çağırır.

    Güvenlik: proc_name regex ile doğrulanır, parametreler
    %s placeholder üzerinden PyMySQL tarafından escape edilir.
    Yönetim panelinde doğrudan CRUD SQL yazılmamasını bu yardımcı sağlar.
    """
    if not _SP_NAME_RE.match(proc_name):
        raise ValueError(f"Geçersiz stored procedure adı: {proc_name!r}")

    params = params or []
    placeholders = ', '.join(['%s'] * len(params))
    sql = f"CALL {proc_name}({placeholders})"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _dict_fetchall(cursor)


def call_fn(fn_name, params=None):
    """
    Belirtilen kullanıcı tanımlı MySQL function'ı çağırır.
    Dönüş: tek skaler değer.

    Örnek:
        skor = call_fn('fn_IcerikEtkilesimSkoru', [icerik_id])
    """
    if not _FN_NAME_RE.match(fn_name):
        raise ValueError(f"Geçersiz function adı: {fn_name!r}")

    params = params or []
    placeholders = ', '.join(['%s'] * len(params))
    sql = f"SELECT {fn_name}({placeholders}) AS sonuc"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else None


# Kullanıcı tanımlı function çağrıları

def get_icerik_yorum_sayisi(icerik_id):
    """Bir içeriğe yapılmış yorum sayısını döndürür (fn_IcerikYorumSayisi)."""
    return call_fn('fn_IcerikYorumSayisi', [icerik_id])


def get_kullanici_icerik_sayisi(user_id):
    """Bir kullanıcının ürettiği içerik sayısını döndürür (fn_KullaniciIcerikSayisi)."""
    return call_fn('fn_KullaniciIcerikSayisi', [user_id])


def get_icerik_etkilesim_skoru(icerik_id):
    """
    Bir içeriğin etkileşim skorunu döndürür (fn_IcerikEtkilesimSkoru).
    Skor = (yorum * 2) + begeni + kaydetme
    """
    return call_fn('fn_IcerikEtkilesimSkoru', [icerik_id])

# 1. KULLANICI DAL METOTLARI (auth_user)

def list_users():
    """Tüm kullanıcıları listeler (sp_KullaniciListele)."""
    return call_sp('sp_KullaniciListele')

def get_user(user_id):
    """Belirli bir kullanıcıyı bulur (sp_KullaniciBul)."""
    results = call_sp('sp_KullaniciBul', [user_id])
    return results[0] if results else None

def check_user_conflict(username, email, exclude_id=None):
    """Kullanıcı adı/e-posta çakışmasını SP üzerinden denetler."""
    results = call_sp('sp_KullaniciCakismaKontrol', [username, email, exclude_id])
    return results[0] if results else {"username_var_mi": 0, "email_var_mi": 0}

def create_user(username, email, password, first_name, last_name, is_active, is_staff, is_superuser):
    """Yeni kullanıcı ekler (sp_KullaniciEkle)."""
    results = call_sp('sp_KullaniciEkle', [
        username, email, password, first_name, last_name,
        int(is_active), int(is_staff), int(is_superuser)
    ])
    return results[0]['id'] if results else None

def update_user(user_id, username, email, first_name, last_name, is_active, is_staff, is_superuser):
    """Kullanıcıyı günceller (sp_KullaniciGuncelle)."""
    call_sp('sp_KullaniciGuncelle', [
        user_id, username, email, first_name, last_name,
        int(is_active), int(is_staff), int(is_superuser)
    ])

def delete_user(user_id):
    """Kullanıcıyı siler (sp_KullaniciSil)."""
    call_sp('sp_KullaniciSil', [user_id])


# 2. KATEGORİ DAL METOTLARI (kategoriler)

def list_categories():
    """Tüm kategorileri listeler (sp_KategoriListele)."""
    return call_sp('sp_KategoriListele')

def get_category(kategori_id):
    """Belirli bir kategoriyi bulur (sp_KategoriBul)."""
    results = call_sp('sp_KategoriBul', [kategori_id])
    return results[0] if results else None

def create_category(isim):
    """Yeni kategori ekler (sp_KategoriEkle)."""
    results = call_sp('sp_KategoriEkle', [isim])
    return results[0]['id'] if results else None

def update_category(kategori_id, isim):
    """Kategoriyi günceller (sp_KategoriGuncelle)."""
    call_sp('sp_KategoriGuncelle', [kategori_id, isim])

def delete_category(kategori_id):
    """Kategoriyi siler (sp_KategoriSil)."""
    call_sp('sp_KategoriSil', [kategori_id])


# 3. İÇERİK DAL METOTLARI (icerikler)

def list_contents():
    """Tüm içerikleri listeler (sp_IcerikListele)."""
    return call_sp('sp_IcerikListele')

def get_content(content_id):
    """Belirli bir içeriği bulur (sp_IcerikBul)."""
    results = call_sp('sp_IcerikBul', [content_id])
    return results[0] if results else None

def create_content(baslik, yazi, resim, yazar_id, kategori_id, tur):
    """Yeni içerik ekler (sp_IcerikEkle)."""
    results = call_sp('sp_IcerikEkle', [
        baslik, yazi, resim or '', yazar_id, kategori_id, tur
    ])
    return results[0]['id'] if results else None

def update_content(content_id, baslik, yazi, resim, kategori_id, tur):
    """İçeriği günceller (sp_IcerikGuncelle)."""
    call_sp('sp_IcerikGuncelle', [
        content_id, baslik, yazi, resim or '', kategori_id, tur
    ])

def delete_content(content_id):
    """İçeriği siler (sp_IcerikSil)."""
    call_sp('sp_IcerikSil', [content_id])


# 4. YORUM DAL METOTLARI (yorumlar)

def list_comments():
    """Tüm yorumları listeler (sp_YorumListele)."""
    return call_sp('sp_YorumListele')

def get_comment(comment_id):
    """Belirli bir yorumu bulur (sp_YorumBul)."""
    results = call_sp('sp_YorumBul', [comment_id])
    return results[0] if results else None

def create_comment(icerik_id, yazar_id, parent_id, depth, mesaj):
    """Yeni yorum ekler (sp_YorumEkle)."""
    results = call_sp('sp_YorumEkle', [
        icerik_id, yazar_id, parent_id, depth, mesaj
    ])
    return results[0]['id'] if results else None

def update_comment(comment_id, mesaj):
    """Yorumu günceller (sp_YorumGuncelle)."""
    call_sp('sp_YorumGuncelle', [comment_id, mesaj])

def delete_comment(comment_id):
    """Yorumu siler (sp_YorumSil)."""
    call_sp('sp_YorumSil', [comment_id])


# 5. PROFİL DAL METOTLARI (profiller)

def list_profiles():
    """Tüm profilleri listeler (sp_ProfilListele)."""
    return call_sp('sp_ProfilListele')

def get_profile(profil_id):
    """Belirli bir profili bulur (sp_ProfilBul)."""
    results = call_sp('sp_ProfilBul', [profil_id])
    return results[0] if results else None

def create_profile(user_id, foto, hakkinda, cinsiyet, boy, kilo,
                   hedef_kilo, baslangic_kilo, fitness_hedefi,
                   dogum_tarihi, is_onboarded, gunluk_su_hedefi_ml,
                   is_banned, timeout_until):
    """Yeni profil ekler (sp_ProfilEkle)."""
    results = call_sp('sp_ProfilEkle', [
        user_id, foto, hakkinda, cinsiyet, boy, kilo,
        hedef_kilo, baslangic_kilo, fitness_hedefi,
        dogum_tarihi, is_onboarded, gunluk_su_hedefi_ml,
        is_banned, timeout_until,
    ])
    return results[0]['id'] if results else None

def update_profile(profil_id, foto, hakkinda, cinsiyet, boy, kilo,
                   hedef_kilo, baslangic_kilo, fitness_hedefi,
                   dogum_tarihi, is_onboarded, gunluk_su_hedefi_ml,
                   is_banned, timeout_until):
    """Profili günceller (sp_ProfilGuncelle)."""
    call_sp('sp_ProfilGuncelle', [
        profil_id, foto, hakkinda, cinsiyet, boy, kilo,
        hedef_kilo, baslangic_kilo, fitness_hedefi,
        dogum_tarihi, is_onboarded, gunluk_su_hedefi_ml,
        is_banned, timeout_until,
    ])

def delete_profile(profil_id):
    """Profili siler (sp_ProfilSil)."""
    call_sp('sp_ProfilSil', [profil_id])

def set_profile_ban(profil_id, is_banned, timeout_until=None):
    """Ban/unban hızlı aksiyon (sp_ProfilBanGuncelle)."""
    call_sp('sp_ProfilBanGuncelle', [profil_id, int(is_banned), timeout_until])


# 6. İÇERİK BEĞENİ DAL METOTLARI (icerik_begenileri)

def list_icerik_begenileri():
    """Tüm içerik beğenilerini listeler (sp_IcerikBegeniListele)."""
    return call_sp('sp_IcerikBegeniListele')

def get_icerik_begeni(begeni_id):
    """Belirli bir içerik beğenisini bulur (sp_IcerikBegeniBul)."""
    results = call_sp('sp_IcerikBegeniBul', [begeni_id])
    return results[0] if results else None

def create_icerik_begeni(icerik_id, user_id):
    """İçerik beğenisi ekler (sp_IcerikBegeniEkle)."""
    results = call_sp('sp_IcerikBegeniEkle', [icerik_id, user_id])
    return results[0]['id'] if results else None

def update_icerik_begeni(begeni_id, icerik_id, user_id):
    """İçerik beğenisini günceller (sp_IcerikBegeniGuncelle)."""
    call_sp('sp_IcerikBegeniGuncelle', [begeni_id, icerik_id, user_id])

def delete_icerik_begeni(begeni_id):
    """İçerik beğenisini siler (sp_IcerikBegeniSil)."""
    call_sp('sp_IcerikBegeniSil', [begeni_id])


# 7. İÇERİK KAYDETME DAL METOTLARI (icerik_kaydetmeleri)

def list_icerik_kaydetmeleri():
    """Tüm içerik kaydetmelerini listeler (sp_IcerikKaydetmeListele)."""
    return call_sp('sp_IcerikKaydetmeListele')

def get_icerik_kaydetme(kaydetme_id):
    """Belirli bir kaydetmeyi bulur (sp_IcerikKaydetmeBul)."""
    results = call_sp('sp_IcerikKaydetmeBul', [kaydetme_id])
    return results[0] if results else None

def create_icerik_kaydetme(icerik_id, user_id):
    """İçerik kaydetmesi ekler (sp_IcerikKaydetmeEkle)."""
    results = call_sp('sp_IcerikKaydetmeEkle', [icerik_id, user_id])
    return results[0]['id'] if results else None

def update_icerik_kaydetme(kaydetme_id, icerik_id, user_id):
    """İçerik kaydetmesini günceller (sp_IcerikKaydetmeGuncelle)."""
    call_sp('sp_IcerikKaydetmeGuncelle', [kaydetme_id, icerik_id, user_id])

def delete_icerik_kaydetme(kaydetme_id):
    """İçerik kaydetmesini siler (sp_IcerikKaydetmeSil)."""
    call_sp('sp_IcerikKaydetmeSil', [kaydetme_id])


# 8. YORUM BEĞENİ DAL METOTLARI (yorum_begenileri)

def list_yorum_begenileri():
    """Tüm yorum beğenilerini listeler (sp_YorumBegeniListele)."""
    return call_sp('sp_YorumBegeniListele')

def get_yorum_begeni(begeni_id):
    """Belirli bir yorum beğenisini bulur (sp_YorumBegeniBul)."""
    results = call_sp('sp_YorumBegeniBul', [begeni_id])
    return results[0] if results else None

def create_yorum_begeni(yorum_id, user_id):
    """Yorum beğenisi ekler (sp_YorumBegeniEkle)."""
    results = call_sp('sp_YorumBegeniEkle', [yorum_id, user_id])
    return results[0]['id'] if results else None

def update_yorum_begeni(begeni_id, yorum_id, user_id):
    """Yorum beğenisini günceller (sp_YorumBegeniGuncelle)."""
    call_sp('sp_YorumBegeniGuncelle', [begeni_id, yorum_id, user_id])

def delete_yorum_begeni(begeni_id):
    """Yorum beğenisini siler (sp_YorumBegeniSil)."""
    call_sp('sp_YorumBegeniSil', [begeni_id])


# 9. RAPORLAMA / ANALİTİK DAL METOTLARI

def get_monthly_interaction_analysis():
    """Son 6 aylık etkileşim özetini getirir (sp_AylikEtkilesimAnalizi)."""
    return call_sp('sp_AylikEtkilesimAnalizi')

def get_category_distribution_report():
    """Kategori bazlı içerik dağılımını getirir (sp_KategoriDagilimiRaporu)."""
    return call_sp('sp_KategoriDagilimiRaporu')
