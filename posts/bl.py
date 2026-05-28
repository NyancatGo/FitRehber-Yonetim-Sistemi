import re
import django.db
from posts import dal


class ValidationError(Exception):
    """İş mantığı (Business Logic) doğrulama hataları için özel istisna sınıfı."""
    pass


# Yardımcı Doğrulama Fonksiyonları

def _validate_email(email):
    """E-posta adresinin geçerliliğini regex ile kontrol eder."""
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(email_regex, email))


def _ensure_user_is_unique(username, email, exclude_id=None):
    """Kullanıcı adı ve e-posta benzersizliğini veritabanında kontrol eder."""
    conflict = dal.check_user_conflict(username, email, exclude_id)
    if int(conflict.get('username_var_mi') or 0):
        raise ValidationError(f"'{username}' kullanıcı adı zaten kullanımda.")
    if int(conflict.get('email_var_mi') or 0):
        raise ValidationError(f"'{email}' e-posta adresi zaten kullanımda.")


def _is_user_blocked_error(error_msg):
    """Trigger kaynaklı kullanıcı engelleme hatalarını tek yerde tanır."""
    lowered = str(error_msg).lower()
    blocked_tokens = (
        'pasif',
        'engellen',
        'ekleyemez',
        'begenemez',
        'kaydedemez',
    )
    return any(token in lowered for token in blocked_tokens)


# 1. KULLANICI İŞ MANTIĞI (auth_user)

def get_all_users():
    """Tüm kullanıcıları getirir."""
    return dal.list_users()

def get_user_detail(user_id):
    """Bir kullanıcının detaylarını getirir."""
    user = dal.get_user(user_id)
    if not user:
        raise ValidationError("Kullanıcı bulunamadı.")
    return user

def add_user(username, email, password, first_name, last_name, is_active, is_staff, is_superuser):
    """Kullanıcı ekleme iş mantığı."""
    username = username.strip()
    email = email.strip()
    
    if not username:
        raise ValidationError("Kullanıcı adı boş bırakılamaz.")
    if not email:
        raise ValidationError("E-posta adresi boş bırakılamaz.")
    if not _validate_email(email):
        raise ValidationError("Geçersiz e-posta formatı.")
    if not password or len(password) < 6:
        raise ValidationError("Şifre en az 6 karakter olmalıdır.")
        
    _ensure_user_is_unique(username, email)
        
    # Şifre hashleme: Django entegrasyonu için Django'nun standardını kullanmak isterseniz
    # formlarda make_password kullanılır. Burada basitlik için make_password import edip uygulayabiliriz.
    from django.contrib.auth.hashers import make_password
    hashed_password = make_password(password)

    try:
        return dal.create_user(
            username, email, hashed_password, first_name, last_name,
            is_active, is_staff, is_superuser
        )
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kullanıcı oluşturulurken veritabanı hatası oluştu: {e}")

def update_user_profile(user_id, username, email, first_name, last_name, is_active, is_staff, is_superuser):
    """Kullanıcı güncelleme iş mantığı."""
    username = username.strip()
    email = email.strip()
    
    if not username:
        raise ValidationError("Kullanıcı adı boş bırakılamaz.")
    if not email:
        raise ValidationError("E-posta adresi boş bırakılamaz.")
    if not _validate_email(email):
        raise ValidationError("Geçersiz e-posta formatı.")
        
    _ensure_user_is_unique(username, email, user_id)

    try:
        dal.update_user(
            user_id, username, email, first_name, last_name,
            is_active, is_staff, is_superuser
        )
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kullanıcı güncellenirken veritabanı hatası oluştu: {e}")

def remove_user(user_id):
    """Kullanıcı silme iş mantığı."""
    # Kendini silmeyi engelleme gibi kurallar buraya yazılabilir.
    try:
        dal.delete_user(user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if "Kullanici silinemez" in error_msg or "iliskili" in error_msg:
            raise ValidationError("Kullanıcı silinemez: Bu kullanıcıya ait içerik, yorum veya etkileşim kayıtları var. Silmek yerine pasife alın.")
        raise ValidationError(f"Kullanıcı silinirken veritabanı hatası oluştu (İlişkili veriler olabilir): {e}")


# 2. KATEGORİ İŞ MANTIĞI (kategoriler)

def get_all_categories():
    """Tüm kategorileri getirir."""
    return dal.list_categories()

def get_category_detail(kategori_id):
    """Kategori detayını getirir."""
    category = dal.get_category(kategori_id)
    if not category:
        raise ValidationError("Kategori bulunamadı.")
    return category

def add_category(isim):
    """Kategori ekleme iş mantığı."""
    isim = isim.strip()
    if not isim:
        raise ValidationError("Kategori adı boş bırakılamaz.")
        
    existing = dal.list_categories()
    if any(k['isim'].lower() == isim.lower() for k in existing):
        raise ValidationError(f"'{isim}' isimli kategori zaten mevcut.")
        
    try:
        return dal.create_category(isim)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kategori eklenirken veritabanı hatası oluştu: {e}")

def update_category_detail(kategori_id, isim):
    """Kategori güncelleme iş mantığı."""
    isim = isim.strip()
    if not isim:
        raise ValidationError("Kategori adı boş bırakılamaz.")
        
    existing = dal.list_categories()
    if any(k['isim'].lower() == isim.lower() and k['id'] != int(kategori_id) for k in existing):
        raise ValidationError(f"'{isim}' isimli kategori zaten mevcut.")
        
    try:
        dal.update_category(kategori_id, isim)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kategori güncellenirken veritabanı hatası oluştu: {e}")

def remove_category(kategori_id):
    """Kategori silme iş mantığı."""
    try:
        dal.delete_category(kategori_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kategori silinirken veritabanı hatası oluştu (Kategoriye ait içerikler olabilir): {e}")


# 3. İÇERİK İŞ MANTIĞI (icerikler)

def get_all_contents():
    """Tüm içerikleri getirir."""
    return dal.list_contents()

def get_content_detail(content_id):
    """İçerik detaylarını getirir."""
    content = dal.get_content(content_id)
    if not content:
        raise ValidationError("İçerik bulunamadı.")
    return content

def add_content(baslik, yazi, resim, yazar_id, kategori_id, tur):
    """İçerik ekleme iş mantığı (Tetikleyici (Trigger) kontrolünü ele alır)."""
    baslik = baslik.strip()
    yazi = yazi.strip()
    
    if not baslik:
        raise ValidationError("İçerik başlığı boş bırakılamaz.")
    if not yazi:
        raise ValidationError("İçerik yazısı boş bırakılamaz.")
    if not yazar_id:
        raise ValidationError("İçerik yazarı belirtilmelidir.")
    if not kategori_id:
        raise ValidationError("Kategori seçilmelidir.")
    if tur not in ['haber', 'soru']:
        raise ValidationError("Geçersiz içerik türü.")
        
    try:
        return dal.create_content(baslik, yazi, resim, yazar_id, kategori_id, tur)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("İçerik Eklenemedi: Hesabınız pasif/engellenmiş durumdadır.")
        raise ValidationError(f"İçerik eklenirken veritabanı hatası oluştu: {e}")

def update_content_detail(content_id, baslik, yazi, resim, kategori_id, tur):
    """İçerik güncelleme iş mantığı."""
    baslik = baslik.strip()
    yazi = yazi.strip()
    
    if not baslik:
        raise ValidationError("İçerik başlığı boş bırakılamaz.")
    if not yazi:
        raise ValidationError("İçerik yazısı boş bırakılamaz.")
    if not kategori_id:
        raise ValidationError("Kategori seçilmelidir.")
    if tur not in ['haber', 'soru']:
        raise ValidationError("Geçersiz içerik türü.")
        
    try:
        dal.update_content(content_id, baslik, yazi, resim, kategori_id, tur)
    except django.db.DatabaseError as e:
        raise ValidationError(f"İçerik güncellenirken veritabanı hatası oluştu: {e}")

def remove_content(content_id):
    """İçerik silme iş mantığı."""
    try:
        dal.delete_content(content_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"İçerik silinirken veritabanı hatası oluştu: {e}")


# 4. YORUM İŞ MANTIĞI (yorumlar)

def get_all_comments():
    """Tüm yorumları getirir."""
    return dal.list_comments()

def get_comment_detail(comment_id):
    """Yorum detaylarını getirir."""
    comment = dal.get_comment(comment_id)
    if not comment:
        raise ValidationError("Yorum bulunamadı.")
    return comment

def add_comment(icerik_id, yazar_id, parent_id, depth, mesaj):
    """Yorum ekleme iş mantığı (Tetikleyici kontrolünü ele alır)."""
    mesaj = mesaj.strip()
    if not mesaj:
        raise ValidationError("Yorum mesajı boş bırakılamaz.")
    if not icerik_id:
        raise ValidationError("Yorum yapılacak içerik belirtilmelidir.")
    if not yazar_id:
        raise ValidationError("Yorum yazarı belirtilmelidir.")
        
    try:
        return dal.create_comment(icerik_id, yazar_id, parent_id, depth, mesaj)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("Yorum Yapılamadı: Hesabınız pasif/engellenmiş durumdadır.")
        raise ValidationError(f"Yorum eklenirken veritabanı hatası oluştu: {e}")

def update_comment_detail(comment_id, mesaj):
    """Yorum güncelleme iş mantığı."""
    mesaj = mesaj.strip()
    if not mesaj:
        raise ValidationError("Yorum mesajı boş bırakılamaz.")
        
    try:
        dal.update_comment(comment_id, mesaj)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Yorum güncellenirken veritabanı hatası oluştu: {e}")

def remove_comment(comment_id):
    """Yorum silme iş mantığı."""
    try:
        dal.delete_comment(comment_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Yorum silinirken veritabanı hatası oluştu: {e}")


# 5. PROFİL İŞ MANTIĞI (profiller)

def get_all_profiles():
    """Tüm profilleri getirir."""
    return dal.list_profiles()

def get_profile_detail(profil_id):
    """Profil detayını getirir."""
    profil = dal.get_profile(profil_id)
    if not profil:
        raise ValidationError("Profil bulunamadı.")
    return profil

def add_profile(user_id, hakkinda, cinsiyet, boy, kilo, hedef_kilo,
                baslangic_kilo, fitness_hedefi, dogum_tarihi):
    """Profil ekleme iş mantığı."""
    if not user_id:
        raise ValidationError("Kullanıcı belirtilmelidir.")
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
        raise ValidationError(f"Profil eklenirken veritabanı hatası oluştu: {e}")

def update_profile_detail(profil_id, hakkinda, cinsiyet, boy, kilo,
                          hedef_kilo, baslangic_kilo, fitness_hedefi,
                          dogum_tarihi, is_banned, timeout_until):
    """Profil güncelleme iş mantığı."""
    try:
        existing = dal.get_profile(profil_id)
        if not existing:
            raise ValidationError("Profil bulunamadı.")
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
        raise ValidationError(f"Profil güncellenirken veritabanı hatası oluştu: {e}")

def ban_profile(profil_id):
    """Profili banlar (sp_ProfilBanGuncelle)."""
    try:
        dal.set_profile_ban(profil_id, is_banned=True, timeout_until=None)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Ban işlemi başarısız: {e}")

def unban_profile(profil_id):
    """Profil banını kaldırır (sp_ProfilBanGuncelle)."""
    try:
        dal.set_profile_ban(profil_id, is_banned=False, timeout_until=None)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Unban işlemi başarısız: {e}")

def remove_profile(profil_id):
    """Profil silme iş mantığı."""
    try:
        dal.delete_profile(profil_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Profil silinirken veritabanı hatası oluştu: {e}")


# 6. İÇERİK BEĞENİ İŞ MANTIĞI (icerik_begenileri)

def get_all_icerik_begenileri():
    return dal.list_icerik_begenileri()

def add_icerik_begeni(icerik_id, user_id):
    """İçerik beğenisi ekleme (Trigger kullanıcı durumunu denetler)."""
    if not icerik_id or not user_id:
        raise ValidationError("İçerik ve kullanıcı belirtilmelidir.")
    try:
        return dal.create_icerik_begeni(icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("Beğeni Eklenemedi: Kullanıcı pasif/engellenmiş durumda.")
        raise ValidationError(f"Beğeni eklenirken veritabanı hatası: {e}")

def update_icerik_begeni_detail(begeni_id, icerik_id, user_id):
    if not icerik_id or not user_id:
        raise ValidationError("İçerik ve kullanıcı belirtilmelidir.")
    existing = get_all_icerik_begenileri() or []
    if not any(int(b['id']) == int(begeni_id) for b in existing):
        raise ValidationError("Güncellenecek beğeni kaydı bulunamadı.")
    if any(
        int(b['id']) != int(begeni_id)
        and int(b['icerik_id']) == int(icerik_id)
        and int(b['user_id']) == int(user_id)
        for b in existing
    ):
        raise ValidationError("Bu kullanıcı için seçilen içerik beğenisi zaten mevcut.")
    try:
        dal.update_icerik_begeni(begeni_id, icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("Beğeni Güncellenemedi: Kullanıcı pasif/engellenmiş durumda.")
        raise ValidationError(f"Beğeni güncellenirken veritabanı hatası: {e}")

def remove_icerik_begeni(begeni_id):
    try:
        dal.delete_icerik_begeni(begeni_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Beğeni silinirken veritabanı hatası: {e}")


# 7. İÇERİK KAYDETME İŞ MANTIĞI (icerik_kaydetmeleri)

def get_all_icerik_kaydetmeleri():
    return dal.list_icerik_kaydetmeleri()

def add_icerik_kaydetme(icerik_id, user_id):
    """İçerik kaydetme ekleme (Trigger kullanıcı durumunu denetler)."""
    if not icerik_id or not user_id:
        raise ValidationError("İçerik ve kullanıcı belirtilmelidir.")
    try:
        return dal.create_icerik_kaydetme(icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("Kaydetme Eklenemedi: Kullanıcı pasif/engellenmiş durumda.")
        raise ValidationError(f"Kaydetme eklenirken veritabanı hatası: {e}")

def update_icerik_kaydetme_detail(kaydetme_id, icerik_id, user_id):
    if not icerik_id or not user_id:
        raise ValidationError("İçerik ve kullanıcı belirtilmelidir.")
    existing = get_all_icerik_kaydetmeleri() or []
    if not any(int(k['id']) == int(kaydetme_id) for k in existing):
        raise ValidationError("Güncellenecek kaydetme kaydı bulunamadı.")
    if any(
        int(k['id']) != int(kaydetme_id)
        and int(k['icerik_id']) == int(icerik_id)
        and int(k['user_id']) == int(user_id)
        for k in existing
    ):
        raise ValidationError("Bu kullanıcı için seçilen içerik kaydetme kaydı zaten mevcut.")
    try:
        dal.update_icerik_kaydetme(kaydetme_id, icerik_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("Kaydetme Güncellenemedi: Kullanıcı pasif/engellenmiş durumda.")
        raise ValidationError(f"Kaydetme güncellenirken veritabanı hatası: {e}")

def remove_icerik_kaydetme(kaydetme_id):
    try:
        dal.delete_icerik_kaydetme(kaydetme_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Kaydetme silinirken veritabanı hatası: {e}")


# 8. YORUM BEĞENİ İŞ MANTIĞI (yorum_begenileri)

def get_all_yorum_begenileri():
    return dal.list_yorum_begenileri()

def add_yorum_begeni(yorum_id, user_id):
    """Yorum beğenisi ekleme (Trigger kullanıcı durumunu denetler)."""
    if not yorum_id or not user_id:
        raise ValidationError("Yorum ve kullanıcı belirtilmelidir.")
    try:
        return dal.create_yorum_begeni(yorum_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("Beğeni Eklenemedi: Kullanıcı pasif/engellenmiş durumda.")
        raise ValidationError(f"Yorum beğenisi eklenirken veritabanı hatası: {e}")

def update_yorum_begeni_detail(begeni_id, yorum_id, user_id):
    if not yorum_id or not user_id:
        raise ValidationError("Yorum ve kullanıcı belirtilmelidir.")
    existing = get_all_yorum_begenileri() or []
    if not any(int(b['id']) == int(begeni_id) for b in existing):
        raise ValidationError("Güncellenecek yorum beğenisi bulunamadı.")
    if any(
        int(b['id']) != int(begeni_id)
        and int(b['yorum_id']) == int(yorum_id)
        and int(b['user_id']) == int(user_id)
        for b in existing
    ):
        raise ValidationError("Bu kullanıcı için seçilen yorum beğenisi zaten mevcut.")
    try:
        dal.update_yorum_begeni(begeni_id, yorum_id, user_id)
    except django.db.DatabaseError as e:
        error_msg = str(e)
        if _is_user_blocked_error(error_msg):
            raise ValidationError("Yorum Beğenisi Güncellenemedi: Kullanıcı pasif/engellenmiş durumda.")
        raise ValidationError(f"Yorum beğenisi güncellenirken veritabanı hatası: {e}")

def remove_yorum_begeni(begeni_id):
    try:
        dal.delete_yorum_begeni(begeni_id)
    except django.db.DatabaseError as e:
        raise ValidationError(f"Yorum beğenisi silinirken veritabanı hatası: {e}")


# 9. RAPORLAMA / ANALİTİK İŞ MANTIĞI

def get_monthly_interaction_analysis():
    rows = dal.get_monthly_interaction_analysis() or []
    return [
        {
            'ay': row.get('ay'),
            'yorum_sayisi': int(row.get('yorum_sayisi') or 0),
            'begeni_sayisi': int(row.get('begeni_sayisi') or 0),
            'kaydetme_sayisi': int(row.get('kaydetme_sayisi') or 0),
            'toplam_etkilesim': int(row.get('toplam_etkilesim') or 0),
        }
        for row in rows
    ]

def get_category_distribution_report():
    rows = dal.get_category_distribution_report() or []
    return [
        {
            'kategori_adi': row.get('kategori_adi') or 'Kategorisiz',
            'icerik_sayisi': int(row.get('icerik_sayisi') or 0),
            'yuzde': float(row.get('yuzde') or 0),
        }
        for row in rows
    ]


# ==========================================
# KULLANICI TANIMLI FONKSİYON İŞ MANTIĞI
# Function çağrılarının dashboard için hazırlanması
# (fn_IcerikYorumSayisi, fn_KullaniciIcerikSayisi, fn_IcerikEtkilesimSkoru)

def get_icerik_yorum_sayisi(icerik_id):
    """Tek içerik için fn_IcerikYorumSayisi çıktısını döndürür."""
    return int(dal.get_icerik_yorum_sayisi(icerik_id) or 0)


def get_kullanici_icerik_sayisi(user_id):
    """Tek kullanıcı için fn_KullaniciIcerikSayisi çıktısını döndürür."""
    return int(dal.get_kullanici_icerik_sayisi(user_id) or 0)


def get_icerik_etkilesim_skoru(icerik_id):
    """Tek içerik için fn_IcerikEtkilesimSkoru çıktısını döndürür."""
    return int(dal.get_icerik_etkilesim_skoru(icerik_id) or 0)


def get_top_icerik_etkilesim_skorlari(contents, limit=5):
    """
    En yüksek etkileşim skoruna sahip ilk N içeriği döndürür.
    Skor hesabı veritabanında fn_IcerikEtkilesimSkoru ile yapılır.
    """
    if not contents:
        return []
    icerikler_with_skor = []
    for c in contents:
        icerik_id = c.get('id')
        if icerik_id is None:
            continue
        skor = dal.get_icerik_etkilesim_skoru(icerik_id)
        icerikler_with_skor.append({
            'id': icerik_id,
            'baslik': c.get('baslik', '')[:60],
            'yazar': c.get('yazar_adi') or c.get('yazar_username') or '',
            'kategori': c.get('kategori_adi') or '-',
            'tur': c.get('tur', '-'),
            'skor': int(skor or 0),
        })
    icerikler_with_skor.sort(key=lambda x: x['skor'], reverse=True)
    return icerikler_with_skor[:limit]


def get_top_kullanici_icerik_sayilari(users, limit=5):
    """
    En çok içerik üreten ilk N kullanıcıyı döndürür.
    Sayım veritabanında fn_KullaniciIcerikSayisi ile yapılır.
    """
    if not users:
        return []
    users_with_count = []
    for u in users:
        user_id = u.get('id')
        if user_id is None:
            continue
        adet = dal.get_kullanici_icerik_sayisi(user_id)
        adet = int(adet or 0)
        if adet <= 0:
            continue
        users_with_count.append({
            'id': user_id,
            'username': u.get('username', ''),
            'first_name': u.get('first_name', ''),
            'last_name': u.get('last_name', ''),
            'icerik_sayisi': adet,
        })
    users_with_count.sort(key=lambda x: x['icerik_sayisi'], reverse=True)
    return users_with_count[:limit]
