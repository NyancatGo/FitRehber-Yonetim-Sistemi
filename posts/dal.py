from django.db import connection

def _dict_fetchall(cursor):
    """Cursor sonuÃ§larÄ±nÄ± sÃ¶zlÃ¼k listesi olarak dÃ¶ndÃ¼rÃ¼r."""
    if cursor.description is None:
        return None
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def call_sp(proc_name, params=None):
    """
    Belirtilen SaklÄ± YordamÄ± (Stored Procedure) Ã§aÄŸÄ±rÄ±r.
    ORM ve dÃ¼z SQL sorgularÄ±ndan kaÃ§Ä±nmak iÃ§in bu yardÄ±mcÄ± fonksiyon kullanÄ±lÄ±r.
    """
    params = params or []
    placeholders = ', '.join(['%s'] * len(params))
    sql = f"CALL {proc_name}({placeholders})"
    
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _dict_fetchall(cursor)

# ==========================================
# 1. KULLANICI DAL METOTLARI (auth_user)
# ==========================================

def list_users():
    """TÃ¼m kullanÄ±cÄ±larÄ± listeler (sp_KullaniciListele)."""
    return call_sp('sp_KullaniciListele')

def get_user(user_id):
    """Belirli bir kullanÄ±cÄ±yÄ± bulur (sp_KullaniciBul)."""
    results = call_sp('sp_KullaniciBul', [user_id])
    return results[0] if results else None

def check_user_conflict(username, email, exclude_id=None):
    """Kullanici adi/e-posta cakismasini SP uzerinden denetler."""
    results = call_sp('sp_KullaniciCakismaKontrol', [username, email, exclude_id])
    return results[0] if results else {"username_var_mi": 0, "email_var_mi": 0}

def create_user(username, email, password, first_name, last_name, is_active, is_staff, is_superuser):
    """Yeni kullanÄ±cÄ± ekler (sp_KullaniciEkle)."""
    results = call_sp('sp_KullaniciEkle', [
        username, email, password, first_name, last_name,
        int(is_active), int(is_staff), int(is_superuser)
    ])
    return results[0]['id'] if results else None

def update_user(user_id, username, email, first_name, last_name, is_active, is_staff, is_superuser):
    """KullanÄ±cÄ±yÄ± gÃ¼nceller (sp_KullaniciGuncelle)."""
    call_sp('sp_KullaniciGuncelle', [
        user_id, username, email, first_name, last_name,
        int(is_active), int(is_staff), int(is_superuser)
    ])

def delete_user(user_id):
    """KullanÄ±cÄ±yÄ± siler (sp_KullaniciSil)."""
    call_sp('sp_KullaniciSil', [user_id])


# ==========================================
# 2. KATEGORÄ° DAL METOTLARI (kategoriler)
# ==========================================

def list_categories():
    """TÃ¼m kategorileri listeler (sp_KategoriListele)."""
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
    """Kategoriyi gÃ¼nceller (sp_KategoriGuncelle)."""
    call_sp('sp_KategoriGuncelle', [kategori_id, isim])

def delete_category(kategori_id):
    """Kategoriyi siler (sp_KategoriSil)."""
    call_sp('sp_KategoriSil', [kategori_id])


# ==========================================
# 3. Ä°Ã‡ERÄ°K DAL METOTLARI (icerikler)
# ==========================================

def list_contents():
    """TÃ¼m iÃ§erikleri listeler (sp_IcerikListele)."""
    return call_sp('sp_IcerikListele')

def get_content(content_id):
    """Belirli bir iÃ§eriÄŸi bulur (sp_IcerikBul)."""
    results = call_sp('sp_IcerikBul', [content_id])
    return results[0] if results else None

def create_content(baslik, yazi, resim, yazar_id, kategori_id, tur):
    """Yeni iÃ§erik ekler (sp_IcerikEkle)."""
    results = call_sp('sp_IcerikEkle', [
        baslik, yazi, resim or '', yazar_id, kategori_id, tur
    ])
    return results[0]['id'] if results else None

def update_content(content_id, baslik, yazi, resim, kategori_id, tur):
    """Ä°Ã§eriÄŸi gÃ¼nceller (sp_IcerikGuncelle)."""
    call_sp('sp_IcerikGuncelle', [
        content_id, baslik, yazi, resim or '', kategori_id, tur
    ])

def delete_content(content_id):
    """Ä°Ã§eriÄŸi siler (sp_IcerikSil)."""
    call_sp('sp_IcerikSil', [content_id])


# ==========================================
# 4. YORUM DAL METOTLARI (yorumlar)
# ==========================================

def list_comments():
    """TÃ¼m yorumlarÄ± listeler (sp_YorumListele)."""
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
    """Yorumu gÃ¼nceller (sp_YorumGuncelle)."""
    call_sp('sp_YorumGuncelle', [comment_id, mesaj])

def delete_comment(comment_id):
    """Yorumu siler (sp_YorumSil)."""
    call_sp('sp_YorumSil', [comment_id])


# ==========================================
# 5. PROFÄ°L DAL METOTLARI (profiller)
# ==========================================

def list_profiles():
    """TÃ¼m profilleri listeler (sp_ProfilListele)."""
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
    """Profili gÃ¼nceller (sp_ProfilGuncelle)."""
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
    """Ban/unban hÄ±zlÄ± aksiyon (sp_ProfilBanGuncelle)."""
    call_sp('sp_ProfilBanGuncelle', [profil_id, int(is_banned), timeout_until])


# ==========================================
# 6. Ä°Ã‡ERÄ°K BEÄENÄ° DAL METOTLARI (icerik_begenileri)
# ==========================================

def list_icerik_begenileri():
    """TÃ¼m iÃ§erik beÄŸenilerini listeler (sp_IcerikBegeniListele)."""
    return call_sp('sp_IcerikBegeniListele')

def get_icerik_begeni(begeni_id):
    """Belirli bir iÃ§erik beÄŸenisini bulur (sp_IcerikBegeniBul)."""
    results = call_sp('sp_IcerikBegeniBul', [begeni_id])
    return results[0] if results else None

def create_icerik_begeni(icerik_id, user_id):
    """Ä°Ã§erik beÄŸenisi ekler (sp_IcerikBegeniEkle)."""
    results = call_sp('sp_IcerikBegeniEkle', [icerik_id, user_id])
    return results[0]['id'] if results else None

def update_icerik_begeni(begeni_id, icerik_id, user_id):
    """Ä°Ã§erik beÄŸenisini gÃ¼nceller (sp_IcerikBegeniGuncelle)."""
    call_sp('sp_IcerikBegeniGuncelle', [begeni_id, icerik_id, user_id])

def delete_icerik_begeni(begeni_id):
    """Ä°Ã§erik beÄŸenisini siler (sp_IcerikBegeniSil)."""
    call_sp('sp_IcerikBegeniSil', [begeni_id])


# ==========================================
# 7. Ä°Ã‡ERÄ°K KAYDETME DAL METOTLARI (icerik_kaydetmeleri)
# ==========================================

def list_icerik_kaydetmeleri():
    """TÃ¼m iÃ§erik kaydetmelerini listeler (sp_IcerikKaydetmeListele)."""
    return call_sp('sp_IcerikKaydetmeListele')

def get_icerik_kaydetme(kaydetme_id):
    """Belirli bir kaydetmeyi bulur (sp_IcerikKaydetmeBul)."""
    results = call_sp('sp_IcerikKaydetmeBul', [kaydetme_id])
    return results[0] if results else None

def create_icerik_kaydetme(icerik_id, user_id):
    """Ä°Ã§erik kaydetmesi ekler (sp_IcerikKaydetmeEkle)."""
    results = call_sp('sp_IcerikKaydetmeEkle', [icerik_id, user_id])
    return results[0]['id'] if results else None

def update_icerik_kaydetme(kaydetme_id, icerik_id, user_id):
    """Ä°Ã§erik kaydetmesini gÃ¼nceller (sp_IcerikKaydetmeGuncelle)."""
    call_sp('sp_IcerikKaydetmeGuncelle', [kaydetme_id, icerik_id, user_id])

def delete_icerik_kaydetme(kaydetme_id):
    """Ä°Ã§erik kaydetmesini siler (sp_IcerikKaydetmeSil)."""
    call_sp('sp_IcerikKaydetmeSil', [kaydetme_id])


# ==========================================
# 8. YORUM BEÄENÄ° DAL METOTLARI (yorum_begenileri)
# ==========================================

def list_yorum_begenileri():
    """TÃ¼m yorum beÄŸenilerini listeler (sp_YorumBegeniListele)."""
    return call_sp('sp_YorumBegeniListele')

def get_yorum_begeni(begeni_id):
    """Belirli bir yorum beÄŸenisini bulur (sp_YorumBegeniBul)."""
    results = call_sp('sp_YorumBegeniBul', [begeni_id])
    return results[0] if results else None

def create_yorum_begeni(yorum_id, user_id):
    """Yorum beÄŸenisi ekler (sp_YorumBegeniEkle)."""
    results = call_sp('sp_YorumBegeniEkle', [yorum_id, user_id])
    return results[0]['id'] if results else None

def update_yorum_begeni(begeni_id, yorum_id, user_id):
    """Yorum beÄŸenisini gÃ¼nceller (sp_YorumBegeniGuncelle)."""
    call_sp('sp_YorumBegeniGuncelle', [begeni_id, yorum_id, user_id])

def delete_yorum_begeni(begeni_id):
    """Yorum beÄŸenisini siler (sp_YorumBegeniSil)."""
    call_sp('sp_YorumBegeniSil', [begeni_id])

