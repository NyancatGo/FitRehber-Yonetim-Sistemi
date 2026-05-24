"""
Resend Email Service — FitRehber

Class-based e-posta servis modülü.
- HTML template render desteği
- Rate limiting (cache ile günlük/aylık)
- Kapsamlı logging
- Hata yönetimi

Kullanım:
    from core.email_service import EmailService

    service = EmailService()
    service.send_email("user@example.com", "Konu", "<h1>Merhaba</h1>")
    service.send_template_email("user@example.com", "Konu", "emails/welcome.html", {"user": user})
    service.send_verification_email(user, "https://fitrehber.com.tr/verify/TOKEN")
"""

_email_service_instance = None

def get_email_service():
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance


def reset_email_service():
    global _email_service_instance
    _email_service_instance = None

import logging
from datetime import date

from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class EmailService:
    """
    Resend API üzerinden e-posta gönderen merkezi servis sınıfı.

    Free tier limitleri:
        - Günlük: 100 e-posta
        - Aylık:  3.000 e-posta
    """

    # Cache key'leri
    DAILY_COUNT_KEY = "resend_daily_count_{date}"
    MONTHLY_COUNT_KEY = "resend_monthly_count_{month}"

    def __init__(self):
        try:
            import resend
            self.resend = resend
            self.resend.api_key = getattr(settings, 'RESEND_API_KEY', '')
        except ImportError:
            logger.error("'resend' paketi yüklü değil! pip install resend")
            self.resend = None

        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')
        self.daily_limit = getattr(settings, 'RESEND_DAILY_LIMIT', 100)
        self.monthly_limit = getattr(settings, 'RESEND_MONTHLY_LIMIT', 3000)

    # ──────────────────────────────────────────────
    # PUBLIC METHODS
    # ──────────────────────────────────────────────

    def send_email(self, to, subject, html_content=None, text_content=None, from_email=None):
        """
        Temel e-posta gönderimi.

        Args:
            to (str | list): Alıcı e-posta adresi veya adresleri
            subject (str): E-posta konusu
            html_content (str, optional): HTML içerik
            text_content (str, optional): Düz metin içerik
            from_email (str, optional): Gönderen adresi (varsayılan: settings)

        Returns:
            dict | None: Resend API response veya hata durumunda None
        """
        if not self._preflight_check():
            return None

        # Rate limit kontrolü
        if not self._check_rate_limit():
            return None

        # Alıcıyı listeye çevir
        if isinstance(to, str):
            to = [to]

        # Parametreleri hazırla
        params = {
            "from": from_email or self.from_email,
            "to": to,
            "subject": subject,
        }

        if html_content:
            params["html"] = html_content
        elif text_content:
            params["text"] = text_content
        else:
            logger.warning("E-posta içeriği (html veya text) belirtilmedi!")
            params["text"] = "(boş içerik)"

        try:
            response = self.resend.Emails.send(params)
            self._increment_counters()
            self._log_email(to, subject, "BAŞARILI", response.get("id", "N/A"))
            return response
        except Exception as e:
            self._log_email(to, subject, "BAŞARISIZ", str(e))
            logger.error(f"Resend API hatası: {e}")
            return None

    def send_template_email(self, to, subject, template_name, context=None, from_email=None):
        """
        Django template'i render edip e-posta olarak gönderir.

        Args:
            to (str | list): Alıcı adresi
            subject (str): E-posta konusu
            template_name (str): Template yolu (ör: 'emails/welcome.html')
            context (dict, optional): Template değişkenleri
            from_email (str, optional): Gönderen adresi

        Returns:
            dict | None: Resend API response
        """
        context = context or {}

        # Varsayılan context değişkenleri
        context.setdefault("site_name", "FitRehber")
        context.setdefault("site_url", "https://fitrehber.com.tr")
        context.setdefault("current_year", date.today().year)

        try:
            html_content = render_to_string(template_name, context)
        except Exception as e:
            logger.error(f"Template render hatası ({template_name}): {e}")
            return None

        return self.send_email(to, subject, html_content=html_content, from_email=from_email)

    def send_verification_email(self, user, verification_url):
        """
        Kayıt doğrulama e-postası gönderir.

        Args:
            user: Django User nesnesi
            verification_url (str): Doğrulama linki

        Returns:
            dict | None: Resend API response
        """
        context = {
            "user": user,
            "username": user.username,
            "verification_url": verification_url,
        }
        return self.send_template_email(
            to=user.email,
            subject="FitRehber — E-posta Adresinizi Doğrulayın",
            template_name="emails/email_verification.html",
            context=context,
        )

    def send_welcome_email(self, user):
        """
        Hoş geldin e-postası gönderir.

        Args:
            user: Django User nesnesi

        Returns:
            dict | None: Resend API response
        """
        context = {
            "user": user,
            "username": user.username,
        }
        return self.send_template_email(
            to=user.email,
            subject="FitRehber'e Hoş Geldiniz! 🎉",
            template_name="emails/welcome.html",
            context=context,
        )

    def get_usage_stats(self):
        """
        Günlük ve aylık e-posta kullanım istatistiklerini döndürür.

        Returns:
            dict: Kullanım bilgileri
        """
        today = date.today()
        daily_key = self.DAILY_COUNT_KEY.format(date=today.isoformat())
        monthly_key = self.MONTHLY_COUNT_KEY.format(month=today.strftime("%Y-%m"))

        daily_count = cache.get(daily_key, 0)
        monthly_count = cache.get(monthly_key, 0)

        return {
            "daily_sent": daily_count,
            "daily_limit": self.daily_limit,
            "daily_remaining": max(0, self.daily_limit - daily_count),
            "monthly_sent": monthly_count,
            "monthly_limit": self.monthly_limit,
            "monthly_remaining": max(0, self.monthly_limit - monthly_count),
        }

    # ──────────────────────────────────────────────
    # PRIVATE METHODS
    # ──────────────────────────────────────────────

    def _preflight_check(self):
        """Gönderim öncesi gerekli kontrolleri yapar."""
        if not self.resend:
            logger.error("Resend SDK yüklenemedi. pip install resend")
            return False

        if not self.resend.api_key:
            logger.error("RESEND_API_KEY ayarlanmamış! .env dosyasını kontrol edin.")
            return False

        return True

    def _check_rate_limit(self):
        """
        Free tier limitlerini kontrol eder.

        Returns:
            bool: Limit aşılmadıysa True
        """
        today = date.today()
        daily_key = self.DAILY_COUNT_KEY.format(date=today.isoformat())
        monthly_key = self.MONTHLY_COUNT_KEY.format(month=today.strftime("%Y-%m"))

        daily_count = cache.get(daily_key, 0)
        monthly_count = cache.get(monthly_key, 0)

        if daily_count >= self.daily_limit:
            logger.warning(
                f"⚠️  Günlük e-posta limiti aşıldı! ({daily_count}/{self.daily_limit})"
            )
            return False

        if monthly_count >= self.monthly_limit:
            logger.warning(
                f"⚠️  Aylık e-posta limiti aşıldı! ({monthly_count}/{self.monthly_limit})"
            )
            return False

        return True

    def _increment_counters(self):
        """Başarılı gönderim sonrası sayaçları artırır."""
        today = date.today()
        daily_key = self.DAILY_COUNT_KEY.format(date=today.isoformat())
        monthly_key = self.MONTHLY_COUNT_KEY.format(month=today.strftime("%Y-%m"))

        # Günlük sayaç (24 saat sonra otomatik silinir)
        daily_count = cache.get(daily_key, 0)
        cache.set(daily_key, daily_count + 1, timeout=86400)  # 24 saat

        # Aylık sayaç (32 gün sonra otomatik silinir)
        monthly_count = cache.get(monthly_key, 0)
        cache.set(monthly_key, monthly_count + 1, timeout=2764800)  # 32 gün

    def _log_email(self, to, subject, status, detail=""):
        """E-posta gönderim bilgilerini loglar."""
        recipients = ", ".join(to) if isinstance(to, list) else to
        log_msg = f"[EMAIL {status}] Konu: {subject} | Alıcı: {recipients}"
        if detail:
            log_msg += f" | Detay: {detail}"

        if status == "BAŞARILI":
            logger.info(log_msg)
        else:
            logger.error(log_msg)
