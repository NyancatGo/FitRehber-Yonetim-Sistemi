import os
import logging

from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)


class BrowserConsoleBackend(BaseEmailBackend):
    """DEBUG modunda e-postaları tarayıcı konsoluna yazan backend."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        try:
            # posts uygulamasının static klasörüne yazıyoruz
            static_dir = os.path.join(settings.BASE_DIR, 'posts', 'static', 'js')
            os.makedirs(static_dir, exist_ok=True)
            file_path = os.path.join(static_dir, 'email_monitor.js')

            with open(file_path, 'w', encoding='utf-8') as f:
                for message in email_messages:
                    # JS string kaçış karakterlerini temizle
                    body = message.body.replace('\n', '\\n').replace('"', '\\"').replace("'", "\\'")
                    subject = message.subject.replace('"', '\\"')

                    # Şık bir konsol çıktısı hazırla
                    js_code = f"""
                    console.group('%c 📨 YENİ E-POSTA YAKALANDI! ', 'background: #222; color: #bada55; font-size: 16px; padding: 4px; border-radius: 4px;');
                    console.log('%c KONU: {subject}', 'font-weight: bold; color: #4facfe; font-size: 14px;');
                    console.log('%c İÇERİK AŞAĞIDA 👇', 'color: #ccc; font-style: italic;');
                    console.log("{body}");
                    console.log('%c ----------------------------------------', 'color: #666;');
                    console.groupEnd();
                    """
                    f.write(js_code)
            return len(email_messages)
        except Exception as e:
            print(f"BrowserConsoleBackend Hatası: {e}")
            return 0


class ResendEmailBackend(BaseEmailBackend):
    """
    Resend API üzerinden e-posta gönderen Django Email Backend.

    Django'nun send_mail() ve django-allauth ile tam uyumludur.
    settings.py'daki EMAIL_BACKEND olarak kullanılır.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        try:
            import resend
            self.resend = resend
            self.resend.api_key = getattr(settings, 'RESEND_API_KEY', '')
        except ImportError:
            logger.error("'resend' paketi yüklü değil! pip install resend")
            self.resend = None

        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')

    def send_messages(self, email_messages):
        """Django EmailMessage listesini Resend API ile gönderir."""
        if not email_messages:
            return 0

        if not self.resend:
            logger.error("Resend SDK yüklenemedi, e-postalar gönderilemedi.")
            return 0

        if not self.resend.api_key:
            logger.error("RESEND_API_KEY ayarlanmamış! .env dosyasını kontrol edin.")
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY ayarlanmamış!")
            return 0

        sent_count = 0
        for message in email_messages:
            try:
                # Gönderen adresi: mesajdan al veya varsayılanı kullan
                from_email = message.from_email or self.from_email

                # HTML içerik varsa kullan, yoksa düz text
                html_content = None
                text_content = message.body

                # Django EmailMessage'ın alternatives'ında HTML aranır
                if hasattr(message, 'alternatives'):
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            html_content = content
                            break

                # Resend API parametreleri
                params = {
                    "from": from_email,
                    "to": list(message.to),
                    "subject": message.subject,
                }

                # HTML veya text içerik ekle
                if html_content:
                    params["html"] = html_content
                else:
                    params["text"] = text_content

                # CC ve BCC desteği
                if message.cc:
                    params["cc"] = list(message.cc)
                if message.bcc:
                    params["bcc"] = list(message.bcc)

                # Reply-To desteği
                if message.reply_to:
                    params["reply_to"] = list(message.reply_to)

                # E-postayı gönder
                response = self.resend.Emails.send(params)
                sent_count += 1

                logger.info(
                    f"✅ E-posta gönderildi: {message.subject} -> {', '.join(message.to)} "
                    f"(ID: {response.get('id', 'N/A')})"
                )

            except Exception as e:
                logger.error(
                    f"❌ E-posta gönderilemedi: {message.subject} -> {', '.join(message.to)} | Hata: {e}"
                )
                if not self.fail_silently:
                    raise

        return sent_count
