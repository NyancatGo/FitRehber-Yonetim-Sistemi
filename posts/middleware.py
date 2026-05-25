from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render
from django.contrib.auth import logout


class BanCheckMiddleware:
    """
    Banlı kullanıcıları her istekte kontrol eder.
    Banlıysa oturumu kapatır ve kırmızı ban ekranını gösterir.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'profil'):
            if request.user.profil.is_banned:
                username = request.user.username
                logout(request)
                return render(request, 'banli.html', {'banned_username': username}, status=403)

        return self.get_response(request)


class OnboardingRedirectMiddleware:
    """Redirect authenticated users to onboarding until required profile data exists."""

    EXEMPT_PREFIXES = (
        '/onboarding/',
        '/cikis/',
        '/giris/',
        '/kayit/',
        '/accounts/',
        '/hesap/',
        '/static/',
        '/media/',
        '/admin/',
        '/yonetim/',
        '/yonetim-sistemi/',
        '/ckeditor-yukle/',
        '/dogrulama-gonder/',
    )
    EXEMPT_EXACT_PATHS = (
        '/robots.txt',
        '/sitemap.xml',
        '/google4c81f11de67ce22.html',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or request.path
        user = getattr(request, 'user', None)

        if (
            getattr(user, 'is_authenticated', False)
            and not self._is_exempt_path(path)
            and not self._is_onboarded(user)
        ):
            return redirect('onboarding')

        return self.get_response(request)

    def _is_exempt_path(self, path):
        return path in self.EXEMPT_EXACT_PATHS or any(
            path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES
        )

    def _is_onboarded(self, user):
        try:
            return bool(user.profil.is_onboarded)
        except (AttributeError, ObjectDoesNotExist):
            return False
