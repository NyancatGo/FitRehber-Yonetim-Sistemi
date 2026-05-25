from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import render

from core.models import BannedIP
from core.security_utils import get_client_ip


class AutoLoginMiddleware:
    """Demo kolayligi: yonetim panelinde belirlenmis kullaniciyi otomatik loglar.

    Sadece settings.AUTO_LOGIN_AS doluyken devreye girer ve settings.py icinde
    yalnizca DEBUG=True iken MIDDLEWARE listesine eklenir. Production icin
    hicbir etkisi yoktur.

    Hocanin tek-tik deneyimi icin: baslat.bat -> tarayici -> panel direkt acilir.
    """

    PANEL_PATH_PREFIX = "/yonetim-sistemi/"
    LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
    SKIP_PATH_PREFIXES = (
        "/accounts/logout/",
        "/cikis/",
    )

    BACKEND_PATH = "django.contrib.auth.backends.ModelBackend"

    def __init__(self, get_response):
        self.get_response = get_response
        self.username = (getattr(settings, "AUTO_LOGIN_AS", "") or "").strip()

    def __call__(self, request):
        path = request.path_info or request.path
        if (
            self.username
            and not getattr(request.user, "is_authenticated", False)
            and path.startswith(self.PANEL_PATH_PREFIX)
            and self._is_local_request(request)
            and not any(path.startswith(p) for p in self.SKIP_PATH_PREFIXES)
        ):
            self._auto_login(request)
        return self.get_response(request)

    def _is_local_request(self, request):
        host = request.get_host().lower()
        if host.startswith("["):
            host = host[1:].split("]", 1)[0]
        else:
            host = host.split(":", 1)[0]
        return host in self.LOCAL_HOSTS

    def _auto_login(self, request):
        from django.contrib.auth import login, get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(
                username=self.username,
                is_active=True,
                is_superuser=True,
            )
        except (User.DoesNotExist, DatabaseError):
            # Demo kullanicisi henuz kurulmamis veya DB hazir degil; sessizce gec
            return
        login(request, user, backend=self.BACKEND_PATH)


class RateLimitMiddleware:
    """Comfort-first rate limiter with manual IP bans and scoped cooldowns."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    COMMENT_PATH_PREFIXES = ("/yorum-yap/", "/cevap-ver/", "/detay/")

    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_prefix = getattr(settings, "RATELIMIT_CACHE_PREFIX", "rate_limit_v2")
        self.exempt_paths = tuple(
            getattr(
                settings,
                "RATELIMIT_EXEMPT_PATHS",
                (
                    "/static/",
                    "/media/",
                    "/admin/",
                    "/aktivite-kaydet/",
                    "/canli-arama/",
                ),
            )
        )
        self.manual_ban_cache_ttl = getattr(settings, "RATELIMIT_MANUAL_BAN_CACHE_TTL", 300)

        self.global_window = getattr(settings, "RATELIMIT_GLOBAL_WINDOW", 60)
        self.global_penalty = getattr(settings, "RATELIMIT_GLOBAL_PENALTY", 60)
        self.global_authenticated = getattr(settings, "RATELIMIT_GLOBAL_AUTHENTICATED", 240)
        self.global_anonymous = getattr(settings, "RATELIMIT_GLOBAL_ANONYMOUS", 120)

        self.comment_max = getattr(settings, "RATELIMIT_COMMENT_MAX", 5)
        self.comment_window = getattr(settings, "RATELIMIT_COMMENT_WINDOW", 60)
        self.comment_penalty = getattr(settings, "RATELIMIT_COMMENT_PENALTY", 120)

        self.reaction_max = getattr(settings, "RATELIMIT_REACTION_MAX", 20)
        self.reaction_window = getattr(settings, "RATELIMIT_REACTION_WINDOW", 30)
        self.reaction_penalty = getattr(settings, "RATELIMIT_REACTION_PENALTY", 20)

    def __call__(self, request):
        path = request.path_info or request.path
        ip_address = get_client_ip(request)

        if self._is_manually_banned(ip_address):
            return self._limit_response(
                request,
                error_code="MANUAL_IP_BAN",
                message="Bu IP adresi engellenmiş durumda.",
                penalty_time=None,
                level=3,
            )

        if self._is_exempt_path(path):
            return self.get_response(request)

        actor_key, actor_type = self._actor_key(request, ip_address)

        scoped_response = self._check_scoped_limits(request, actor_key)
        if scoped_response is not None:
            return scoped_response

        global_response = self._check_global_limit(request, actor_key, actor_type)
        if global_response is not None:
            return global_response

        return self.get_response(request)

    def _is_exempt_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.exempt_paths)

    def _is_ajax(self, request) -> bool:
        return (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or request.headers.get("sec-fetch-mode") == "cors"
        )

    def _cache_key(self, *parts: object) -> str:
        clean_parts = [str(part).strip(":") for part in parts]
        return ":".join([self.cache_prefix, *clean_parts])

    def _actor_key(self, request, ip_address: str) -> tuple[str, str]:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            return f"user:{user.pk}", "authenticated"
        return f"ip:{ip_address}", "anonymous"

    def _is_manually_banned(self, ip_address: str) -> bool:
        cache_key = self._cache_key("manual_ban", ip_address)
        cached = cache.get(cache_key)
        if cached is not None:
            return bool(cached)

        try:
            is_banned = BannedIP.objects.filter(ip_address=ip_address).exists()
        except DatabaseError:
            is_banned = False

        cache.set(cache_key, is_banned, self.manual_ban_cache_ttl)
        return is_banned

    def _check_scoped_limits(self, request, actor_key: str):
        if self._is_comment_action(request):
            return self._check_limited_scope(
                request=request,
                actor_key=actor_key,
                scope="comment",
                limit=self.comment_max,
                window=self.comment_window,
                penalty=self.comment_penalty,
                error_code="COMMENT_PENALTY",
                message="Çok hızlı yorum yapıyorsunuz. Lütfen biraz bekleyin.",
                level=0,
            )

        if request.method not in self.SAFE_METHODS:
            return self._check_limited_scope(
                request=request,
                actor_key=actor_key,
                scope="action",
                limit=self.reaction_max,
                window=self.reaction_window,
                penalty=self.reaction_penalty,
                error_code="BURST_PENALTY",
                message="Çok hızlı işlem yapıyorsunuz. Lütfen biraz bekleyin.",
                level=0,
            )

        return None

    def _check_global_limit(self, request, actor_key: str, actor_type: str):
        limit = (
            self.global_authenticated
            if actor_type == "authenticated"
            else self.global_anonymous
        )
        return self._check_limited_scope(
            request=request,
            actor_key=actor_key,
            scope="global",
            limit=limit,
            window=self.global_window,
            penalty=self.global_penalty,
            error_code="RATE_LIMIT",
            message="Çok fazla istek gönderildi. Lütfen biraz bekleyin.",
            level=1,
        )

    def _is_comment_action(self, request) -> bool:
        if request.method != "POST":
            return False
        path = request.path_info or request.path
        return any(path.startswith(prefix) for prefix in self.COMMENT_PATH_PREFIXES)

    def _check_limited_scope(
        self,
        *,
        request,
        actor_key: str,
        scope: str,
        limit: int,
        window: int,
        penalty: int,
        error_code: str,
        message: str,
        level: int,
    ):
        now = int(time.time())
        cooldown_key = self._cache_key("cooldown", scope, actor_key)
        remaining = self._cooldown_remaining(cooldown_key, now)
        if remaining > 0:
            return self._limit_response(
                request,
                error_code=error_code,
                message=message,
                penalty_time=remaining,
                level=level,
            )

        counter_key = self._cache_key("counter", scope, actor_key)
        current_count = self._increment_counter(counter_key, window)

        if current_count > limit:
            cooldown_until = now + penalty
            cache.set(cooldown_key, cooldown_until, penalty)
            return self._limit_response(
                request,
                error_code=error_code,
                message=message,
                penalty_time=penalty,
                level=level,
            )

        return None

    def _increment_counter(self, key: str, window: int) -> int:
        try:
            return cache.incr(key)
        except ValueError:
            cache.set(key, 1, window)
            return 1

    def _cooldown_remaining(self, key: str, now: int) -> int:
        cooldown_until = cache.get(key)
        if not cooldown_until:
            return 0
        return max(int(cooldown_until) - now, 0)

    def _limit_response(
        self,
        request,
        *,
        error_code: str,
        message: str,
        penalty_time: int | None,
        level: int,
    ):
        if self._is_ajax(request):
            payload = {"error": error_code, "message": message}
            if penalty_time is not None:
                payload["penalty_time"] = penalty_time
            return JsonResponse(payload, status=429)

        return render(
            request,
            "rate_limit_429.html",
            {"level": level, "burst_penalty": penalty_time or self.global_penalty},
            status=429,
        )
