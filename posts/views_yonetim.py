from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from posts import bl

# ==========================================
# Yetki Kontrolü Dekoratörü
# ==========================================

def superuser_required(view_func):
    """Yalnızca is_superuser olan kullanıcıların erişimine izin verir."""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')  # Allauth veya standart giriş
        if not request.user.is_superuser:
            return HttpResponseForbidden("Bu yönetim konsoluna yalnızca Süper Yöneticiler (Superuser) erişebilir.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ==========================================
# Dashboard (Özet Paneli)
# ==========================================

@superuser_required
def dashboard(request):
    users = bl.get_all_users()
    categories = bl.get_all_categories()
    contents = bl.get_all_contents()
    comments = bl.get_all_comments()
    profiller = bl.get_all_profiles()
    icerik_begenileri = bl.get_all_icerik_begenileri()
    icerik_kaydetmeleri = bl.get_all_icerik_kaydetmeleri()
    yorum_begenileri = bl.get_all_yorum_begenileri()
    aylik_etkilesim = bl.get_monthly_interaction_analysis()
    kategori_dagilimi = bl.get_category_distribution_report()

    context = {
        'total_users': len(users) if users else 0,
        'total_categories': len(categories) if categories else 0,
        'total_contents': len(contents) if contents else 0,
        'total_comments': len(comments) if comments else 0,
        'total_profiles': len(profiller) if profiller else 0,
        'total_icerik_begenileri': len(icerik_begenileri) if icerik_begenileri else 0,
        'total_icerik_kaydetmeleri': len(icerik_kaydetmeleri) if icerik_kaydetmeleri else 0,
        'total_yorum_begenileri': len(yorum_begenileri) if yorum_begenileri else 0,
        'aylik_etkilesim': aylik_etkilesim,
        'kategori_dagilimi': kategori_dagilimi,
        'active_tab': 'dashboard'
    }
    return render(request, 'yonetim/dashboard.html', context)


# ==========================================
# 1. KULLANICI YÖNETİMİ
# ==========================================

@superuser_required
def kullanici_liste(request):
    users = bl.get_all_users()
    return render(request, 'yonetim/kullanicilar.html', {
        'kullanicilar': users,
        'active_tab': 'kullanicilar'
    })

@superuser_required
def kullanici_ekle(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        
        try:
            bl.add_user(username, email, password, first_name, last_name, is_active, is_staff, is_superuser)
            messages.success(request, f"'{username}' kullanıcısı başarıyla eklendi.")
            return redirect('yonetim_kullanicilar')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/kullanici_form.html', {
        'title': 'Yeni Kullanıcı Ekle',
        'active_tab': 'kullanicilar'
    })

@superuser_required
def kullanici_duzenle(request, user_id):
    try:
        user = bl.get_user_detail(user_id)
    except bl.ValidationError as e:
        messages.error(request, str(e))
        return redirect('yonetim_kullanicilar')
        
    if request.method == 'POST':
        username = request.POST.get('username', '')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        
        try:
            bl.update_user_profile(user_id, username, email, first_name, last_name, is_active, is_staff, is_superuser)
            messages.success(request, f"'{username}' kullanıcısı başarıyla güncellendi.")
            return redirect('yonetim_kullanicilar')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/kullanici_form.html', {
        'user_data': user,
        'title': 'Kullanıcı Düzenle',
        'active_tab': 'kullanicilar'
    })

@superuser_required
def kullanici_sil(request, user_id):
    if request.method != 'POST':
        return redirect('yonetim_kullanicilar')
    try:
        user = bl.get_user_detail(user_id)
        if request.user.id == int(user_id):
            messages.error(request, "Kendinizi silemezsiniz!")
        else:
            bl.remove_user(user_id)
            messages.success(request, f"'{user['username']}' kullanıcısı başarıyla silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_kullanicilar')


# ==========================================
# 2. KATEGORİ YÖNETİMİ
# ==========================================

@superuser_required
def kategori_liste(request):
    categories = bl.get_all_categories()
    return render(request, 'yonetim/kategoriler.html', {
        'kategoriler': categories,
        'active_tab': 'kategoriler'
    })

@superuser_required
def kategori_ekle(request):
    if request.method == 'POST':
        isim = request.POST.get('isim', '')
        try:
            bl.add_category(isim)
            messages.success(request, f"'{isim}' kategorisi başarıyla eklendi.")
            return redirect('yonetim_kategoriler')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/kategori_form.html', {
        'title': 'Yeni Kategori Ekle',
        'active_tab': 'kategoriler'
    })

@superuser_required
def kategori_duzenle(request, kategori_id):
    try:
        category = bl.get_category_detail(kategori_id)
    except bl.ValidationError as e:
        messages.error(request, str(e))
        return redirect('yonetim_kategoriler')
        
    if request.method == 'POST':
        isim = request.POST.get('isim', '')
        try:
            bl.update_category_detail(kategori_id, isim)
            messages.success(request, f"Kategori '{isim}' olarak güncellendi.")
            return redirect('yonetim_kategoriler')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/kategori_form.html', {
        'category_data': category,
        'title': 'Kategori Düzenle',
        'active_tab': 'kategoriler'
    })

@superuser_required
def kategori_sil(request, kategori_id):
    if request.method != 'POST':
        return redirect('yonetim_kategoriler')
    try:
        category = bl.get_category_detail(kategori_id)
        bl.remove_category(kategori_id)
        messages.success(request, f"'{category['isim']}' kategorisi başarıyla silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_kategoriler')


# ==========================================
# 3. İÇERİK YÖNETİMİ
# ==========================================

@superuser_required
def icerik_liste(request):
    contents = bl.get_all_contents()
    return render(request, 'yonetim/icerikler.html', {
        'icerikler': contents,
        'active_tab': 'icerikler'
    })

@superuser_required
def icerik_ekle(request):
    categories = bl.get_all_categories()
    users = bl.get_all_users()
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '')
        yazi = request.POST.get('yazi', '')
        resim = request.POST.get('resim', '') # Varsa resim yolu
        yazar_id = request.POST.get('yazar_id', '')
        kategori_id = request.POST.get('kategori_id', '')
        tur = request.POST.get('tur', 'haber')
        
        try:
            bl.add_content(baslik, yazi, resim, yazar_id, kategori_id, tur)
            messages.success(request, f"'{baslik}' içeriği başarıyla eklendi.")
            return redirect('yonetim_icerikler')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/icerik_form.html', {
        'title': 'Yeni İçerik Ekle',
        'kategoriler': categories,
        'yazarlar': users,
        'active_tab': 'icerikler'
    })

@superuser_required
def icerik_duzenle(request, content_id):
    try:
        content = bl.get_content_detail(content_id)
    except bl.ValidationError as e:
        messages.error(request, str(e))
        return redirect('yonetim_icerikler')
        
    categories = bl.get_all_categories()
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '')
        yazi = request.POST.get('yazi', '')
        resim = request.POST.get('resim', '')
        kategori_id = request.POST.get('kategori_id', '')
        tur = request.POST.get('tur', 'haber')
        
        try:
            bl.update_content_detail(content_id, baslik, yazi, resim, kategori_id, tur)
            messages.success(request, f"'{baslik}' içeriği başarıyla güncellendi.")
            return redirect('yonetim_icerikler')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/icerik_form.html', {
        'content_data': content,
        'title': 'İçerik Düzenle',
        'kategoriler': categories,
        'active_tab': 'icerikler'
    })

@superuser_required
def icerik_sil(request, content_id):
    if request.method != 'POST':
        return redirect('yonetim_icerikler')
    try:
        content = bl.get_content_detail(content_id)
        bl.remove_content(content_id)
        messages.success(request, f"'{content['baslik']}' içeriği başarıyla silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_icerikler')


# ==========================================
# 4. YORUM YÖNETİMİ
# ==========================================

@superuser_required
def yorum_liste(request):
    comments = bl.get_all_comments()
    return render(request, 'yonetim/yorumlar.html', {
        'yorumlar': comments,
        'active_tab': 'yorumlar'
    })

@superuser_required
def yorum_ekle(request):
    contents = bl.get_all_contents()
    users = bl.get_all_users()
    
    if request.method == 'POST':
        icerik_id = request.POST.get('icerik_id', '')
        yazar_id = request.POST.get('yazar_id', '')
        mesaj = request.POST.get('mesaj', '')
        parent_id = request.POST.get('parent_id') or None
        depth = int(request.POST.get('depth', 0))
        
        try:
            bl.add_comment(icerik_id, yazar_id, parent_id, depth, mesaj)
            messages.success(request, "Yorum başarıyla eklendi.")
            return redirect('yonetim_yorumlar')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/yorum_form.html', {
        'title': 'Yeni Yorum Ekle',
        'icerikler': contents,
        'yazarlar': users,
        'active_tab': 'yorumlar'
    })

@superuser_required
def yorum_duzenle(request, comment_id):
    try:
        comment = bl.get_comment_detail(comment_id)
    except bl.ValidationError as e:
        messages.error(request, str(e))
        return redirect('yonetim_yorumlar')
        
    if request.method == 'POST':
        mesaj = request.POST.get('mesaj', '')
        try:
            bl.update_comment_detail(comment_id, mesaj)
            messages.success(request, "Yorum başarıyla güncellendi.")
            return redirect('yonetim_yorumlar')
        except bl.ValidationError as e:
            messages.error(request, str(e))
            
    return render(request, 'yonetim/yorum_form.html', {
        'comment_data': comment,
        'title': 'Yorum Düzenle',
        'active_tab': 'yorumlar'
    })

@superuser_required
def yorum_sil(request, comment_id):
    if request.method != 'POST':
        return redirect('yonetim_yorumlar')
    try:
        bl.remove_comment(comment_id)
        messages.success(request, "Yorum başarıyla silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_yorumlar')


# ==========================================
# 5. PROFİL YÖNETİMİ
# ==========================================

@superuser_required
def profil_liste(request):
    profiller = bl.get_all_profiles()
    return render(request, 'yonetim/profiller.html', {
        'profiller': profiller,
        'active_tab': 'profiller'
    })

@superuser_required
def profil_ekle(request):
    all_users = bl.get_all_users() or []
    all_profiles = bl.get_all_profiles() or []
    profilli_ids = {p['user_id'] for p in all_profiles}
    users = [u for u in all_users if u['id'] not in profilli_ids]
    if request.method == 'POST':
        user_id = request.POST.get('user_id', '')
        hakkinda = request.POST.get('hakkinda', '')
        cinsiyet = request.POST.get('cinsiyet', 'B')
        boy = request.POST.get('boy') or None
        kilo = request.POST.get('kilo') or None
        hedef_kilo = request.POST.get('hedef_kilo') or None
        baslangic_kilo = request.POST.get('baslangic_kilo') or None
        fitness_hedefi = request.POST.get('fitness_hedefi', '')
        dogum_tarihi = request.POST.get('dogum_tarihi') or None
        try:
            bl.add_profile(user_id, hakkinda, cinsiyet, boy, kilo,
                           hedef_kilo, baslangic_kilo, fitness_hedefi, dogum_tarihi)
            messages.success(request, "Profil başarıyla oluşturuldu.")
            return redirect('yonetim_profiller')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/profil_form.html', {
        'title': 'Yeni Profil Ekle',
        'kullanicilar': users,
        'active_tab': 'profiller'
    })

@superuser_required
def profil_duzenle(request, profil_id):
    try:
        profil = bl.get_profile_detail(profil_id)
    except bl.ValidationError as e:
        messages.error(request, str(e))
        return redirect('yonetim_profiller')
    if request.method == 'POST':
        hakkinda = request.POST.get('hakkinda', '')
        cinsiyet = request.POST.get('cinsiyet', 'B')
        boy = request.POST.get('boy') or None
        kilo = request.POST.get('kilo') or None
        hedef_kilo = request.POST.get('hedef_kilo') or None
        baslangic_kilo = request.POST.get('baslangic_kilo') or None
        fitness_hedefi = request.POST.get('fitness_hedefi', '')
        dogum_tarihi = request.POST.get('dogum_tarihi') or None
        is_banned = request.POST.get('is_banned') == 'on'
        timeout_until = request.POST.get('timeout_until') or None
        try:
            bl.update_profile_detail(
                profil_id, hakkinda, cinsiyet, boy, kilo,
                hedef_kilo, baslangic_kilo, fitness_hedefi,
                dogum_tarihi, is_banned, timeout_until
            )
            messages.success(request, f"Profil #{profil_id} başarıyla güncellendi.")
            return redirect('yonetim_profiller')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/profil_form.html', {
        'profil': profil,
        'title': 'Profil Düzenle',
        'active_tab': 'profiller'
    })

@superuser_required
def profil_sil(request, profil_id):
    if request.method != 'POST':
        return redirect('yonetim_profiller')
    try:
        bl.remove_profile(profil_id)
        messages.success(request, f"Profil #{profil_id} silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_profiller')

@superuser_required
def profil_ban_toggle(request, profil_id):
    """Ban/Unban hızlı aksiyonu — POST ile tetiklenir."""
    if request.method != 'POST':
        return redirect('yonetim_profiller')
    aksiyon = request.POST.get('aksiyon', '')
    try:
        if aksiyon == 'ban':
            bl.ban_profile(profil_id)
            messages.success(request, f"Profil #{profil_id} banlandı.")
        elif aksiyon == 'unban':
            bl.unban_profile(profil_id)
            messages.success(request, f"Profil #{profil_id} bandan çıkarıldı.")
        else:
            messages.error(request, "Geçersiz aksiyon.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_profiller')


# ==========================================
# 6. İÇERİK BEĞENİ YÖNETİMİ
# ==========================================

@superuser_required
def icerik_begeni_liste(request):
    contents = bl.get_all_contents()
    users = bl.get_all_users()
    begeniler = bl.get_all_icerik_begenileri()
    if request.method == 'POST':
        icerik_id = request.POST.get('icerik_id', '')
        user_id = request.POST.get('user_id', '')
        try:
            bl.add_icerik_begeni(icerik_id, user_id)
            messages.success(request, "İçerik beğenisi eklendi.")
            return redirect('yonetim_icerik_begenileri')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/icerik_begeniler.html', {
        'begeniler': begeniler,
        'icerikler': contents,
        'kullanicilar': users,
        'active_tab': 'icerik_begenileri'
    })

@superuser_required
def icerik_begeni_duzenle(request, begeni_id):
    contents = bl.get_all_contents()
    users = bl.get_all_users()
    begeniler = bl.get_all_icerik_begenileri()
    edit_data = next((b for b in (begeniler or []) if b['id'] == begeni_id), None)
    if not edit_data:
        messages.error(request, f"Beğeni #{begeni_id} bulunamadı.")
        return redirect('yonetim_icerik_begenileri')
    if request.method == 'POST':
        icerik_id = request.POST.get('icerik_id', '')
        user_id = request.POST.get('user_id', '')
        try:
            bl.update_icerik_begeni_detail(begeni_id, icerik_id, user_id)
            messages.success(request, f"Beğeni #{begeni_id} güncellendi.")
            return redirect('yonetim_icerik_begenileri')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/icerik_begeniler.html', {
        'begeniler': begeniler,
        'icerikler': contents,
        'kullanicilar': users,
        'edit_data': edit_data,
        'active_tab': 'icerik_begenileri'
    })

@superuser_required
def icerik_begeni_sil(request, begeni_id):
    if request.method != 'POST':
        return redirect('yonetim_icerik_begenileri')
    try:
        bl.remove_icerik_begeni(begeni_id)
        messages.success(request, f"Beğeni #{begeni_id} silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_icerik_begenileri')


# ==========================================
# 7. İÇERİK KAYDETME YÖNETİMİ
# ==========================================

@superuser_required
def icerik_kaydetme_liste(request):
    contents = bl.get_all_contents()
    users = bl.get_all_users()
    kaydetmeler = bl.get_all_icerik_kaydetmeleri()
    if request.method == 'POST':
        icerik_id = request.POST.get('icerik_id', '')
        user_id = request.POST.get('user_id', '')
        try:
            bl.add_icerik_kaydetme(icerik_id, user_id)
            messages.success(request, "İçerik kaydetmesi eklendi.")
            return redirect('yonetim_icerik_kaydetmeleri')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/icerik_kaydetmeler.html', {
        'kaydetmeler': kaydetmeler,
        'icerikler': contents,
        'kullanicilar': users,
        'active_tab': 'icerik_kaydetmeleri'
    })

@superuser_required
def icerik_kaydetme_duzenle(request, kaydetme_id):
    contents = bl.get_all_contents()
    users = bl.get_all_users()
    kaydetmeler = bl.get_all_icerik_kaydetmeleri()
    edit_data = next((k for k in (kaydetmeler or []) if k['id'] == kaydetme_id), None)
    if not edit_data:
        messages.error(request, f"Kaydetme #{kaydetme_id} bulunamadı.")
        return redirect('yonetim_icerik_kaydetmeleri')
    if request.method == 'POST':
        icerik_id = request.POST.get('icerik_id', '')
        user_id = request.POST.get('user_id', '')
        try:
            bl.update_icerik_kaydetme_detail(kaydetme_id, icerik_id, user_id)
            messages.success(request, f"Kaydetme #{kaydetme_id} güncellendi.")
            return redirect('yonetim_icerik_kaydetmeleri')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/icerik_kaydetmeler.html', {
        'kaydetmeler': kaydetmeler,
        'icerikler': contents,
        'kullanicilar': users,
        'edit_data': edit_data,
        'active_tab': 'icerik_kaydetmeleri'
    })

@superuser_required
def icerik_kaydetme_sil(request, kaydetme_id):
    if request.method != 'POST':
        return redirect('yonetim_icerik_kaydetmeleri')
    try:
        bl.remove_icerik_kaydetme(kaydetme_id)
        messages.success(request, f"Kaydetme #{kaydetme_id} silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_icerik_kaydetmeleri')


# ==========================================
# 8. YORUM BEĞENİ YÖNETİMİ
# ==========================================

@superuser_required
def yorum_begeni_liste(request):
    comments = bl.get_all_comments()
    users = bl.get_all_users()
    begeniler = bl.get_all_yorum_begenileri()
    if request.method == 'POST':
        yorum_id = request.POST.get('yorum_id', '')
        user_id = request.POST.get('user_id', '')
        try:
            bl.add_yorum_begeni(yorum_id, user_id)
            messages.success(request, "Yorum beğenisi eklendi.")
            return redirect('yonetim_yorum_begenileri')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/yorum_begeniler.html', {
        'begeniler': begeniler,
        'yorumlar': comments,
        'kullanicilar': users,
        'active_tab': 'yorum_begenileri'
    })

@superuser_required
def yorum_begeni_duzenle(request, begeni_id):
    comments = bl.get_all_comments()
    users = bl.get_all_users()
    begeniler = bl.get_all_yorum_begenileri()
    edit_data = next((b for b in (begeniler or []) if b['id'] == begeni_id), None)
    if not edit_data:
        messages.error(request, f"Yorum beğenisi #{begeni_id} bulunamadı.")
        return redirect('yonetim_yorum_begenileri')
    if request.method == 'POST':
        yorum_id = request.POST.get('yorum_id', '')
        user_id = request.POST.get('user_id', '')
        try:
            bl.update_yorum_begeni_detail(begeni_id, yorum_id, user_id)
            messages.success(request, f"Yorum beğenisi #{begeni_id} güncellendi.")
            return redirect('yonetim_yorum_begenileri')
        except bl.ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'yonetim/yorum_begeniler.html', {
        'begeniler': begeniler,
        'yorumlar': comments,
        'kullanicilar': users,
        'edit_data': edit_data,
        'active_tab': 'yorum_begenileri'
    })

@superuser_required
def yorum_begeni_sil(request, begeni_id):
    if request.method != 'POST':
        return redirect('yonetim_yorum_begenileri')
    try:
        bl.remove_yorum_begeni(begeni_id)
        messages.success(request, f"Yorum beğenisi #{begeni_id} silindi.")
    except bl.ValidationError as e:
        messages.error(request, str(e))
    return redirect('yonetim_yorum_begenileri')
