from django.conf import settings

from posts.seo import absolute_url, static_absolute_url


def app_flags(request):
    canonical_path = getattr(request, "path", "/") or "/"
    return {
        "APP_DEBUG": settings.DEBUG,
        "SEO_SITE_NAME": getattr(settings, "SITE_NAME", "FitRehber"),
        "SEO_SITE_ALTERNATE_NAME": getattr(settings, "SITE_ALTERNATE_NAME", "Fit Rehber"),
        "SEO_SITE_URL": getattr(settings, "SITE_BASE_URL", "https://fitrehber.com.tr").rstrip("/"),
        "SEO_DEFAULT_TITLE": getattr(
            settings,
            "DEFAULT_SEO_TITLE",
            "FitRehber | Bilimsel Fitness, Beslenme ve Supplement Rehberi",
        ),
        "SEO_DEFAULT_DESCRIPTION": getattr(settings, "DEFAULT_SEO_DESCRIPTION", ""),
        "SEO_DEFAULT_IMAGE": static_absolute_url("images/og-default.png"),
        "SEO_ORGANIZATION_LOGO": static_absolute_url("images/favicons/android-icon-192x192.png"),
        "SEO_CANONICAL_URL": absolute_url(canonical_path),
    }
