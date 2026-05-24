from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy

from allauth.account.views import ConfirmEmailView


class InstantConfirmEmailView(ConfirmEmailView):
    def post(self, *args, **kwargs):
        self.object = verification = self.get_object()
        self.logout_other_user(self.object)

        email_address = verification.confirm(self.request)
        if not email_address:
            return self.respond(False)

        user = email_address.user
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        if not self.request.user.is_authenticated:
            auth_login(self.request, user, backend=settings.AUTHENTICATION_BACKENDS[0])

        return redirect("anasayfa")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["auto_submit"] = bool(self.object and self.object.email_address)
        return ctx

class CustomPasswordResetView(PasswordResetView):
    """
    Şifre sıfırlama formuna request objesini (IP bilgisi için) 
    enjekte eden özel view.
    """
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        if not form.get_target_users().exists():
            email = form.cleaned_data["email"]
            signup_url = f"{reverse('kayit')}?{urlencode({'email': email})}"
            messages.info(
                self.request,
                "Bu e-posta adresiyle kayitli bir hesap bulamadik. Isterseniz yeni hesap olusturabilirsiniz.",
            )
            return redirect(signup_url)
        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    success_url = reverse_lazy("giris")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Sifreniz basariyla guncellendi. Yeni sifrenizle giris yapabilirsiniz.",
        )
        return super().form_valid(form)
