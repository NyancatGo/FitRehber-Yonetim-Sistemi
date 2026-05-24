from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic.base import RedirectView

from core.forms import CustomPasswordResetForm
from core.views import (
    CustomPasswordResetConfirmView,
    CustomPasswordResetView,
    InstantConfirmEmailView,
)
from posts.views import (
    anasayfa, forum_sayfasi, detay, kayit_ol, giris_yap, cikis_yap, onboarding,
    icerik_ekle, icerik_sil, icerik_duzenle, profil_sayfasi, profil_duzenle, 
    profil_icerikleri, yorum_begen, icerik_kaydet, icerik_begen, yorum_sil, arama, kurallar,
    admin_ban_user, admin_timeout_user, admin_delete_user, admin_monitor, admin_export_data,
    admin_user_detail, admin_security_logs, ckeditor_resim_yukle, dogrulama_mail_gonder,
    profil_foto_guncelle, profil_foto_sil, robots_txt, sitemap_xml, google_site_verification,
    mobile_google_start, mobile_auth_callback,
)
from posts.api import aktivite_kaydet, canli_arama
from core.api_mobile_auth import mobile_register, mobile_resend_verification, mobile_password_reset_request
from django.conf import settings
from django.conf.urls.static import static
import posts.views_yonetim as views_yonetim


urlpatterns = [
    # Admin İşlemleri (Önce Tanımla)
    path('admin/islem/ban/<int:user_id>/', admin_ban_user, name='admin_ban_user'),
    path('admin/islem/timeout/<int:user_id>/', admin_timeout_user, name='admin_timeout_user'),
    path('admin/islem/sil/<int:user_id>/', admin_delete_user, name='admin_delete_user'),
    path('yonetim/', admin_monitor, name='admin_monitor'),
    path('yonetim/indir/', admin_export_data, name='admin_export_data'),
    path('yonetim/kullanici/<int:user_id>/', admin_user_detail, name='admin_user_detail'),
    path('yonetim/guvenlik-kayitlari/', admin_security_logs, name='admin_security_logs'),
    path('ckeditor-yukle/', ckeditor_resim_yukle, name='ckeditor_resim_yukle'),

    # Şifre Sıfırlama ve Giriş İşlemleri İçin
    path('hesap/password_reset/', 
         CustomPasswordResetView.as_view(
             form_class=CustomPasswordResetForm,
             success_url='/hesap/password_reset/done/'
         ), 
         name='password_reset'),
    path(
        'hesap/reset/<uidb64>/<token>/',
        CustomPasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ),
        name='password_reset_confirm',
    ),
    path('hesap/reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    path('hesap/', include('django.contrib.auth.urls')),
    path('accounts/confirm-email/<str:key>/', InstantConfirmEmailView.as_view(), name='email_confirm_magic'),
    path('accounts/mobile-google/start/', mobile_google_start, name='mobile_google_start'),
    path('accounts/mobile-token/', mobile_auth_callback, name='mobile_auth_callback'),

    # Mobil JSON Auth Endpoints
    path('mobile/auth/register/', mobile_register, name='mobile_register'),
    path('mobile/auth/verification/resend/', mobile_resend_verification, name='mobile_resend_verification'),
    path('mobile/auth/password-reset/request/', mobile_password_reset_request, name='mobile_password_reset_request'),

    path('accounts/', include('allauth.urls')),

    path('', anasayfa, name='anasayfa'),
    path('google4c81f11de67ce22.html', google_site_verification, name='google_site_verification'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('forum/', forum_sayfasi, name='forum'),
    path('detay/<int:id>/', detay, name='detay'),
    path('kayit/', kayit_ol, name='kayit'),
    path('giris/', giris_yap, name='giris'),
    path('cikis/', cikis_yap, name='cikis'),
    path('onboarding/', onboarding, name='onboarding'),
    path('ekle/', icerik_ekle, name='ekle'),
    path('sil/<int:id>/', icerik_sil, name='sil'),
    path('duzenle/<int:id>/', icerik_duzenle, name='icerik_duzenle'),
    path('profil/<str:username>/icerikler/', profil_icerikleri, name='profil_icerikleri'),
    path('profil/<str:username>/', profil_sayfasi, name='profil'),
    path('aktivite-kaydet/', aktivite_kaydet, name='aktivite_kaydet'),
    path('canli-arama/', include([
        path('', canli_arama, name='canli_arama'),
    ])),
    path('dogrulama-gonder/', dogrulama_mail_gonder, name='dogrulama_mail_gonder'),
    path('profil-duzenle/', profil_duzenle, name='profil_duzenle'),
    path('profil-foto/guncelle/', profil_foto_guncelle, name='profil_foto_guncelle'),
    path('profil-foto/sil/', profil_foto_sil, name='profil_foto_sil'),
    path('begen/<int:id>/', yorum_begen, name='yorum_begen'),
    path('icerik-begen/<int:id>/', icerik_begen, name='icerik_begen'),
    path('kaydet/<int:id>/', icerik_kaydet, name='icerik_kaydet'),
    path('yorum-sil/<int:id>/', yorum_sil, name='yorum_sil'),
    path('arama/', arama, name='arama'),
    path('kurallar/', kurallar, name='kurallar'),

    # Veritabanı Ödevi Yönetim Konsolu (N-Tier, SP, Trigger & UDF)
    path('yonetim-sistemi/', include([
        path('', views_yonetim.dashboard, name='yonetim_dashboard'),
        path('kullanicilar/', views_yonetim.kullanici_liste, name='yonetim_kullanicilar'),
        path('kullanicilar/ekle/', views_yonetim.kullanici_ekle, name='yonetim_kullanici_ekle'),
        path('kullanicilar/duzenle/<int:user_id>/', views_yonetim.kullanici_duzenle, name='yonetim_kullanici_duzenle'),
        path('kullanicilar/sil/<int:user_id>/', views_yonetim.kullanici_sil, name='yonetim_kullanici_sil'),
        path('kategoriler/', views_yonetim.kategori_liste, name='yonetim_kategoriler'),
        path('kategoriler/ekle/', views_yonetim.kategori_ekle, name='yonetim_kategori_ekle'),
        path('kategoriler/duzenle/<int:kategori_id>/', views_yonetim.kategori_duzenle, name='yonetim_kategori_duzenle'),
        path('kategoriler/sil/<int:kategori_id>/', views_yonetim.kategori_sil, name='yonetim_kategori_sil'),
        path('icerikler/', views_yonetim.icerik_liste, name='yonetim_icerikler'),
        path('icerikler/ekle/', views_yonetim.icerik_ekle, name='yonetim_icerik_ekle'),
        path('icerikler/duzenle/<int:content_id>/', views_yonetim.icerik_duzenle, name='yonetim_icerik_duzenle'),
        path('icerikler/sil/<int:content_id>/', views_yonetim.icerik_sil, name='yonetim_icerik_sil'),
        path('yorumlar/', views_yonetim.yorum_liste, name='yonetim_yorumlar'),
        path('yorumlar/ekle/', views_yonetim.yorum_ekle, name='yonetim_yorum_ekle'),
        path('yorumlar/duzenle/<int:comment_id>/', views_yonetim.yorum_duzenle, name='yonetim_yorum_duzenle'),
        path('yorumlar/sil/<int:comment_id>/', views_yonetim.yorum_sil, name='yonetim_yorum_sil'),
        # Profil
        path('profiller/', views_yonetim.profil_liste, name='yonetim_profiller'),
        path('profiller/ekle/', views_yonetim.profil_ekle, name='yonetim_profil_ekle'),
        path('profiller/duzenle/<int:profil_id>/', views_yonetim.profil_duzenle, name='yonetim_profil_duzenle'),
        path('profiller/sil/<int:profil_id>/', views_yonetim.profil_sil, name='yonetim_profil_sil'),
        path('profiller/ban/<int:profil_id>/', views_yonetim.profil_ban_toggle, name='yonetim_profil_ban_toggle'),
        # İçerik Beğeni
        path('icerik-begenileri/', views_yonetim.icerik_begeni_liste, name='yonetim_icerik_begenileri'),
        path('icerik-begenileri/duzenle/<int:begeni_id>/', views_yonetim.icerik_begeni_duzenle, name='yonetim_icerik_begeni_duzenle'),
        path('icerik-begenileri/sil/<int:begeni_id>/', views_yonetim.icerik_begeni_sil, name='yonetim_icerik_begeni_sil'),
        # İçerik Kaydetme
        path('icerik-kaydetmeleri/', views_yonetim.icerik_kaydetme_liste, name='yonetim_icerik_kaydetmeleri'),
        path('icerik-kaydetmeleri/duzenle/<int:kaydetme_id>/', views_yonetim.icerik_kaydetme_duzenle, name='yonetim_icerik_kaydetme_duzenle'),
        path('icerik-kaydetmeleri/sil/<int:kaydetme_id>/', views_yonetim.icerik_kaydetme_sil, name='yonetim_icerik_kaydetme_sil'),
        # Yorum Beğeni
        path('yorum-begenileri/', views_yonetim.yorum_begeni_liste, name='yonetim_yorum_begenileri'),
        path('yorum-begenileri/duzenle/<int:begeni_id>/', views_yonetim.yorum_begeni_duzenle, name='yonetim_yorum_begeni_duzenle'),
        path('yorum-begenileri/sil/<int:begeni_id>/', views_yonetim.yorum_begeni_sil, name='yonetim_yorum_begeni_sil'),
    ])),

    path('admin/', admin.site.urls),
    path("favicon.ico", RedirectView.as_view(url=settings.STATIC_URL + "images/favicons/favicon.ico?v=20260311c", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
