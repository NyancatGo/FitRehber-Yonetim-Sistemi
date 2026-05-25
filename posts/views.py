"""
Ana FitRehber platformunun mevcut kullanıcı arayüzü rotaları.

BTS304 ödev değerlendirme kapsamındaki N-Tier yönetim modülü bu dosya
değildir; ödev modülü için posts/views_yonetim.py kullanılır.
"""

from pathlib import Path
import re
import secrets
from urllib.parse import urlencode, urlsplit
from xml.sax.saxutils import escape as xml_escape

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.db.models import Q, Count, Sum, Prefetch, Max
from django.core.cache import cache
from django.core.exceptions import ValidationError

# --- ANA SAYFA ---
from django.contrib.auth.decorators import login_required
from .models import Icerik, Kategori, Yorum, Profil, MobileOAuthCode, ROZET_HEDEFLERI
from .forms import (
    PROFILE_IMAGE_EXTENSIONS,
    IcerikFormu,
    KullaniciGuncellemeFormu,
    KullaniciKayitFormu,
    OnboardingForm,
    ProfilFormu,
    YorumFormu,
    validate_image_upload,
)
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from allauth.account.models import EmailAddress
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, StreamingHttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from .decorators import check_ban, check_timeout
from .image_optimization import close_file_field, delete_media_file, optimize_profile_photo, optimize_uploaded_image
from .seo import (
    absolute_url,
    blog_posting_json_ld,
    breadcrumb_json_ld,
    clean_text,
    content_description,
    content_image_url,
    discussion_posting_json_ld,
)
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from core.security_utils import get_client_ip

PROFILE_CONTENT_PAGE_SIZE = 3
PROFILE_CONTENT_TYPES = {'paylasim', 'kaydedilen', 'begeni'}
MOBILE_OAUTH_STATE_RE = re.compile(r'^[A-Za-z0-9_-]{32,128}$')
MOBILE_OAUTH_CHALLENGE_RE = re.compile(r'^[A-Za-z0-9_-]{43}$')
MOBILE_OAUTH_CODE_TTL = timedelta(minutes=5)

# Native mobil uygulamanin deep link adresi. redirect_uri verilmezse
# (eski uygulama surumleri) bu varsayilan kullanilir.
MOBILE_OAUTH_NATIVE_REDIRECT = 'fitrehber://oauth/callback'


class MobileAppRedirect(HttpResponseRedirect):
    allowed_schemes = ['http', 'https', 'fitrehber']


def _mobile_oauth_params_from_get(request):
    """GET parametrelerinden state ve code_challenge okur ve doğrular."""
    state = request.GET.get('state', '').strip()
    code_challenge = request.GET.get('code_challenge', '').strip()
    if not MOBILE_OAUTH_STATE_RE.fullmatch(state):
        return None, None, 'Geçersiz mobil giriş state değeri.'
    if not MOBILE_OAUTH_CHALLENGE_RE.fullmatch(code_challenge):
        return None, None, 'Geçersiz mobil giriş code challenge değeri.'
    return state, code_challenge, None


def _mobile_oauth_params_from_session(request):
    """Django session'dan state ve code_challenge okur, doğrular ve temizler."""
    state = (request.session.pop('mobile_oauth_state', '') or '').strip()
    code_challenge = (request.session.pop('mobile_oauth_code_challenge', '') or '').strip()
    if not state or not code_challenge:
        return None, None, None          # session'da veri yok → fallback'e düş
    if not MOBILE_OAUTH_STATE_RE.fullmatch(state):
        return None, None, 'Geçersiz mobil giriş state değeri.'
    if not MOBILE_OAUTH_CHALLENGE_RE.fullmatch(code_challenge):
        return None, None, 'Geçersiz mobil giriş code challenge değeri.'
    return state, code_challenge, None


def _validate_mobile_oauth_redirect_uri(raw):
    """Mobil/web OAuth dönüş adresini doğrular (open redirect koruması).

    - Boş/None → varsayılan native deep link (eski uygulama sürümleriyle uyum).
    - fitrehber://oauth/callback → native uygulama, kabul.
    - http(s) + localhost / 127.0.0.1 → Flutter web geliştirme ortamı, kabul.
    - http(s) + settings.MOBILE_OAUTH_WEB_ORIGINS içindeki origin → prod web, kabul.
    - Diğer her şey → None (geçersiz, çağıran 400 döndürmeli).

    Dönen değer query/fragment'tan arındırılmış, yeniden kurulmuş temiz adrestir.
    """
    if not raw:
        return MOBILE_OAUTH_NATIVE_REDIRECT
    raw = raw.strip()
    if raw == MOBILE_OAUTH_NATIVE_REDIRECT:
        return MOBILE_OAUTH_NATIVE_REDIRECT
    parts = urlsplit(raw)
    if parts.scheme in ('http', 'https') and parts.hostname:
        # Temiz adres: yalnız scheme + netloc + path; query/fragment atılır.
        clean = f"{parts.scheme}://{parts.netloc}{parts.path or '/'}"
        host = parts.hostname.lower()
        if host in ('localhost', '127.0.0.1'):
            return clean
        allowed = getattr(settings, 'MOBILE_OAUTH_WEB_ORIGINS', ())
        if f"{parts.scheme}://{parts.netloc}" in allowed:
            return clean
    return None


def mobile_google_start(request):
    state, code_challenge, error = _mobile_oauth_params_from_get(request)
    if error:
        return HttpResponse(error, status=400)

    redirect_uri = _validate_mobile_oauth_redirect_uri(request.GET.get('redirect_uri'))
    if redirect_uri is None:
        return HttpResponse('Geçersiz mobil giriş redirect_uri değeri.', status=400)

    # Parametreleri session'a kaydet — allauth yönlendirmesi sırasında
    # URL query string kaybolsa bile callback'te session'dan okunabilecek.
    request.session['mobile_oauth_state'] = state
    request.session['mobile_oauth_code_challenge'] = code_challenge
    request.session['mobile_oauth_redirect_uri'] = redirect_uri

    # next URL'e artık parametreleri eklemiyoruz, session'dan okunacak.
    # Yine de geriye uyumluluk için query string'i de bırakıyoruz.
    next_query = urlencode({
        'state': state,
        'code_challenge': code_challenge,
        'redirect_uri': redirect_uri,
    })
    next_url = f"{reverse('mobile_auth_callback')}?{next_query}"
    login_query = urlencode({
        'process': 'login',
        'next': next_url,
    })
    login_url = f"{reverse('google_login')}?{login_query}"
    return redirect(login_url)


@login_required(login_url='/giris/')
def mobile_auth_callback(request):
    import traceback as _tb
    try:
        # Öncelik: session'dan oku (allauth yönlendirmesi query string'i kaybetse bile çalışır)
        state, code_challenge, error = _mobile_oauth_params_from_session(request)
        if state is None and error is None:
            # Session'da veri yoksa GET parametrelerine fallback (geriye uyumluluk)
            state, code_challenge, error = _mobile_oauth_params_from_get(request)
        if error:
            return HttpResponse(error, status=400)

        # redirect_uri: önce session, sonra GET fallback — her durumda yeniden doğrula.
        redirect_uri_raw = (
            request.session.pop('mobile_oauth_redirect_uri', '')
            or request.GET.get('redirect_uri', '')
        )
        redirect_uri = _validate_mobile_oauth_redirect_uri(redirect_uri_raw)
        if redirect_uri is None:
            return HttpResponse('Geçersiz mobil giriş redirect_uri değeri.', status=400)

        MobileOAuthCode.objects.filter(
            created_at__lt=timezone.now() - MOBILE_OAUTH_CODE_TTL,
        ).delete()
        MobileOAuthCode.objects.filter(user=request.user, state=state).delete()
        oauth_code = MobileOAuthCode.objects.create(
            user=request.user,
            code=secrets.token_urlsafe(32),
            state=state,
            code_challenge=code_challenge,
        )
        callback_query = urlencode({
            'code': oauth_code.code,
            'state': state,
        })

        if redirect_uri.startswith('fitrehber://'):
            # Native uygulama: deep link'i güzel ara sayfayla tetikle
            # (Chrome Custom Tabs redirect engelini aşmak için).
            callback_url = f"{redirect_uri}?{callback_query}"
            return render(request, 'mobile_redirect.html', {'callback_url': callback_url})

        # Flutter web: doğrudan 302 ile uygulamanın kendi URL'ine dön.
        separator = '&' if '?' in redirect_uri else '?'
        return redirect(f"{redirect_uri}{separator}{callback_query}")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("mobile_auth_callback failed")
        if settings.DEBUG:
            return HttpResponse(
                f"DEBUG mobile_auth_callback:\n\n{_tb.format_exc()}",
                status=500,
                content_type='text/plain',
            )
        return HttpResponse("Google giriş işlemi tamamlanamadı.", status=500)

# --- ANA SAYFA ---
def anasayfa(request):
    # Kategorileri menü için çekiyoruz
    kategoriler = Kategori.objects.all()
    secili_kategori = request.GET.get('kategori')

    # İçerikleri çek
    icerik_listesi = Icerik.objects.filter(tur='haber').select_related(
        'yazar__profil',
        'kategori',
    ).prefetch_related('begenenler', 'kaydedenler', 'yorumlar').order_by('-tarih')

    # Eğer kategori seçildiyse filtrele
    if secili_kategori:
        icerik_listesi = icerik_listesi.filter(kategori__id=secili_kategori)
    
    # Sayfalama (6'şarlı)
    paginator = Paginator(icerik_listesi, 6) 
    page = request.GET.get('page')
    try:
        icerikler = paginator.page(page)
    except PageNotAnInteger:
        icerikler = paginator.page(1)
    except EmptyPage:
        icerikler = paginator.page(paginator.num_pages)

    context = {
        'icerikler': icerikler,
        'kategoriler': kategoriler,
        'secili_kategori': int(secili_kategori) if secili_kategori else None,
        'seo_title': getattr(settings, 'DEFAULT_SEO_TITLE', 'FitRehber'),
        'seo_description': getattr(settings, 'DEFAULT_SEO_DESCRIPTION', ''),
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, '_anasayfa_icerik.html', context)

    return render(request, 'anasayfa.html', context)

# --- FORUM SAYFASI ---
def forum_sayfasi(request):
    # Kategorileri menü için çekiyoruz
    kategoriler = Kategori.objects.all()
    secili_kategori = request.GET.get('kategori')

    # Forum sorularını çek (yorum sayısı için prefetch)
    icerik_listesi = Icerik.objects.filter(tur='soru').select_related(
        'yazar__profil',
        'kategori',
    ).prefetch_related('yorumlar', 'begenenler', 'kaydedenler').order_by('-tarih')
    
    # Kategori filtresi
    if secili_kategori:
        icerik_listesi = icerik_listesi.filter(kategori__id=secili_kategori)
    
    # Sayfalama (10'arlı)
    paginator = Paginator(icerik_listesi, 10)
    page = request.GET.get('page')
    try:
        icerikler = paginator.page(page)
    except PageNotAnInteger:
        icerikler = paginator.page(1)
    except EmptyPage:
        icerikler = paginator.page(paginator.num_pages)

    context = {
        'icerikler': icerikler,
        'kategoriler': kategoriler,
        'secili_kategori': int(secili_kategori) if secili_kategori else None,
        'seo_title': 'FitRehber Topluluk | Fitness Soruları ve Deneyim Paylaşımı',
        'seo_description': (
            'FitRehber Topluluk; antrenman, beslenme, supplement ve sağlıklı yaşam '
            'konularında soru sorup deneyim paylaşabileceğiniz fitness forumudur.'
        ),
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, '_forum_icerik.html', context)

    return render(request, 'forum.html', context)

# --- DETAY SAYFASI ---
@check_ban
def detay(request, id):
    icerik = get_object_or_404(
        Icerik.objects.select_related('yazar__profil', 'kategori').prefetch_related(
            'begenenler',
            'kaydedenler',
        ),
        id=id,
    )
    
    if request.method == 'POST':
        # --- SUSTURULMA KONTROLÜ (SADECE YORUM YAPMAYA ÇALIŞIRSA ÇALIŞIR) ---
        if hasattr(request.user, 'profil') and request.user.profil.timeout_until and request.user.profil.timeout_until > timezone.now():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'mesaj': 'Geçici olarak susturulduğunuz için yorum yapamazsınız.'}, status=403)
            
            messages.error(request, "Geçici olarak susturulduğunuz için yorum yapamazsınız.")
            return redirect('detay', id=id)
        # --------------------------------------------------------------------

        form = YorumFormu(request.POST)
        if form.is_valid():
            yorum = form.save(commit=False)
            yorum.icerik = icerik
            yorum.yazar = request.user
            
            # EĞER BİR YANITSA, BABASININ BU İÇERİĞE AİT OLDUĞUNU DOĞRULA
            parent_id = request.POST.get('parent_id')
            if parent_id:
                if Yorum.objects.filter(id=parent_id, icerik=icerik).exists():
                    yorum.parent_id = parent_id
                else:
                    # Hatalı/hileli parent_id → root yorum olarak kaydet
                    yorum.parent_id = None
            
            yorum.save()

            # AJAX İsteği mi?
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                from django.template.loader import render_to_string
                
                depth = yorum.depth

                # İçerik türüne göre doğru yorum kartı şablonunu seç
                comment_template = 'yorum_karti_soru.html' if icerik.tur == 'soru' else 'yorum_karti.html'

                yorum_html = render_to_string(comment_template, {
                    'yorum': yorum,
                    'user': request.user,
                    'icerik': icerik,
                    'depth': depth
                }, request=request)

                return JsonResponse({
                    'success': True,
                    'html': yorum_html,
                    'parent_id': parent_id,
                    'mesaj': "Yorumunuz başarıyla eklendi."
                })

            # Yeni yorumun ID'sine göre anchor (çapa) ekleyerek sayfayı oraya kaydır
            anchor = f"#cevap-{yorum.id}" if icerik.tur == 'soru' else f"#comment-{yorum.id}"
            return redirect(reverse('detay', args=[id]) + anchor)
    else:
        form = YorumFormu()

    # Yorumları filtrele (Odaklanma mantığı)
    odak_id = request.GET.get('odak')
    if odak_id:
        # Sadece odaklanılan yorumu (ve dolaylı olarak altlarını) göster
        # Burada tek elemanlı bir liste veya queryset döndürüyoruz
        yorumlar = Yorum.objects.filter(id=odak_id).select_related('yazar__profil')
        is_focus_mode = True
    else:
        # Varsayılan: Sadece ana yorumları (parent'ı olmayanları) gönder
        # Template içindeki "if not yorum.parent" kontrolüne gerek kalmayacak (veya zararı olmaz)
        # Ama icerik.yorumlar.all yerine bunu kullanacağız
        yorumlar = icerik.yorumlar.filter(parent=None).select_related('yazar__profil').prefetch_related(
            'begenenler',
            'yanitlar__yazar',
            'yanitlar__yazar__profil',
            'yanitlar__begenenler',
            'yanitlar__yanitlar__yazar',
            'yanitlar__yanitlar__yazar__profil',
            'yanitlar__yanitlar__begenenler',
        ).order_by('-tarih')
        is_focus_mode = False

    # Eğer içerik türü 'soru' ise farklı, 'haber' ise eski şablonu kullan
    template_name = 'detay_soru.html' if icerik.tur == 'soru' else 'detay.html'
    seo_title = (
        f"{icerik.baslik} | FitRehber Topluluk"
        if icerik.tur == 'soru'
        else f"{icerik.baslik} | FitRehber"
    )
    seo_structured_data = (
        discussion_posting_json_ld(icerik, yorumlar)
        if icerik.tur == 'soru'
        else blog_posting_json_ld(icerik)
    )

    # Breadcrumb JSON-LD oluştur
    if icerik.tur == 'soru':
        seo_breadcrumb = breadcrumb_json_ld([
            {'name': 'Ana Sayfa', 'url': '/'},
            {'name': 'Forum', 'url': reverse('forum')},
            {'name': icerik.baslik, 'url': reverse('detay', args=[icerik.id])},
        ])
    else:
        seo_breadcrumb = breadcrumb_json_ld([
            {'name': 'Ana Sayfa', 'url': '/'},
            {'name': 'Blog', 'url': '/'},
            {'name': icerik.baslik, 'url': reverse('detay', args=[icerik.id])},
        ])

    return render(request, template_name, {
        'icerik': icerik,
        'form': form,
        'yorumlar': yorumlar,
        'is_focus_mode': is_focus_mode,
        'now': timezone.now(),
        'seo_title': seo_title,
        'seo_description': content_description(icerik),
        'seo_image': content_image_url(icerik),
        'seo_structured_data': seo_structured_data,
        'seo_breadcrumb': seo_breadcrumb,
    })
    
# --- KULLANICI İŞLEMLERİ ---
def kayit_ol(request):
    if request.method == 'POST':
        form = KullaniciKayitFormu(request.POST)
        if form.is_valid():
            ip = get_client_ip(request)
            signup_limit_key = f"signup_limit_{ip}"
            if cache.get(signup_limit_key):
                messages.error(request, "Bu cihazdan son 24 saat içinde zaten bir hesap oluşturulmuş.")
                return render(request, 'kayit.html', {'form': form})

            user = form.save(commit=False)
            user.is_active = False
            user.save()

            email_address, _ = EmailAddress.objects.update_or_create(
                user=user,
                email=user.email,
                defaults={'verified': False, 'primary': True},
            )
            
            try:
                email_address.send_confirmation(request, signup=True)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"E-posta onay linki gönderilemedi: {e}")
                user.delete()
                messages.error(
                    request,
                    "Doğrulama e-postası şu anda gönderilemedi. Lütfen biraz sonra tekrar deneyin.",
                )
                return render(request, 'kayit.html', {'form': form})

            cache.set(signup_limit_key, True, timeout=86400)

            # Sayfada kal, modal göster
            registered_at_ts = int(user.date_joined.timestamp())
            return render(request, 'kayit.html', {
                'form': KullaniciKayitFormu(),
                'verification_pending': True,
                'pending_email': user.email,
                'registered_at_ts': registered_at_ts,
            })
    else:
        initial_email = request.GET.get('email', '').strip()
        form = KullaniciKayitFormu(initial={'email': initial_email})
    return render(request, 'kayit.html', {'form': form})

def giris_yap(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        # Django authenticate, is_active=False olan kullanıcılarda None döner.
        # O yüzden el ile kontrol edip pasif kullanıcıya modal göstermeliyiz.
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        # Önce kullanıcıyı bul
        try:
            check_user = User.objects.get(username=username)
        except User.DoesNotExist:
            check_user = None
        
        # Kullanıcı var ama aktif değilse → şifre doğru mu kontrol et
        if check_user and not check_user.is_active and check_user.check_password(password):
            registered_at_ts = int(check_user.date_joined.timestamp())
            return render(request, 'giris.html', {
                'form': AuthenticationForm(),
                'verification_pending': True,
                'pending_email': check_user.email,
                'registered_at_ts': registered_at_ts,
            })
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # Banlı kullanıcı kontrolü - giriş yapmasını engelle
                if hasattr(user, 'profil') and user.profil.is_banned:
                    return render(request, 'banli.html', {'banned_username': user.username}, status=403)
                login(request, user)
                messages.info(request, f"Hoş geldin {username}!")
                return redirect('anasayfa')
    else:
        form = AuthenticationForm()
        for field in form.fields.values():
            field.widget.attrs['class'] = 'form-control'
    return render(request, 'giris.html', {'form': form})


def cikis_yap(request):
    logout(request)
    messages.info(request, "Çıkış yapıldı.")
    return redirect('anasayfa')

# --- İÇERİK EKLEME VE SİLME ---
@login_required(login_url='/giris/')
def onboarding(request):
    profil, _ = Profil.objects.get_or_create(user=request.user)
    if profil.is_onboarded:
        return redirect('anasayfa')

    if request.method == 'POST':
        form = OnboardingForm(request.POST, instance=profil, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil kurulumun tamamlandı. Hoş geldin!")
            return redirect('anasayfa')
    else:
        form = OnboardingForm(instance=profil, user=request.user)

    return render(request, 'onboarding.html', {'form': form})


@login_required(login_url='/giris/') 
@check_ban
def icerik_ekle(request):
    # URL üzerindeki tür bilgisini al (haber mi soru mu?)
    gelen_tur = request.GET.get('tur', 'soru') # Varsayılan: soru
    
    # --- YETKİ KONTROLÜ (KRİTİK) ---
    # Haber paylaşma yetkisi sadece süper kullanıcılardadır.
    if gelen_tur == 'haber' and not request.user.is_superuser:
        log_ihlali(request) # Logla
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})

    if request.method == 'POST':
        # --- SUSTURULMA KONTROLÜ (SADECE PAYLAŞMAYA BASARSA ÇALIŞIR) ---
        if hasattr(request.user, 'profil') and request.user.profil.timeout_until and request.user.profil.timeout_until > timezone.now():
            messages.error(request, "Geçici olarak susturulduğunuz için içerik paylaşamazsınız.")
            return redirect('icerik_ekle')
        # ---------------------------------------------------------------

        form = IcerikFormu(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            yeni_icerik = form.save(commit=False)
            yeni_icerik.yazar = request.user
            
            # Formda olmayan 'tur' alanını burada kontrollü set ediyoruz
            if request.user.is_superuser:
                # Admin her iki türü de paylaşabilir, query param neyse o olur
                yeni_icerik.tur = gelen_tur
            else:
                # Normal kullanıcı her halükarda 'soru' paylaşır (Bypass koruması)
                yeni_icerik.tur = 'soru'
                
            yeni_icerik.save()
            messages.success(request, "İçeriğin başarıyla paylaşıldı!")
            return redirect('detay', id=yeni_icerik.id)
    else:
        form = IcerikFormu(user=request.user)
    return render(request, 'ekle.html', {'form': form, 'now': timezone.now()})

@login_required
def icerik_sil(request, id):
    icerik = get_object_or_404(Icerik, id=id)
    if not request.user.is_superuser and icerik.yazar != request.user:
        log_ihlali(request) # Logla
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    tur = icerik.tur
    icerik.delete()
    messages.success(request, "İçerik başarıyla silindi.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        redirect_url = reverse('forum') if tur == 'soru' else reverse('anasayfa')
        return JsonResponse({'success': True, 'mesaj': 'İçerik başarıyla silindi.', 'redirect_url': redirect_url})

    if tur == 'soru':
        return redirect('forum')
    else:
        return redirect('anasayfa')

# --- İÇERİK DÜZENLEME ---
@login_required(login_url='/giris/')
@check_ban
def icerik_duzenle(request, id):
    icerik = get_object_or_404(Icerik, id=id)

    # Yetki kontrolü: Sadece yazar veya admin düzenleyebilir
    if not request.user.is_superuser and icerik.yazar != request.user:
        log_ihlali(request)
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})

    if request.method == 'POST':
        form = IcerikFormu(request.POST, request.FILES, instance=icerik, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "İçerik başarıyla güncellendi!")
            return redirect('detay', id=icerik.id)
    else:
        form = IcerikFormu(instance=icerik, user=request.user)

    return render(request, 'ekle.html', {
        'form': form,
        'now': timezone.now(),
        'edit_mode': True,
        'icerik': icerik,
    })

# --- PROFİL İŞLEMLERİ ---
def _profile_content_queryset(profil_sahibi, content_type):
    if content_type == 'paylasim':
        return Icerik.objects.filter(yazar=profil_sahibi).select_related(
            'yazar__profil',
            'kategori',
        ).order_by('-tarih')
    if content_type == 'kaydedilen':
        return profil_sahibi.kaydedilen_icerikler.all().select_related(
            'yazar__profil',
            'kategori',
        ).order_by('-tarih')
    if content_type == 'begeni':
        liked_comments = profil_sahibi.begendigi_yorumlar.all().select_related(
            'yazar__profil',
            'icerik',
        )
        liked_contents = profil_sahibi.begendigi_icerikler.all().select_related(
            'yazar__profil',
            'kategori',
        )
        items = [
            {'kind': 'yorum', 'obj': yorum, 'tarih': yorum.tarih}
            for yorum in liked_comments
        ]
        items.extend(
            {'kind': 'icerik', 'obj': icerik, 'tarih': icerik.tarih}
            for icerik in liked_contents
        )
        return sorted(items, key=lambda item: item['tarih'], reverse=True)
    return Icerik.objects.none()


def _paginate_profile_content(queryset, page_number):
    paginator = Paginator(queryset, PROFILE_CONTENT_PAGE_SIZE)
    return paginator.get_page(page_number or 1)


def _format_metric(value, suffix="", fraction_digits=0):
    if value is None:
        return None

    numeric = float(value)
    if numeric.is_integer() and fraction_digits == 0:
        text = f"{int(numeric)}"
    else:
        text = f"{numeric:.{fraction_digits}f}".rstrip("0").rstrip(".")

    return f"{text} {suffix}".strip()


def _build_biometric_summary(profil):
    height = float(profil.boy) if profil.boy else None
    weight = float(profil.kilo) if profil.kilo else None
    target = float(profil.hedef_kilo) if profil.hedef_kilo else None

    bmi = None
    bmi_category = "Eksik veri"
    if height and weight and height > 0:
        meters = height / 100
        bmi = weight / (meters * meters)
        if bmi < 18.5:
            bmi_category = "Düşük"
        elif bmi < 25:
            bmi_category = "Dengeli"
        elif bmi < 30:
            bmi_category = "Yüksek"
        else:
            bmi_category = "Çok yüksek"

    # Yolculuk-bazli progress (mobile profile_screen.dart ile birebir ayni):
    #   toplam_yol  = |baslangic - hedef|
    #   gidilen_yol = if hedef_asagi: (baslangic - mevcut), else (mevcut - baslangic)
    #   progress    = clamp(gidilen / toplam, 0, 1) * 100
    # baslangic_kilo NULL ise fallback olarak mevcut kilo alinir; bu durumda
    # gidilen=0 olur, progress=0. Kullanici yolun basinda.
    has_goal = bool(weight and target and target > 0)
    target_progress = 0
    target_status = "Hedef kilo eklenmedi"
    if has_goal:
        raw_start = float(profil.baslangic_kilo) if profil.baslangic_kilo else None
        start = raw_start if raw_start and raw_start > 0 else weight
        total_path = abs(start - target)
        difference = abs(weight - target)
        formatted_difference = _format_metric(difference, "kg", 1)

        if difference < 0.1:
            # Mevcut == hedef → barı dolu goster, status sabit.
            target_status = "Hedef kilodasın"
            target_progress = 100
        elif total_path < 0.05:
            # Baslangic = hedef ama mevcut farkli (sapma) → progress hesaplanamaz.
            target_progress = 0
            if weight > target:
                target_status = f"Hedefe {formatted_difference} kaldı"
            else:
                target_status = f"Hedefe {formatted_difference} artış kaldı"
        else:
            going_down = target < start
            traveled = (start - weight) if going_down else (weight - start)
            ratio = max(0.0, min(1.0, traveled / total_path))
            target_progress = int(round(ratio * 100))
            if weight > target:
                target_status = f"Hedefe {formatted_difference} kaldı"
            else:
                target_status = f"Hedefe {formatted_difference} artış kaldı"

    return {
        "height": _format_metric(height, "cm"),
        "weight": _format_metric(weight, "kg", 1),
        "target": _format_metric(target, "kg", 1),
        "goal": profil.fitness_hedefi,
        "birth_date": profil.dogum_tarihi,
        "bmi": _format_metric(bmi, "", 1),
        "bmi_category": bmi_category,
        "has_goal": has_goal,
        "target_progress": target_progress,
        "target_status": target_status,
    }


def profil_sayfasi(request, username):
    from .models import GunlukAktivite, Aktivite
    profil_sahibi = get_object_or_404(User.objects.select_related('profil'), username=username)
    # Profil yoksa 404 değil, signal ile oluşturulmuş olmalı
    if not hasattr(profil_sahibi, 'profil'):
        Profil.objects.get_or_create(user=profil_sahibi)
    
    icerikler = _profile_content_queryset(profil_sahibi, 'paylasim')
    profile_content_page = _paginate_profile_content(icerikler, 1)
    toplam_icerik_sayisi = profile_content_page.paginator.count
    
    # Bugün (Local time ile)
    today = timezone.localtime(timezone.now()).date()
    gunluk_veriler = []
    
    # Kullanıcının kayıt tarihi (Local time ile)
    join_date = timezone.localtime(profil_sahibi.date_joined).date()
    # 30 gün öncesi
    thirty_days_ago = today - timedelta(days=29)
    
    # Başlangıç tarihini belirle: Eğer üyelik yeni ise üyelik tarihi, eskiyse 30 gün öncesi
    if join_date > thirty_days_ago:
        start_date = join_date
    else:
        start_date = thirty_days_ago
        
    # Kaç gün göstereceğimizi hesapla
    days_to_show = (today - start_date).days + 1 # +1 çünkü bugün de dahil
    
    # Döngü aralığını belirle
    # range(days_to_show - 1, -1, -1) -> [N-1, ..., 0]
    # today - timedelta(0) = today
    
    son_gunler = [today - timedelta(days=i) for i in range(days_to_show - 1, -1, -1)]
    
    aktiviteler = GunlukAktivite.objects.filter(
        user=profil_sahibi, 
        tarih__gte=son_gunler[0]
    ).values('tarih', 'sure_dk')
    
    aktivite_sozlugu = {a['tarih']: a['sure_dk'] for a in aktiviteler}
    
    aylar_tr = {
        1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis', 5: 'May', 6: 'Haz',
        7: 'Tem', 8: 'Ağu', 9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'
    }

    for tarih in son_gunler:
        sure = aktivite_sozlugu.get(tarih, 0)
        tarih_formatli = f"{tarih.day} {aylar_tr[tarih.month]}"
        gunluk_veriler.append({
            'tarih': tarih_formatli,
            'gun': tarih.day,
            'ay': aylar_tr[tarih.month],
            'sure': sure
        })
    
    # Ortalama hesapla
    # Artık 30'a değil, geçen gün sayısına bölüyoruz (daha mantıklı)
    toplam_sure = sum(d['sure'] for d in gunluk_veriler)
    bolen = len(gunluk_veriler) if len(gunluk_veriler) > 0 else 1
    gunluk_ortalama = int(toplam_sure / bolen)

    # İstatistikler
    toplam_soru = Icerik.objects.filter(yazar=profil_sahibi, tur='soru').count()
    toplam_yorum = profil_sahibi.yazdigi_yorumlar.count()
    # Yorum modeline baktım: yazar = ForeignKey(User). related_name yok, default 'yorum_set'.

    # Toplam Beğeni (Yorumlarına gelen beğeniler)
    # Performanslı yöntem:
    from django.db.models import Count
    toplam_begeni_cache_key = f"profil:{profil_sahibi.id}:toplam_begeni"
    toplam_begeni = cache.get(toplam_begeni_cache_key)
    if toplam_begeni is None:
        toplam_begeni = Yorum.objects.filter(yazar=profil_sahibi).aggregate(
            total=Count('begenenler')
        )['total'] or 0
        cache.set(toplam_begeni_cache_key, toplam_begeni, 300)

    # Rozet İlerlemeleri
    
    # --- İSTATİSTİKLER (GÜNCELLENDİ) ---
    # 1. Şart: Toplam Soru Sayısı - SADECE SORULARI SAY (Rozet için lazım)
    toplam_soru = icerikler.filter(tur='soru').count()
    
    # 2. Şart: Toplam Yorum Sayısı (Zaten vardı)
    toplam_yorum = Yorum.objects.filter(yazar=profil_sahibi).count() # profil_sahibi.yazdigi_yorumlar.count() da olur ama modelde related_name yoksa bu daha guvenli
    # Üst satırda `profil_sahibi.yazdigi_yorumlar.count()` kullanılmıştı, onu tekrar `Yorum.objects...` ile düzeltebiliriz ya da olduğu gibi bırakabiliriz ama view'da daha önce `profil_sahibi.yazdigi_yorumlar.count()` vardı.
    # Kullanıcı isteğinde `Yorum.objects.filter(yazar=profil_sahibi).count()` var. Ben de onu kullanacağım.
    
    # 3. Şart: Yaptığı Beğeniler (yorum + içerik beğenileri)
    yapilan_begeni_sayisi = (
        profil_sahibi.begendigi_yorumlar.count()
        + profil_sahibi.begendigi_icerikler.count()
    )

    # --- ROZET İLERLEMELERİ (YENİ MANTIK) ---
    def calc_progress(current, target):
        if target == 0: return 0
        if current >= target: return 100
        return int((current / target) * 100)

    # Aktif Rozeti İçin Detaylı İlerlemeler
    aktif_progress_soru = calc_progress(toplam_soru, 10)       # Hedef: 10 Soru
    aktif_progress_yorum = calc_progress(toplam_yorum, 15)     # Hedef: 15 Yorum
    aktif_progress_begeni = calc_progress(yapilan_begeni_sayisi, 20) # Hedef: 20 Beğeni
    
    # Ana ilerleme çubuğu için EN DÜŞÜK olanı baz alıyoruz (Biri bile eksikse rozet açılmaz)
    aktif_genel_progress = min(aktif_progress_soru, aktif_progress_yorum, aktif_progress_begeni)

    h = ROZET_HEDEFLERI
    rozetler = {
        'ilk_adim': calc_progress(toplam_soru, h['ilk_adim']['soru']),
        
        'aktif': aktif_genel_progress,
        'aktif_detay': {
            'soru': aktif_progress_soru,
            'yorum': aktif_progress_yorum,
            'begeni': aktif_progress_begeni
        },
        
        'begenme': calc_progress(yapilan_begeni_sayisi, h['begenme']['begeni']),
        
        'populer': calc_progress(toplam_soru, h['populer']['soru']),
        'konuskan': calc_progress(toplam_yorum, h['konuskan']['yorum']),
        
        'vip_soru': calc_progress(toplam_soru, h['vip']['soru']),
        'vip_yorum': calc_progress(toplam_yorum, h['vip']['yorum']),
        'vip_begeni': calc_progress(yapilan_begeni_sayisi, h['vip']['begeni']),
    }

    # Aktivite Akışı (Timeline) - ARTIK VERİTABANINDAN ÇEKİYORUZ
    # Aktivite modelinden son 5 kaydı getir
    aktiviteler_timeline = Aktivite.objects.filter(user=profil_sahibi).select_related(
        'icerik',
        'icerik__yazar__profil',
        'yorum',
        'yorum__yazar__profil',
    ).order_by('-tarih')[:5]
    
    # Frontend için veri hazırlığı (ikon ve renkler için)
    # Modelde bu bilgileri tutmadık, burada basitçe ekleyebiliriz veya template'de halledebiliriz.
    # Template'de halletmek daha temiz. Modelde 'tur' alanı var zaten.

    profile_about = getattr(profil_sahibi.profil, 'hakkinda', '') if hasattr(profil_sahibi, 'profil') else ''
    biyometri = _build_biometric_summary(profil_sahibi.profil)

    return render(request, 'profil.html', {
        'profil_sahibi': profil_sahibi, 
        'icerikler': profile_content_page.object_list,
        'profile_content_items': profile_content_page.object_list,
        'profile_content_page': profile_content_page,
        'profile_content_total_pages': profile_content_page.paginator.num_pages,
        'profile_content_total_count': profile_content_page.paginator.count,
        'toplam_icerik_sayisi': toplam_icerik_sayisi,
        'gunluk_aktivite_verisi': gunluk_veriler,
        'gunluk_ortalama': gunluk_ortalama,
        'toplam_soru': toplam_soru,
        'toplam_yorum': toplam_yorum,
        'toplam_begeni': toplam_begeni,
        'yapilan_begeni_sayisi': yapilan_begeni_sayisi,
        'rozetler': rozetler,
        'aktiviteler_timeline': aktiviteler_timeline,
        'biyometri': biyometri,
        'seo_title': f"{profil_sahibi.username} | FitRehber Profili",
        'seo_description': clean_text(
            profile_about or f"{profil_sahibi.username} kullanıcısının FitRehber profilini ve paylaşımlarını inceleyin.",
            max_chars=160,
        ),
    })


def profil_icerikleri(request, username):
    profil_sahibi = get_object_or_404(User.objects.select_related('profil'), username=username)
    content_type = request.GET.get('type', 'paylasim')
    if content_type not in PROFILE_CONTENT_TYPES:
        return JsonResponse({'error': 'Geçersiz içerik türü.'}, status=400)

    if content_type in {'kaydedilen', 'begeni'} and request.user != profil_sahibi:
        return JsonResponse({'error': 'Bu listeyi sadece profil sahibi görebilir.'}, status=403)

    page_obj = _paginate_profile_content(
        _profile_content_queryset(profil_sahibi, content_type),
        request.GET.get('page', 1),
    )
    html = render_to_string(
        '_profil_content_items.html',
        {
            'content_type': content_type,
            'content_items': page_obj.object_list,
            'profil_sahibi': profil_sahibi,
        },
        request=request,
    )

    return JsonResponse({
        'html': html,
        'type': content_type,
        'page': page_obj.number,
        'total_pages': page_obj.paginator.num_pages,
        'total_count': page_obj.paginator.count,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
    })

@login_required(login_url='/giris/')
def profil_duzenle(request):
    profil, created = Profil.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = KullaniciGuncellemeFormu(request.POST, instance=request.user)
        profil_form = ProfilFormu(request.POST, request.FILES, instance=profil)
        
        if user_form.is_valid() and profil_form.is_valid():
            user_form.save()
            profil_form.save()
            messages.success(request, "Profilin başarıyla güncellendi! ✅")
            return redirect('profil_duzenle')
    else:
        user_form = KullaniciGuncellemeFormu(instance=request.user)
        profil_form = ProfilFormu(instance=profil)

    return render(request, 'profil_duzenle.html', {
        'user_form': user_form, 
        'profil_form': profil_form
    })


@login_required(login_url='/giris/')
@require_POST
def profil_foto_guncelle(request):
    profil, _ = Profil.objects.get_or_create(user=request.user)
    upload = request.FILES.get('foto')

    if not upload:
        messages.error(request, "Lütfen bir profil fotoğrafı seç.")
        return redirect('profil', username=request.user.username)

    try:
        validate_image_upload(upload, allowed_extensions=PROFILE_IMAGE_EXTENSIONS)
        old_photo = profil.foto if getattr(profil, 'foto', None) else None
        old_photo_name = old_photo.name if old_photo else ''
        optimized_photo = optimize_profile_photo(upload, upload.name)
        profil.foto = optimized_photo.file
        profil.save(update_fields=['foto'])

        new_photo_name = profil.foto.name if profil.foto else ''
        if old_photo_name and old_photo_name != new_photo_name:
            close_file_field(old_photo)
            delete_media_file(old_photo_name)
    except ValidationError as exc:
        for error in exc.messages:
            messages.error(request, error)
    except OSError:
        messages.error(request, "Profil fotoğrafı kaydedilemedi. Dosya adını değiştirip tekrar deneyin.")
    else:
        messages.success(request, "Profil fotoğrafın güncellendi.")

    return redirect('profil', username=request.user.username)


@login_required(login_url='/giris/')
@require_POST
def profil_foto_sil(request):
    profil, _ = Profil.objects.get_or_create(user=request.user)
    old_photo = profil.foto if getattr(profil, 'foto', None) else None
    old_photo_name = old_photo.name if old_photo else ''

    if not old_photo_name:
        messages.info(request, "Kaldırılacak bir profil fotoğrafın yok.")
        return redirect('profil', username=request.user.username)

    profil.foto = None
    profil.save(update_fields=['foto'])

    try:
        close_file_field(old_photo)
        delete_media_file(old_photo_name)
    except OSError:
        messages.warning(request, "Profil fotoğrafın kaldırıldı, eski dosya daha sonra temizlenebilir.")
    else:
        messages.success(request, "Profil fotoğrafın kaldırıldı.")

    return redirect('profil', username=request.user.username)

# --- BEĞENİ VE KAYDETME ---
@login_required(login_url='/giris/')
@check_ban
@require_POST
def yorum_begen(request, id):
    yorum = get_object_or_404(Yorum, id=id)
    
    if yorum.begenenler.filter(id=request.user.id).exists():
        yorum.begenenler.remove(request.user)
        begenildi = False
    else:
        yorum.begenenler.add(request.user)
        begenildi = True
        
    # Cache invalidation: beğenilen yorumun yazarının profil cache'ini temizle
    begeni_cache_key = f"profil:{yorum.yazar.id}:toplam_begeni"
    cache.delete(begeni_cache_key)

    return JsonResponse({
        'begenildi': begenildi,
        'sayi': yorum.begenenler.count()
    })

@login_required(login_url='/giris/')
@check_ban
@require_POST
def icerik_kaydet(request, id):
    icerik = get_object_or_404(Icerik, id=id)
    
    if icerik.kaydedenler.filter(id=request.user.id).exists():
        icerik.kaydedenler.remove(request.user)
        kaydedildi = False
    else:
        icerik.kaydedenler.add(request.user)
        kaydedildi = True
        
    return JsonResponse({'kaydedildi': kaydedildi})

@login_required(login_url='/giris/')
@check_ban
@require_POST
def icerik_begen(request, id):
    icerik = get_object_or_404(Icerik, id=id)

    if icerik.begenenler.filter(id=request.user.id).exists():
        icerik.begenenler.remove(request.user)
        begenildi = False
    else:
        icerik.begenenler.add(request.user)
        begenildi = True

    return JsonResponse({
        'begenildi': begenildi,
        'sayi': icerik.begenenler.count(),
    })

@login_required
def yorum_sil(request, id):
    yorum = get_object_or_404(Yorum, id=id)
    
    if request.user.is_superuser or request.user == yorum.yazar:
        yorum.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'mesaj': 'Yorum başarıyla silindi.'})
        return redirect(request.META.get('HTTP_REFERER', 'anasayfa')) # Fallback
    
    # Yetkisiz erişim - AJAX ise hata mesajı, değilse kilit ekranı
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'mesaj': 'Bu yorumu silme yetkiniz yok.'}, status=403)
    
    log_ihlali(request) # Logla
    return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})

# --- AKTİVİTE TAKİP ---

# Aktivite takibi api.py'a taşındı.

# --- ARAMA MOTORU (YENİ & HIZLI VERSİYON) ---
def arama(request):
    query = request.GET.get('q', '').strip()
    sonuclar_qs = Icerik.objects.none()
    
    if query:
        sonuclar_qs = Icerik.objects.filter(
            Q(baslik__icontains=query) | Q(yazi__icontains=query)
        ).order_by('-tarih')
    
    paginator = Paginator(sonuclar_qs, 10)
    sayfa = request.GET.get('sayfa', 1)
    try:
        sonuclar = paginator.page(sayfa)
    except (PageNotAnInteger, EmptyPage):
        sonuclar = paginator.page(1)
    
    return render(request, 'arama.html', {'sonuclar': sonuclar, 'query': query, 'toplam_sonuc': paginator.count})

# --- KURALLAR SAYFASI ---
def kurallar(request):
    return render(request, 'kurallar.html', {
        'seo_title': 'FitRehber Topluluk Kuralları',
        'seo_description': 'FitRehber topluluğunda güvenli, saygılı ve kaynaklı bilgi paylaşımı için kurallar.',
    })


def robots_txt(request):
    disallowed_paths = [
        '/admin/',
        '/yonetim/',
        '/admin/islem/',
        '/admin/islem/ban/',
        '/admin/islem/timeout/',
        '/admin/islem/sil/',
        '/yonetim/kullanici/',
        '/yonetim/guvenlik-kayitlari/',
        '/yonetim/indir/',
        '/ckeditor-yukle/',
        '/aktivite-kaydet/',
        '/canli-arama/',
        '/dogrulama-gonder/',
        '/profil-foto/',
        '/sil/',
        '/duzenle/',
        '/begen/',
        '/kaydet/',
        '/yorum-sil/',
        '/cikis/',
    ]
    lines = ['User-agent: *']
    lines.extend(f'Disallow: {path}' for path in disallowed_paths)
    lines.extend(['', f'Sitemap: {absolute_url("/sitemap.xml")}', ''])
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


def google_site_verification(request):
    return HttpResponse(
        'google-site-verification: google4c81f11de67ce22.html',
        content_type='text/html; charset=utf-8',
    )


def _sitemap_entry(path, lastmod=None, changefreq='weekly', priority='0.5'):
    loc = xml_escape(absolute_url(path))
    parts = ['  <url>', f'    <loc>{loc}</loc>']
    if lastmod:
        parts.append(f'    <lastmod>{timezone.localtime(lastmod).date().isoformat()}</lastmod>')
    parts.extend([
        f'    <changefreq>{changefreq}</changefreq>',
        f'    <priority>{priority}</priority>',
        '  </url>',
    ])
    return '\n'.join(parts)


def sitemap_xml(request):
    latest_content_date = Icerik.objects.aggregate(last=Max('tarih'))['last']
    entries = [
        _sitemap_entry(reverse('anasayfa'), latest_content_date, 'daily', '1.0'),
        _sitemap_entry(reverse('forum'), latest_content_date, 'daily', '0.8'),
        _sitemap_entry(reverse('kurallar'), None, 'monthly', '0.3'),
    ]

    # Profil sayfalari - aktif kullanicilar
    for user in User.objects.filter(is_active=True).only('username', 'date_joined').iterator(chunk_size=500):
        entries.append(_sitemap_entry(
            reverse('profil', args=[user.username]),
            user.date_joined,
            'monthly',
            '0.5'
        ))

    # Icerikler - optimize query
    for icerik in Icerik.objects.filter(tur__in=['haber', 'soru']).only('id', 'tur', 'tarih').order_by('-tarih').iterator(chunk_size=500):
        priority = '0.8' if icerik.tur == 'haber' else '0.6'
        entries.append(_sitemap_entry(reverse('detay', args=[icerik.id]), icerik.tarih, 'weekly', priority))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{chr(10).join(entries)}\n"
        '</urlset>\n'
    )
    return HttpResponse(xml, content_type='application/xml; charset=utf-8')

# --- ADMIN MONITOR DASHBOARD ---
from django.contrib.auth.decorators import user_passes_test
from .models import Aktivite, GunlukAktivite

def log_ihlali(request):
    """Güvenlik ihlalini veritabanına kaydeder."""
    from .models import GuvenlikIhlali
    ip = get_client_ip(request)
    GuvenlikIhlali.objects.create(
        user=request.user if request.user.is_authenticated else None,
        ip_adresi=ip,
        yol=request.get_full_path(),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

@login_required
def admin_monitor(request):
    if not request.user.is_superuser:
        log_ihlali(request)
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    
    # Güvenlik İhlallerini getir
    from .models import GuvenlikIhlali
    son_ihlaller = GuvenlikIhlali.objects.all()[:10]
    
    # Arama ve filtre
    arama = request.GET.get('q', '').strip()
    # ... rest of the view
    filtre = request.GET.get('filtre', 'hepsi')
    
    # Tüm kullanıcıları al (admin hariç)
    kullanicilar = User.objects.filter(is_superuser=False).select_related('profil').annotate(
        icerik_sayisi=Count('icerik', distinct=True),
        yorum_sayisi=Count('yazdigi_yorumlar', distinct=True),
    ).order_by('-date_joined')
    
    # Arama
    if arama:
        kullanicilar = kullanicilar.filter(
            Q(username__icontains=arama) | Q(email__icontains=arama)
        )
    
    # Filtre
    now = timezone.now()
    if filtre == 'banli':
        kullanicilar = kullanicilar.filter(profil__is_banned=True)
    elif filtre == 'susturulmus':
        kullanicilar = kullanicilar.filter(profil__timeout_until__gt=now)
    elif filtre == 'normal':
        kullanicilar = kullanicilar.filter(is_active=True, profil__is_banned=False).exclude(profil__timeout_until__gt=now)
    elif filtre == 'pasif':
        kullanicilar = kullanicilar.filter(is_active=False)
    
    # Her kullanıcının son aktivitesini al
    kullanici_ids = kullanicilar.values_list('id', flat=True)
    son_aktiviteler = {}
    for akt in Aktivite.objects.filter(user_id__in=kullanici_ids).values('user_id').annotate(
        son_tarih=Max('tarih')
    ):
        son_aktiviteler[akt['user_id']] = akt['son_tarih']
    
    # Kullanıcı listesi
    kullanici_listesi = []
    for k in kullanicilar:
        durum = 'normal'
        durum_text = 'Aktif'
        
        has_profil = hasattr(k, 'profil')
        
        if has_profil and k.profil.is_banned:
            durum = 'banli'
            durum_text = 'Banlı'
        elif not k.is_active:
            durum = 'pasif'
            durum_text = 'Onaysız (Pasif)'
        elif has_profil and k.profil.timeout_until and k.profil.timeout_until > now:
            durum = 'susturulmus'
            durum_text = 'Susturulmuş'
        
        kullanici_listesi.append({
            'user': k,
            'durum': durum,
            'durum_text': durum_text,
            'icerik_sayisi': k.icerik_sayisi,
            'yorum_sayisi': k.yorum_sayisi,
            'son_aktivite': son_aktiviteler.get(k.id),
            'timeout_bitis': k.profil.timeout_until if has_profil and durum == 'susturulmus' else None,
        })
    
    # İstatistikler
    toplam_kullanici = User.objects.filter(is_superuser=False).count()
    banli_sayisi = Profil.objects.filter(is_banned=True).count()
    susturulmus_sayisi = Profil.objects.filter(timeout_until__gt=now).count()
    pasif_sayisi = User.objects.filter(is_superuser=False, is_active=False).count()
    bugun_aktif = GunlukAktivite.objects.filter(tarih=now.date()).values('user').distinct().count()
    
    # Paginate
    paginator = Paginator(kullanici_listesi, 20)
    sayfa = request.GET.get('sayfa', 1)
    try:
        kullanicilar_page = paginator.page(sayfa)
    except (PageNotAnInteger, EmptyPage):
        kullanicilar_page = paginator.page(1)
    
    context = {
        'kullanicilar': kullanicilar_page,
        'toplam_kullanici': toplam_kullanici,
        'banli_sayisi': banli_sayisi,
        'susturulmus_sayisi': susturulmus_sayisi,
        'pasif_sayisi': pasif_sayisi,
        'bugun_aktif': bugun_aktif,
        'arama': arama,
        'filtre': filtre,
        'now': now,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, '_admin_user_list.html', context)

    return render(request, 'admin_monitor.html', context)

@login_required
@require_POST
def admin_delete_user(request, user_id):
    """Kullanıcıyı ve tüm verilerini kalıcı olarak siler."""
    if not request.user.is_superuser:
        log_ihlali(request)
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    
    hedef_user = get_object_or_404(User.objects.select_related('profil'), id=user_id)
    
    # Admin kendini silemesin
    if hedef_user.is_superuser:
        messages.error(request, "Admin hesapları silinemez!")
        return redirect('admin_monitor')
    
    username = hedef_user.username
    hedef_user.delete()  # Cascade ile tüm ilişkili veriler de silinir
    
    import logging
    logging.getLogger(__name__).warning(f"Kullanıcı '{username}' (ID: {user_id}) admin tarafından kalıcı olarak silindi.")
    
    messages.success(request, f"'{username}' kullanıcısı ve tüm verileri kalıcı olarak silindi.")
    return redirect('admin_monitor')

@login_required
def admin_security_logs(request):
    """Tüm güvenlik ihlallerini detaylı olarak listeler."""
    if not request.user.is_superuser:
        log_ihlali(request) # Logla
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    
    from .models import GuvenlikIhlali
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    ihlaller_listesi = GuvenlikIhlali.objects.all().order_by('-tarih')
    
    # Sayfalama
    paginator = Paginator(ihlaller_listesi, 30) # Sayfa başı 30 kayıt
    page = request.GET.get('sayfa')
    try:
        ihlaller = paginator.page(page)
    except PageNotAnInteger:
        ihlaller = paginator.page(1)
    except EmptyPage:
        ihlaller = paginator.page(paginator.num_pages)
        
    return render(request, 'admin_security_logs.html', {'ihlaller': ihlaller})

@login_required
def admin_user_detail(request, user_id):
    if not request.user.is_superuser:
        log_ihlali(request) # Logla
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    from django.db.models import Count, Sum
    hedef_user = get_object_or_404(User, id=user_id)
    Profil.objects.get_or_create(user=hedef_user)
    
    # Kullanıcı durumu
    now = timezone.now()
    durum = 'normal'
    durum_text = 'Aktif'
    if hedef_user.profil.is_banned:
        durum = 'banli'
        durum_text = 'Banlı'
    elif not hedef_user.is_active:
        durum = 'pasif'
        durum_text = 'Onaysız (Pasif)'
    elif hedef_user.profil.timeout_until and hedef_user.profil.timeout_until > now:
        durum = 'susturulmus'
        durum_text = 'Susturulmuş'
    
    # İçerikler
    icerikler = Icerik.objects.filter(yazar=hedef_user).select_related('kategori', 'yazar__profil').order_by('-tarih')
    
    # Yorumlar
    yorumlar = Yorum.objects.filter(yazar=hedef_user).select_related('icerik', 'yazar__profil').order_by('-tarih')
    
    # Kaydedilenler
    kaydedilenler = hedef_user.kaydedilen_icerikler.all().select_related('yazar__profil', 'kategori').order_by('-tarih')
    
    # Beğendiği yorumlar
    begenilenler = hedef_user.begendigi_yorumlar.all().select_related('icerik', 'yazar__profil').order_by('-tarih')
    
    # İstatistikler
    toplam_icerik = icerikler.count()
    toplam_yorum = yorumlar.count()
    toplam_kayit = kaydedilenler.count()
    toplam_begeni_yapilan = begenilenler.count()
    
    # Aldığı beğeniler (yorumlarına gelen)
    alinan_begeni = Yorum.objects.filter(yazar=hedef_user).aggregate(
        total=Count('begenenler', distinct=True)
    )['total']
    
    # Aktivite Haritası (son 30 gün)
    today = timezone.localtime(now).date()
    join_date = timezone.localtime(hedef_user.date_joined).date()
    thirty_days_ago = today - timedelta(days=29)
    start_date = max(join_date, thirty_days_ago)
    days_to_show = (today - start_date).days + 1
    
    son_gunler = [today - timedelta(days=i) for i in range(days_to_show - 1, -1, -1)]
    
    aktiviteler_heatmap = GunlukAktivite.objects.filter(
        user=hedef_user, tarih__gte=son_gunler[0]
    ).values('tarih', 'sure_dk')
    aktivite_sozlugu = {a['tarih']: a['sure_dk'] for a in aktiviteler_heatmap}
    
    aylar_tr = {
        1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis', 5: 'May', 6: 'Haz',
        7: 'Tem', 8: 'Ağu', 9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'
    }
    
    gunluk_veriler = []
    for tarih in son_gunler:
        sure = aktivite_sozlugu.get(tarih, 0)
        gunluk_veriler.append({
            'tarih': f"{tarih.day} {aylar_tr[tarih.month]}",
            'gun': tarih.day,
            'ay': aylar_tr[tarih.month],
            'sure': sure
        })
    
    toplam_sure = sum(d['sure'] for d in gunluk_veriler)
    bolen = len(gunluk_veriler) if gunluk_veriler else 1
    gunluk_ortalama = int(toplam_sure / bolen)
    
    # Son aktiviteler (timeline)
    son_aktiviteler = Aktivite.objects.filter(user=hedef_user).select_related('icerik', 'yorum').order_by('-tarih')
    
    context = {
        'hedef_user': hedef_user,
        'durum': durum,
        'durum_text': durum_text,
        'icerikler': icerikler,
        'yorumlar': yorumlar,
        'kaydedilenler': kaydedilenler,
        'begenilenler': begenilenler,
        'toplam_icerik': toplam_icerik,
        'toplam_yorum': toplam_yorum,
        'toplam_kayit': toplam_kayit,
        'toplam_begeni_yapilan': toplam_begeni_yapilan,
        'alinan_begeni': alinan_begeni,
        'gunluk_veriler': gunluk_veriler,
        'gunluk_ortalama': gunluk_ortalama,
        'son_aktiviteler': son_aktiviteler,
        'now': now,
    }
    return render(request, 'admin_user_detail.html', context)

@login_required
def admin_export_data(request):
    if not request.user.is_superuser:
        log_ihlali(request) # Logla
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    def stream_lines():
        now_text = timezone.now().strftime('%d.%m.%Y %H:%M')
        yield f"SİSTEM TAM VERİ DÖKÜMÜ\nTarih: {now_text}\nUser: {request.user.username}\n"
        
        # USERS
        users = User.objects.all().select_related('profil').order_by('-date_joined')
        yield f"\n{'='*20} KULLANICILAR ({users.count()}) {'='*20}\n\n"
        for u in users.iterator(chunk_size=1000):
            status_list = []
            if u.is_superuser: status_list.append("ADMIN")
            if hasattr(u, 'profil'):
                if u.profil.is_banned: status_list.append("BANLI")
                if u.profil.timeout_until and u.profil.timeout_until > timezone.now(): status_list.append(f"SUSTURULMUŞ ({u.profil.timeout_until})")
            status = ", ".join(status_list) if status_list else "Aktif"
            
            yield f"User: {u.username} (ID: {u.id})\n"
            yield f"Email: {u.email}\n"
            yield f"Kayıt: {u.date_joined.strftime('%d.%m.%Y %H:%M')}\n"
            yield f"Durum: {status}\n"
            if hasattr(u, 'profil'):
                yield f"Hakkında: {u.profil.hakkinda}\n"
            yield "-" * 30 + "\n"

        # KATEGORILER
        cats = Kategori.objects.all()
        yield f"\n{'='*20} KATEGORİLER ({cats.count()}) {'='*20}\n\n"
        for c in cats.iterator(chunk_size=1000):
            yield f"- {c.isim} (ID: {c.id})\n"

        # ICERIKLER
        posts = Icerik.objects.all().select_related('yazar', 'kategori').order_by('-tarih')
        yield f"\n{'='*20} İÇERİKLER ({posts.count()}) {'='*20}\n\n"
        for p in posts.iterator(chunk_size=1000):
            yield f"Başlık: {p.baslik} (ID: {p.id})\n"
            yield f"Yazar: {p.yazar.username}\n"
            yield f"Kategori: {p.kategori.isim if p.kategori else 'Yok'}\n"
            yield f"Tarih: {p.tarih.strftime('%d.%m.%Y %H:%M')}\n"
            yield f"Türü: {p.get_tur_display()}\n"
            yield f"İçerik:\n{p.yazi}\n"
            yield "-" * 30 + "\n"

        # YORUMLAR
        comments = Yorum.objects.all().select_related('yazar', 'icerik').order_by('-tarih')
        yield f"\n{'='*20} YORUMLAR ({comments.count()}) {'='*20}\n\n"
        for c in comments.iterator(chunk_size=1000):
            yield f"Yazar: {c.yazar.username}\n"
            yield f"Konu: {c.icerik.baslik}\n"
            yield f"Tarih: {c.tarih.strftime('%d.%m.%Y %H:%M')}\n"
            yield f"Mesaj: {c.mesaj}\n"
            yield "-" * 30 + "\n"

    response = StreamingHttpResponse(stream_lines(), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="sistem_verileri.txt"'
    return response

# --- ADMIN ACTIONS ---
@login_required
@require_POST
def admin_ban_user(request, user_id):
    if not request.user.is_superuser:
        log_ihlali(request) # Logla
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    user_to_ban = get_object_or_404(User, id=user_id)
    profil = user_to_ban.profil
    
    # Toggle ban status
    profil.is_banned = not profil.is_banned
    profil.save()
    
    status = "banlandı" if profil.is_banned else "banı kaldırıldı"
    messages.success(request, f"{user_to_ban.username} başarıyla {status}.")
    
    # Dashboard'dan geldiyse dashboard'a dön
    referer = request.META.get('HTTP_REFERER', '')
    if 'yonetim' in referer:
        return redirect('admin_monitor')
    return redirect('profil', username=user_to_ban.username)

@login_required
@require_POST
def admin_timeout_user(request, user_id):
    if not request.user.is_superuser:
        log_ihlali(request) # Logla
        return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
    if request.method == 'POST':
        user_to_timeout = get_object_or_404(User, id=user_id)
        profil = user_to_timeout.profil
        
        duration = request.POST.get('duration')
        if duration == 'remove':
            profil.timeout_until = None
            messages.success(request, f"{user_to_timeout.username} kullanıcısının susturması kaldırıldı.")
        else:
            try:
                days = int(duration)
                profil.timeout_until = timezone.now() + timedelta(days=days)
                messages.success(request, f"{user_to_timeout.username} {days} günlüğüne susturuldu.")
            except (ValueError, TypeError):
                messages.error(request, "Geçersiz süre.")
        
        profil.save()
        
        # Dashboard'dan geldiyse dashboard'a dön
        referer = request.META.get('HTTP_REFERER', '')
        if 'yonetim' in referer:
            return redirect('admin_monitor')
        return redirect('profil', username=user_to_timeout.username)
    
    return redirect('anasayfa')

# --- CKEditor Resim Yükleme ---
@login_required
@require_POST
def ckeditor_resim_yukle(request):
    """CKEditor editöründen yüklenen resimleri karşılar. Sadece adminler kullanabilir."""
    if not request.user.is_superuser:
        return JsonResponse({'error': {'message': 'Yetkisiz erişim.'}}, status=403)
    
    upload = request.FILES.get('upload')
    if not upload:
        return JsonResponse({'error': {'message': 'Dosya bulunamadı.'}}, status=400)
    
    # Dosya boyutu kontrolü (max 5MB)
    if upload.size > 5 * 1024 * 1024:
        return JsonResponse({'error': {'message': 'Dosya boyutu en fazla 5MB olabilir.'}}, status=400)
    
    # Uzantı kontrolü
    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
    ext = upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else ''
    if ext not in allowed_extensions:
        return JsonResponse({'error': {'message': f'Sadece şu dosya türleri kabul edilir: {", ".join(allowed_extensions)}'}}, status=400)
    
    # Gerçek resim doğrulaması
    try:
        from PIL import Image
        img = Image.open(upload)
        img.verify()
        upload.seek(0)
    except Exception:
        return JsonResponse({'error': {'message': 'Yüklenen dosya geçerli bir resim değil.'}}, status=400)
    
    from django.core.files.storage import default_storage

    try:
        optimized_upload = optimize_uploaded_image(upload, Path(upload.name).name)
        file_name = default_storage.save(f"ckeditor_resimleri/{optimized_upload.file.name}", optimized_upload.file)
        file_url = default_storage.url(file_name)
    except OSError:
        return JsonResponse({'error': {'message': 'Resim dosyasi kaydedilemedi. Dosya adini degistirip tekrar deneyin.'}}, status=500)
    
    return JsonResponse({'url': file_url})
@require_POST
def dogrulama_mail_gonder(request):
    """Kullanıcıya doğrulama e-postasını tekrar gönderir (Güvenli versiyon)."""
    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({'success': False, 'mesaj': 'E-posta adresi belirtilmedi.'}, status=400)

    # 1. Rate Limit Kontrolü (IP bazlı 5 dakikada 1)
    ip = get_client_ip(request)
    ip_limit_key = f"resend_limit_ip_{ip}"
    email_limit_key = f"resend_limit_email_{email.lower()}"
    if cache.get(ip_limit_key) or cache.get(email_limit_key):
        return JsonResponse({
            'success': False, 
            'mesaj': 'Çok sık deniyorsunuz. Lütfen birkaç dakika bekleyin.'
        }, status=429)

    generic_msg = 'Eğer bu e-posta adresi sistemimizde kayıtlıysa ve henüz doğrulanmamışsa, bir bağlantı gönderilecektir.'

    try:
        user = User.objects.get(email=email)
        # Sadece pasif kullanıcılar için gönder
        if not user.is_active:
            email_address = EmailAddress.objects.get(user=user, email=email)
            email_address.send_confirmation(request, signup=False)
        cache.set(ip_limit_key, True, timeout=300)
        cache.set(email_limit_key, True, timeout=300)
        return JsonResponse({'success': True, 'mesaj': generic_msg})
    except (User.DoesNotExist, EmailAddress.DoesNotExist):
        # Güvenlik için enumerate engelle
        cache.set(ip_limit_key, True, timeout=300)
        cache.set(email_limit_key, True, timeout=300)
        return JsonResponse({'success': True, 'mesaj': generic_msg})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"E-posta tekrar gönderim hatası: {e}")
        return JsonResponse({'success': False, 'mesaj': 'Bir hata oluştu.'}, status=500)
