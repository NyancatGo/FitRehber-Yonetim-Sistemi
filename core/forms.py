from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from core.email_service import get_email_service
from core.security_utils import get_client_ip

User = get_user_model()
PASSWORD_RESET_RATE_LIMIT_WINDOW = 86400


class CustomPasswordResetForm(PasswordResetForm):
    """
    Sends password reset links with the shared EmailService and applies
    per-email/per-IP cooldowns for 24 hours.

    Unlike Django's default form, inactive users are also eligible so the
    reset flow can still help accounts that have not completed activation yet.
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def _get_normalized_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def _get_email_limit_key(self, email):
        return f"reset_limit_email_{email}"

    def _get_ip_limit_key(self, ip_address):
        return f"reset_limit_ip_{ip_address}"

    def _mark_rate_limited(self, email):
        if not self.request:
            return

        ip_address = get_client_ip(self.request)
        cache.set(
            self._get_email_limit_key(email),
            True,
            timeout=PASSWORD_RESET_RATE_LIMIT_WINDOW,
        )

        ip_key = self._get_ip_limit_key(ip_address)
        ip_count = cache.get(ip_key, 0)
        cache.set(
            ip_key,
            ip_count + 1,
            timeout=PASSWORD_RESET_RATE_LIMIT_WINDOW,
        )

    def _build_reset_url(self, user, token_generator, request, use_https, domain_override):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        reset_path = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": uid, "token": token},
        )

        if request is not None:
            reset_url = request.build_absolute_uri(reset_path)
            preferred_protocol = getattr(settings, "ACCOUNT_DEFAULT_HTTP_PROTOCOL", "https")
            if preferred_protocol == "https" and reset_url.startswith("http://"):
                return "https://" + reset_url[len("http://"):]
            return reset_url

        domain = domain_override or "fitrehber.com.tr"
        protocol = "https" if use_https else getattr(
            settings,
            "ACCOUNT_DEFAULT_HTTP_PROTOCOL",
            "https",
        )
        return f"{protocol}://{domain}{reset_path}"

    def get_target_users(self):
        email = self._get_normalized_email()
        email_field_name = get_user_model().get_email_field_name()
        return User.objects.filter(**{f"{email_field_name}__iexact": email})

    def clean_email(self):
        email = self._get_normalized_email()
        if not self.request:
            return email

        ip_address = get_client_ip(self.request)

        if cache.get(self._get_email_limit_key(email)):
            raise forms.ValidationError(
                _("Bu e-posta adresine son 24 saat içinde zaten bir sıfırlama bağlantısı gönderildi.")
            )

        ip_count = cache.get(self._get_ip_limit_key(ip_address), 0)
        if ip_count >= 3:
            raise forms.ValidationError(
                _("Bu cihazdan çok fazla şifre sıfırlama talebinde bulunuldu. Lütfen 24 saat sonra tekrar deneyin.")
            )

        return email

    def save(
        self,
        domain_override=None,
        subject_template_name="registration/password_reset_subject.txt",
        email_template_name="registration/password_reset_email.html",
        use_https=True,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        email = self._get_normalized_email()
        users = self.get_target_users()

        email_service = get_email_service()
        for user in users:
            reset_url = self._build_reset_url(
                user=user,
                token_generator=token_generator,
                request=request,
                use_https=use_https,
                domain_override=domain_override,
            )

            email_service.send_template_email(
                to=user.email,
                subject="FitRehber - Sifrenizi Sifirlayin",
                template_name="emails/password_reset.html",
                context={
                    "user": user,
                    "username": user.username or "Kullanici",
                    "reset_url": reset_url,
                },
            )

        # Preserve enumeration resistance by applying the same cooldown even
        # when the email does not belong to an account.
        self._mark_rate_limited(email)
        return email
