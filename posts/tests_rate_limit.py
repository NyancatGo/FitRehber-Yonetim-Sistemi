from datetime import date

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from posts.models import Icerik, Kategori, Yorum


def mark_onboarded(user):
    profile = user.profil
    profile.boy = 180
    profile.kilo = 82
    profile.hedef_kilo = 76
    profile.fitness_hedefi = "Yağ kaybı"
    profile.dogum_tarihi = date(1998, 3, 12)
    profile.is_onboarded = True
    profile.save(
        update_fields=[
            "boy",
            "kilo",
            "hedef_kilo",
            "fitness_hedefi",
            "dogum_tarihi",
            "is_onboarded",
        ]
    )


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "posts-rate-limit-tests",
    }
}


@override_settings(
    CACHES=TEST_CACHES,
    RATELIMIT_CACHE_PREFIX="test_posts_rate_limit",
    RATELIMIT_GLOBAL_ANONYMOUS=1,
    RATELIMIT_SEARCH_MAX=2,
    RATELIMIT_SEARCH_WINDOW=60,
)
class PostActionRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="poster", password="pass")
        mark_onboarded(self.user)
        self.category = Kategori.objects.create(isim="Genel")
        self.content = Icerik.objects.create(
            baslik="Arama Basligi",
            yazi="Arama icerigi",
            yazar=self.user,
            kategori=self.category,
        )
        self.comment = Yorum.objects.create(
            icerik=self.content,
            yazar=self.user,
            mesaj="Test yorum",
        )

    def test_like_and_save_do_not_mutate_on_get_and_work_on_post(self):
        self.client.force_login(self.user)

        save_url = reverse("icerik_kaydet", args=[self.content.id])
        content_like_url = reverse("icerik_begen", args=[self.content.id])
        like_url = reverse("yorum_begen", args=[self.comment.id])

        self.assertEqual(self.client.get(save_url).status_code, 405)
        self.assertFalse(self.content.kaydedenler.filter(id=self.user.id).exists())

        save_response = self.client.post(
            save_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertTrue(save_response.json()["kaydedildi"])
        self.assertTrue(self.content.kaydedenler.filter(id=self.user.id).exists())

        self.assertEqual(self.client.get(content_like_url).status_code, 405)
        self.assertFalse(self.content.begenenler.filter(id=self.user.id).exists())

        content_like_response = self.client.post(
            content_like_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(content_like_response.status_code, 200)
        self.assertTrue(content_like_response.json()["begenildi"])
        self.assertEqual(content_like_response.json()["sayi"], 1)
        self.assertTrue(self.content.begenenler.filter(id=self.user.id).exists())

        self.assertEqual(self.client.get(like_url).status_code, 405)
        self.assertFalse(self.comment.begenenler.filter(id=self.user.id).exists())

        like_response = self.client.post(
            like_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.json()["begenildi"])
        self.assertEqual(like_response.json()["sayi"], 1)

    def test_content_like_controls_render_on_web_surfaces(self):
        self.client.force_login(self.user)
        question = Icerik.objects.create(
            baslik="Forum sorusu",
            yazi="Soru icerigi",
            yazar=self.user,
            kategori=self.category,
            tur="soru",
        )

        responses = [
            self.client.get(reverse("anasayfa")),
            self.client.get(reverse("forum")),
            self.client.get(reverse("detay", args=[self.content.id])),
            self.client.get(reverse("detay", args=[question.id])),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "icerik-begen")

        home_html = responses[0].content.decode()
        self.assertIn("btn-kaydet-", home_html)
        self.assertIn("bi-chat-left-text", home_html)
        self.assertIn("#ana-yorum-formu", home_html)
        self.assertNotIn("text-kaydet-", home_html)

    def test_live_search_throttles_silently_without_error_status(self):
        url = reverse("canli_arama")

        first = self.client.get(url, {"q": "Arama"})
        second = self.client.get(url, {"q": "Arama"})
        third = self.client.get(url, {"q": "Arama"})

        self.assertEqual(first.status_code, 200)
        self.assertIn("results", first.json())
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(third.json(), {"results": [], "throttled": True})
