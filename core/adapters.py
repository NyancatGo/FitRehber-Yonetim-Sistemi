import re

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.urls import reverse


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        email = data.get("email", "")
        base_username = ""

        if email:
            base_username = email.split("@")[0]

        if not base_username:
            base_username = data.get("username") or data.get("name", "user").replace(" ", "_")

        base_username = re.sub(r"[^a-zA-Z0-9_]", "", base_username)

        if not base_username:
            base_username = "user"

        user.username = self.generate_unique_username(base_username)
        return user

    def generate_unique_username(self, base):
        user_model = get_user_model()
        username = base
        counter = 1

        while user_model.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1

        return username

    def is_open_for_signup(self, request, sociallogin):
        return True


class MyAccountAdapter(DefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        from core.email_service import get_email_service

        if request is not None:
            verification_url = request.build_absolute_uri(
                reverse("email_confirm_magic", args=[emailconfirmation.key])
            )
        else:
            current_site = Site.objects.get_current()
            verification_url = (
                f"{settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL}://"
                f"{current_site.domain}{reverse('email_confirm_magic', args=[emailconfirmation.key])}"
            )

        response = get_email_service().send_template_email(
            to=emailconfirmation.email_address.email,
            subject="FitRehber - E-posta Adresinizi Dogrulayin",
            template_name="emails/email_verification.html",
            context={
                "username": (
                    emailconfirmation.email_address.user.username
                    if emailconfirmation.email_address.user
                    else "Kullanici"
                ),
                "verification_url": verification_url,
            },
        )
        if response is not None:
            return None

        return super().send_confirmation_mail(request, emailconfirmation, signup)

    def send_mail(self, template_prefix, email, context):
        """Use EmailService for confirmation emails and fallback otherwise."""
        if "email_confirmation" in template_prefix:
            from core.email_service import get_email_service

            response = get_email_service().send_template_email(
                to=email,
                subject="FitRehber - E-posta Adresinizi Dogrulayin",
                template_name="emails/email_verification.html",
                context={
                    "username": context.get("user").username if context.get("user") else "Kullanici",
                    "verification_url": context.get("activate_url"),
                },
            )
            if response is not None:
                return None

        return super().send_mail(template_prefix, email, context)
