import re
import django.db
from posts import dal

class ValidationError(Exception):
    """Ä°ÅŸ mantÄ±ÄŸÄ± (Business Logic) doÄŸrulama hatalarÄ± iÃ§in Ã¶zel istisna sÄ±nÄ±fÄ±."""
    pass

# ==========================================
# YardÄ±mcÄ± DoÄŸrulama FonksiyonlarÄ±
# ==========================================

def _validate_email(email):
    """E-posta adresinin geÃ§erliliÄŸini regex ile kontrol eder."""
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(email_regex, email))

def _ensure_user_is_unique(username, email, exclude_id=None):
    """Kullanici adi ve e-posta benzersizligini veritabaninda kontrol eder."""
    conflict = dal.check_user_conflict(username, email, exclude_id)
    if int(conflict.get('username_var_mi') or 0):
        raise ValidationError(f"'{username}' kullanÄ±cÄ± adÄ± zaten kullanÄ±mda.")
    if int(conflict.get('email_var_mi') or 0):
        raise ValidationError(f"'{email}' e-posta adresi zaten kullanÄ±mda.")


# ==========================================
# 1. KULLANICI Ä°Å MANTIÄI (auth_user)
# ==========================================

def get_all_users():
    """TÃ¼m kullanÄ±cÄ±larÄ± getirir."""
    return dal.list_users()

def get_user_detail(user_id):
    """Bir kullanÄ±cÄ±nÄ±n detaylarÄ±nÄ± getirir."""
    user = dal.get_user(user_id)
    if not user:
        raise ValidationError("KullanÄ±cÄ± bulunamadÄ±.")
    return user

def add_user(username, email, password, first_name, last_name, is_active, is_staff, is_superuser):
    """KullanÄ±cÄ± ekleme iÅŸ mantÄ±ÄŸÄ±."""
    username = username.strip()
    email = email.strip()
    
    if not username:
        raise ValidationError("KullanÄ±cÄ± adÄ± boÅŸ bÄ±rakÄ±lamaz.")
    if not email:
        raise ValidationError("E-posta adresi boÅŸ bÄ±rakÄ±lamaz.")
    if not _validate_email(email):
        raise ValidationError("GeÃ§ersiz e-posta formatÄ±.")
    if not password or len(password) < 6:
        raise ValidationError("Åifre en az 6 karakter olmalÄ±dÄ±r.")
        
    _ensure_user_is_unique(username, email)
        
    # Åifre hashleme: Django entegrasyonu iÃ§in Django'nun standardÄ±nÄ± kullanmak isterseniz
    # formlarda make_password kullanÄ±lÄ±r. Burada basitlik iÃ§in make_password import edip uygulayabiliriz.
    from django.contrib.auth.hashers import make_password
    hashed_password = make_password(password)

    try:
        return dal.create_user(
            username, email, hashed_password, first_name, last_name,
            is_active, is_staff, is_superuser
        )
    except django.db.DatabaseError as e:
        raise ValidationError(f"KullanÄ±cÄ± oluÅŸturulurken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def update_user_profile(user_id, username, email, first_name, last_name, is_active, is_staff, is_superuser):
    """KullanÄ±cÄ± gÃ¼ncelleme iÅŸ mantÄ±ÄŸÄ±."""
    username = username.strip()
    email = email.strip()
    
    if not username:
        raise ValidationError("KullanÄ±cÄ± adÄ± boÅŸ bÄ±rakÄ±lamaz.")
    if not email:
        raise ValidationError("E-posta adresi boÅŸ bÄ±rakÄ±lamaz.")
    if not _validate_email(email):
        raise ValidationError("GeÃ§ersiz e-posta formatÄ±.")
        
    _ensure_user_is_unique(username, email, user_id)

    try:
        dal.update_user(
            user_id, username, email, first_name, last_name,
            is_active, is_staff, is_superuser
        )
    except django.db.DatabaseError as e:
        raise ValidationError(f"KullanÄ±cÄ± gÃ¼ncellenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def remove_user(user_id):
    """KullanÄ±cÄ± silme iÅŸ mantÄ±ÄŸÄ±."""
    # Kendini silmeyi engelleme gibi kurallar buraya yazÄ±labilir.
    try:
        dal.delete_user(user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "Kullanici silinemez" in error_msg or "iliskili" in error_msg:
            raise ValidationError("Kullanici silinemez: Bu kullaniciya ait icerik, yorum veya etkilesim kayitlari var. Silmek yerine pasife alin.")
        raise ValidationError(f"KullanÄ±cÄ± silinirken veritabanÄ± hatasÄ± oluÅŸtu (Ä°liÅŸkili veriler olabilir): {e}")


# ==========================================
# 2. KATEGORÄ° Ä°Å MANTIÄI (kategoriler)
# ==========================================

def get_all_categories():
    """TÃ¼m kategorileri getirir."""
    return dal.list_categories()

def get_category_detail(kategori_id):
    """Kategori detayÄ±nÄ± getirir."""
    category = dal.get_category(kategori_id)
    if not category:
        raise ValidationError("Kategori bulunamadÄ±.")
    return category

def add_category(isim):
    """Kategori ekleme iÅŸ mantÄ±ÄŸÄ±."""
    isim = isim.strip()
    if not isim:
        raise ValidationError("Kategori adÄ± boÅŸ bÄ±rakÄ±lamaz.")
        
    existing = dal.list_categories()
    if any(k['isim'].lower() == isim.lower() for k in existing):
        raise ValidationError(f"'{isim}' isimli kategori zaten mevcut.")
        
    try:
        return dal.create_category(isim)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kategori eklenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def update_category_detail(kategori_id, isim):
    """Kategori gÃ¼ncelleme iÅŸ mantÄ±ÄŸÄ±."""
    isim = isim.strip()
    if not isim:
        raise ValidationError("Kategori adÄ± boÅŸ bÄ±rakÄ±lamaz.")
        
    existing = dal.list_categories()
    if any(k['isim'].lower() == isim.lower() and k['id'] != int(kategori_id) for k in existing):
        raise ValidationError(f"'{isim}' isimli kategori zaten mevcut.")
        
    try:
        dal.update_category(kategori_id, isim)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kategori gÃ¼ncellenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def remove_category(kategori_id):
    """Kategori silme iÅŸ mantÄ±ÄŸÄ±."""
    try:
        dal.delete_category(kategori_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kategori silinirken veritabanÄ± hatasÄ± oluÅŸtu (Kategoriye ait iÃ§erikler olabilir): {e}")


# ==========================================
# 3. Ä°Ã‡ERÄ°K Ä°Å MANTIÄI (icerikler)
# ==========================================

def get_all_contents():
    """TÃ¼m iÃ§erikleri getirir."""
    return dal.list_contents()

def get_content_detail(content_id):
    """Ä°Ã§erik detaylarÄ±nÄ± getirir."""
    content = dal.get_content(content_id)
    if not content:
        raise ValidationError("Ä°Ã§erik bulunamadÄ±.")
    return content

def add_content(baslik, yazi, resim, yazar_id, kategori_id, tur):
    """Ä°Ã§erik ekleme iÅŸ mantÄ±ÄŸÄ± (Tetikleyici (Trigger) kontrolÃ¼nÃ¼ ele alÄ±r)."""
    baslik = baslik.strip()
    yazi = yazi.strip()
    
    if not baslik:
        raise ValidationError("Ä°Ã§erik baÅŸlÄ±ÄŸÄ± boÅŸ bÄ±rakÄ±lamaz.")
    if not yazi:
        raise ValidationError("Ä°Ã§erik yazÄ±sÄ± boÅŸ bÄ±rakÄ±lamaz.")
    if not yazar_id:
        raise ValidationError("Ä°Ã§erik yazarÄ± belirtilmelidir.")
    if not kategori_id:
        raise ValidationError("Kategori seÃ§ilmelidir.")
    if tur not in ['haber', 'soru']:
        raise ValidationError("GeÃ§ersiz iÃ§erik tÃ¼rÃ¼.")
        
    try:
        return dal.create_content(baslik, yazi, resim, yazar_id, kategori_id, tur)
    except django.db.DatabaseError as e:
        # Trigger tarafÄ±ndan yÃ¼kseltilen hata mesajÄ±nÄ± kullanÄ±cÄ±ya dostÃ§a gÃ¶steriyoruz
        error_msg = str(e)
        if "pasif olan kullanÄ±cÄ±lar" in error_msg:
            raise ValidationError("Ä°Ã§erik Eklenemedi: HesabÄ±nÄ±z pasif/engellenmiÅŸ durumdadÄ±r.")
        raise ValidationError(f"Ä°Ã§erik eklenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def update_content_detail(content_id, baslik, yazi, resim, kategori_id, tur):
    """Ä°Ã§erik gÃ¼ncelleme iÅŸ mantÄ±ÄŸÄ±."""
    baslik = baslik.strip()
    yazi = yazi.strip()
    
    if not baslik:
        raise ValidationError("Ä°Ã§erik baÅŸlÄ±ÄŸÄ± boÅŸ bÄ±rakÄ±lamaz.")
    if not yazi:
        raise ValidationError("Ä°Ã§erik yazÄ±sÄ± boÅŸ bÄ±rakÄ±lamaz.")
    if not kategori_id:
        raise ValidationError("Kategori seÃ§ilmelidir.")
    if tur not in ['haber', 'soru']:
        raise ValidationError("GeÃ§ersiz iÃ§erik tÃ¼rÃ¼.")
        
    try:
        dal.update_content(content_id, baslik, yazi, resim, kategori_id, tur)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Ä°Ã§erik gÃ¼ncellenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def remove_content(content_id):
    """Ä°Ã§erik silme iÅŸ mantÄ±ÄŸÄ±."""
    try:
        dal.delete_content(content_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Ä°Ã§erik silinirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")


# ==========================================
# 4. YORUM Ä°Å MANTIÄI (yorumlar)
# ==========================================

def get_all_comments():
    """TÃ¼m yorumlarÄ± getirir."""
    return dal.list_comments()

def get_comment_detail(comment_id):
    """Yorum detaylarÄ±nÄ± getirir."""
    comment = dal.get_comment(comment_id)
    if not comment:
        raise ValidationError("Yorum bulunamadÄ±.")
    return comment

def add_comment(icerik_id, yazar_id, parent_id, depth, mesaj):
    """Yorum ekleme iÅŸ mantÄ±ÄŸÄ± (Tetikleyici kontrolÃ¼nÃ¼ ele alÄ±r)."""
    mesaj = mesaj.strip()
    if not mesaj:
        raise ValidationError("Yorum mesajÄ± boÅŸ bÄ±rakÄ±lamaz.")
    if not icerik_id:
        raise ValidationError("Yorum yapÄ±lacak iÃ§erik belirtilmelidir.")
    if not yazar_id:
        raise ValidationError("Yorum yazarÄ± belirtilmelidir.")
        
    try:
        return dal.create_comment(icerik_id, yazar_id, parent_id, depth, mesaj)
    except django.db.DatabaseError as e:
        # Trigger tarafÄ±ndan yÃ¼kseltilen hata mesajÄ±nÄ± kullanÄ±cÄ±ya dostÃ§a gÃ¶steriyoruz
        error_msg = str(e)
        if "pasif olan kullanÄ±cÄ±lar" in error_msg:
            raise ValidationError("Yorum YapÄ±lamadÄ±: HesabÄ±nÄ±z pasif/engellenmiÅŸ durumdadÄ±r.")
        raise ValidationError(f"Yorum eklenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def update_comment_detail(comment_id, mesaj):
    """Yorum gÃ¼ncelleme iÅŸ mantÄ±ÄŸÄ±."""
    mesaj = mesaj.strip()
    if not mesaj:
        raise ValidationError("Yorum mesajÄ± boÅŸ bÄ±rakÄ±lamaz.")
        
    try:
        dal.update_comment(comment_id, mesaj)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Yorum gÃ¼ncellenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def remove_comment(comment_id):
    """Yorum silme iÅŸ mantÄ±ÄŸÄ±."""
    try:
        dal.delete_comment(comment_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Yorum silinirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")


# ==========================================
# 5. PROFÄ°L Ä°Å MANTIÄI (profiller)
# ==========================================

def get_all_profiles():
    """TÃ¼m profilleri getirir."""
    return dal.list_profiles()

def get_profile_detail(profil_id):
    """Profil detayÄ±nÄ± getirir."""
    profil = dal.get_profile(profil_id)
    if not profil:
        raise ValidationError("Profil bulunamadÄ±.")
    return profil

def add_profile(user_id, hakkinda, cinsiyet, boy, kilo, hedef_kilo,
                baslangic_kilo, fitness_hedefi, dogum_tarihi):
    """Profil ekleme iÅŸ mantÄ±ÄŸÄ±."""
    if not user_id:
        raise ValidationError("KullanÄ±cÄ± belirtilmelidir.")
    try:
        return dal.create_profile(
            user_id=user_id,
            foto='',
            hakkinda=hakkinda or '',
            cinsiyet=cinsiyet or 'B',
            boy=boy or None,
            kilo=kilo or None,
            hedef_kilo=hedef_kilo or None,
            baslangic_kilo=baslangic_kilo or None,
            fitness_hedefi=fitness_hedefi or '',
            dogum_tarihi=dogum_tarihi or None,
            is_onboarded=0,
            gunluk_su_hedefi_ml=None,
            is_banned=0,
            timeout_until=None,
        )
    except django.db.DatabaseError as e:
        raise ValidationError(f"Profil eklenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def update_profile_detail(profil_id, hakkinda, cinsiyet, boy, kilo,
                          hedef_kilo, baslangic_kilo, fitness_hedefi,
                          dogum_tarihi, is_banned, timeout_until):
    """Profil gÃ¼ncelleme iÅŸ mantÄ±ÄŸÄ±."""
    try:
        existing = dal.get_profile(profil_id)
        if not existing:
            raise ValidationError("Profil bulunamadÄ±.")
        dal.update_profile(
            profil_id=profil_id,
            foto=existing.get('foto') or '',
            hakkinda=hakkinda or '',
            cinsiyet=cinsiyet or 'B',
            boy=boy or None,
            kilo=kilo or None,
            hedef_kilo=hedef_kilo or None,
            baslangic_kilo=baslangic_kilo or None,
            fitness_hedefi=fitness_hedefi or '',
            dogum_tarihi=dogum_tarihi or None,
            is_onboarded=existing.get('is_onboarded', 0),
            gunluk_su_hedefi_ml=existing.get('gunluk_su_hedefi_ml'),
            is_banned=int(is_banned),
            timeout_until=timeout_until or None,
        )
    except django.db.DatabaseError as e:
        raise ValidationError(f"Profil gÃ¼ncellenirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")

def ban_profile(profil_id):
    """Profili banlar (sp_ProfilBanGuncelle)."""
    try:
        dal.set_profile_ban(profil_id, is_banned=True, timeout_until=None)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Ban iÅŸlemi baÅŸarÄ±sÄ±z: {e}")

def unban_profile(profil_id):
    """Profil banÄ±nÄ± kaldÄ±rÄ±r (sp_ProfilBanGuncelle)."""
    try:
        dal.set_profile_ban(profil_id, is_banned=False, timeout_until=None)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Unban iÅŸlemi baÅŸarÄ±sÄ±z: {e}")

def remove_profile(profil_id):
    """Profil silme iÅŸ mantÄ±ÄŸÄ±."""
    try:
        dal.delete_profile(profil_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Profil silinirken veritabanÄ± hatasÄ± oluÅŸtu: {e}")


# ==========================================
# 6. Ä°Ã‡ERÄ°K BEÄENÄ° Ä°Å MANTIÄI (icerik_begenileri)
# ==========================================

def get_all_icerik_begenileri():
    return dal.list_icerik_begenileri()

def add_icerik_begeni(icerik_id, user_id):
    """Ä°Ã§erik beÄŸenisi ekleme (Trigger kullanÄ±cÄ± durumunu denetler)."""
    if not icerik_id or not user_id:
        raise ValidationError("Ä°Ã§erik ve kullanÄ±cÄ± belirtilmelidir.")
    try:
        return dal.create_icerik_begeni(icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "pasif" in error_msg or "begenemez" in error_msg:
            raise ValidationError("BeÄŸeni Eklenemedi: KullanÄ±cÄ± pasif/engellenmiÅŸ durumda.")
        raise ValidationError(f"BeÄŸeni eklenirken veritabanÄ± hatasÄ±: {e}")

def update_icerik_begeni_detail(begeni_id, icerik_id, user_id):
    if not icerik_id or not user_id:
        raise ValidationError("Ä°Ã§erik ve kullanÄ±cÄ± belirtilmelidir.")
    existing = get_all_icerik_begenileri() or []
    if not any(int(b['id']) == int(begeni_id) for b in existing):
        raise ValidationError("GÃ¼ncellenecek beÄŸeni kaydÄ± bulunamadÄ±.")
    if any(
        int(b['id']) != int(begeni_id)
        and int(b['icerik_id']) == int(icerik_id)
        and int(b['user_id']) == int(user_id)
        for b in existing
    ):
        raise ValidationError("Bu kullanÄ±cÄ± iÃ§in seÃ§ilen iÃ§erik beÄŸenisi zaten mevcut.")
    try:
        dal.update_icerik_begeni(begeni_id, icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "begenemez" in error_msg or "pasif" in error_msg or "engellen" in error_msg:
            raise ValidationError("BeÄŸeni GÃ¼ncellenemedi: KullanÄ±cÄ± pasif/engellenmiÅŸ durumda.")
        raise ValidationError(f"BeÄŸeni gÃ¼ncellenirken veritabanÄ± hatasÄ±: {e}")

def remove_icerik_begeni(begeni_id):
    try:
        dal.delete_icerik_begeni(begeni_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"BeÄŸeni silinirken veritabanÄ± hatasÄ±: {e}")


# ==========================================
# 7. Ä°Ã‡ERÄ°K KAYDETME Ä°Å MANTIÄI (icerik_kaydetmeleri)
# ==========================================

def get_all_icerik_kaydetmeleri():
    return dal.list_icerik_kaydetmeleri()

def add_icerik_kaydetme(icerik_id, user_id):
    """Ä°Ã§erik kaydetme ekleme (Trigger kullanÄ±cÄ± durumunu denetler)."""
    if not icerik_id or not user_id:
        raise ValidationError("Ä°Ã§erik ve kullanÄ±cÄ± belirtilmelidir.")
    try:
        return dal.create_icerik_kaydetme(icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "pasif" in error_msg or "kaydedemez" in error_msg:
            raise ValidationError("Kaydetme Eklenemedi: KullanÄ±cÄ± pasif/engellenmiÅŸ durumda.")
        raise ValidationError(f"Kaydetme eklenirken veritabanÄ± hatasÄ±: {e}")

def update_icerik_kaydetme_detail(kaydetme_id, icerik_id, user_id):
    if not icerik_id or not user_id:
        raise ValidationError("Ä°Ã§erik ve kullanÄ±cÄ± belirtilmelidir.")
    existing = get_all_icerik_kaydetmeleri() or []
    if not any(int(k['id']) == int(kaydetme_id) for k in existing):
        raise ValidationError("GÃ¼ncellenecek kaydetme kaydÄ± bulunamadÄ±.")
    if any(
        int(k['id']) != int(kaydetme_id)
        and int(k['icerik_id']) == int(icerik_id)
        and int(k['user_id']) == int(user_id)
        for k in existing
    ):
        raise ValidationError("Bu kullanÄ±cÄ± iÃ§in seÃ§ilen iÃ§erik kaydetme kaydÄ± zaten mevcut.")
    try:
        dal.update_icerik_kaydetme(kaydetme_id, icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "kaydedemez" in error_msg or "pasif" in error_msg or "engellen" in error_msg:
            raise ValidationError("Kaydetme GÃ¼ncellenemedi: KullanÄ±cÄ± pasif/engellenmiÅŸ durumda.")
        raise ValidationError(f"Kaydetme gÃ¼ncellenirken veritabanÄ± hatasÄ±: {e}")

def remove_icerik_kaydetme(kaydetme_id):
    try:
        dal.delete_icerik_kaydetme(kaydetme_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kaydetme silinirken veritabanÄ± hatasÄ±: {e}")


# ==========================================
# 8. YORUM BEÄENÄ° Ä°Å MANTIÄI (yorum_begenileri)
# ==========================================

def get_all_yorum_begenileri():
    return dal.list_yorum_begenileri()

def add_yorum_begeni(yorum_id, user_id):
    """Yorum beÄŸenisi ekleme (Trigger kullanÄ±cÄ± durumunu denetler)."""
    if not yorum_id or not user_id:
        raise ValidationError("Yorum ve kullanÄ±cÄ± belirtilmelidir.")
    try:
        return dal.create_yorum_begeni(yorum_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "pasif" in error_msg or "begenemez" in error_msg:
            raise ValidationError("BeÄŸeni Eklenemedi: KullanÄ±cÄ± pasif/engellenmiÅŸ durumda.")
        raise ValidationError(f"Yorum beÄŸenisi eklenirken veritabanÄ± hatasÄ±: {e}")

def update_yorum_begeni_detail(begeni_id, yorum_id, user_id):
    if not yorum_id or not user_id:
        raise ValidationError("Yorum ve kullanÄ±cÄ± belirtilmelidir.")
    existing = get_all_yorum_begenileri() or []
    if not any(int(b['id']) == int(begeni_id) for b in existing):
        raise ValidationError("GÃ¼ncellenecek yorum beÄŸenisi bulunamadÄ±.")
    if any(
        int(b['id']) != int(begeni_id)
        and int(b['yorum_id']) == int(yorum_id)
        and int(b['user_id']) == int(user_id)
        for b in existing
    ):
        raise ValidationError("Bu kullanÄ±cÄ± iÃ§in seÃ§ilen yorum beÄŸenisi zaten mevcut.")
    try:
        dal.update_yorum_begeni(begeni_id, yorum_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "begenemez" in error_msg or "pasif" in error_msg or "engellen" in error_msg:
            raise ValidationError("Yorum BeÄŸenisi GÃ¼ncellenemedi: KullanÄ±cÄ± pasif/engellenmiÅŸ durumda.")
        raise ValidationError(f"Yorum beÄŸenisi gÃ¼ncellenirken veritabanÄ± hatasÄ±: {e}")

def remove_yorum_begeni(begeni_id):
    try:
        dal.delete_yorum_begeni(begeni_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Yorum beÄŸenisi silinirken veritabanÄ± hatasÄ±: {e}")

