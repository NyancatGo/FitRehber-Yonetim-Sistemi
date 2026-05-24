import json

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from core.middleware import RateLimitMiddleware
from core.models import BannedIP


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rate-limit-middleware-tests",
    }
}


@override_settings(
    CACHES=TEST_CACHES,
    RATELIMIT_CACHE_PREFIX="test_rate_limit",
    RATELIMIT_EXEMPT_PATHS=("/aktivite-kaydet/",),
    RATELIMIT_MANUAL_BAN_CACHE_TTL=1,
    RATELIMIT_GLOBAL_WINDOW=60,
    RATELIMIT_GLOBAL_AUTHENTICATED=40,
    RATELIMIT_GLOBAL_ANONYMOUS=2,
    RATELIMIT_GLOBAL_PENALTY=60,
    RATELIMIT_COMMENT_MAX=5,
    RATELIMIT_COMMENT_WINDOW=60,
    RATELIMIT_COMMENT_PENALTY=120,
    RATELIMIT_REACTION_MAX=20,
    RATELIMIT_REACTION_WINDOW=30,
    RATELIMIT_REACTION_PENALTY=20,
)
class RateLimitMiddlewareTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def _middleware(self):
        return RateLimitMiddleware(lambda request: HttpResponse("ok"))

    def _request(self, method="get", path="/", user=None, ajax=False, ip="10.0.0.1"):
        request_method = getattr(self.factory, method.lower())
        headers = {"REMOTE_ADDR": ip}
        if ajax:
            headers["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
        request = request_method(path, **headers)
        request.user = user or AnonymousUser()
        return request

    def test_authenticated_navigation_allows_configured_limit(self):
        user = User.objects.create_user(username="nav", password="x")
        middleware = self._middleware()

        for _ in range(40):
            response = middleware(self._request(user=user))
            self.assertEqual(response.status_code, 200)

        response = middleware(self._request(user=user))
        self.assertEqual(response.status_code, 429)

    def test_anonymous_global_limit_is_temporary_and_does_not_create_banned_ip(self):
        middleware = self._middleware()

        self.assertEqual(middleware(self._request()).status_code, 200)
        self.assertEqual(middleware(self._request()).status_code, 200)

        response = middleware(self._request())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(BannedIP.objects.count(), 0)

    @override_settings(RATELIMIT_GLOBAL_AUTHENTICATED=2)
    def test_authenticated_users_on_same_ip_have_separate_counters(self):
        user_one = User.objects.create_user(username="same-ip-one", password="x")
        user_two = User.objects.create_user(username="same-ip-two", password="x")
        middleware = self._middleware()

        self.assertEqual(middleware(self._request(user=user_one)).status_code, 200)
        self.assertEqual(middleware(self._request(user=user_one)).status_code, 200)
        self.assertEqual(middleware(self._request(user=user_two)).status_code, 200)

        response = middleware(self._request(user=user_one))
        self.assertEqual(response.status_code, 429)

    def test_comment_limit_allows_five_then_returns_ajax_penalty(self):
        user = User.objects.create_user(username="commenter", password="x")
        middleware = self._middleware()

        for _ in range(5):
            response = middleware(
                self._request(method="post", path="/detay/1/", user=user, ajax=True)
            )
            self.assertEqual(response.status_code, 200)

        response = middleware(
            self._request(method="post", path="/detay/1/", user=user, ajax=True)
        )
        self.assertEqual(response.status_code, 429)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"], "COMMENT_PENALTY")
        self.assertEqual(payload["penalty_time"], 120)

    @override_settings(RATELIMIT_GLOBAL_ANONYMOUS=1)
    def test_activity_ping_path_does_not_fill_global_counter(self):
        middleware = self._middleware()

        for _ in range(3):
            response = middleware(self._request(method="post", path="/aktivite-kaydet/"))
            self.assertEqual(response.status_code, 200)

        response = middleware(self._request())
        self.assertEqual(response.status_code, 200)
