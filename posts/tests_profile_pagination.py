from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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


class ProfilePaginationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        mark_onboarded(self.owner)
        mark_onboarded(self.other)
        self.category = Kategori.objects.create(isim="Genel")

    def _create_content(self, title, author=None, minutes=0):
        item = Icerik.objects.create(
            baslik=title,
            yazi=f"{title} yazısı",
            yazar=author or self.owner,
            kategori=self.category,
        )
        Icerik.objects.filter(pk=item.pk).update(tarih=timezone.now() + timedelta(minutes=minutes))
        item.refresh_from_db()
        return item

    def _create_owner_posts(self, count):
        return [
            self._create_content(f"Paylaşım {index}", minutes=index)
            for index in range(1, count + 1)
        ]

    def test_profile_page_renders_only_first_three_posts(self):
        self._create_owner_posts(5)

        response = self.client.get(reverse("profil", args=[self.owner.username]))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Paylaşım 5", html)
        self.assertIn("Paylaşım 4", html)
        self.assertIn("Paylaşım 3", html)
        self.assertNotIn("Paylaşım 2", html)
        self.assertNotIn("Paylaşım 1", html)
        self.assertIn("let currentTotalPages = 2;", html)

    def test_profile_content_endpoint_returns_requested_page_metadata(self):
        self._create_owner_posts(5)

        response = self.client.get(
            reverse("profil_icerikleri", args=[self.owner.username]),
            {"type": "paylasim", "page": 2},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "paylasim")
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(data["total_count"], 5)
        self.assertTrue(data["has_previous"])
        self.assertFalse(data["has_next"])
        self.assertIn("Paylaşım 2", data["html"])
        self.assertIn("Paylaşım 1", data["html"])
        self.assertNotIn("Paylaşım 5", data["html"])

    def test_owner_can_page_saved_and_liked_content(self):
        saved_item = self._create_content("Kaydedilen İçerik", author=self.other, minutes=10)
        self.owner.kaydedilen_icerikler.add(saved_item)
        liked_item = self._create_content("Begenilen Icerik", author=self.other, minutes=11)
        liked_item.begenenler.add(self.owner)
        comment = Yorum.objects.create(
            icerik=saved_item,
            yazar=self.other,
            mesaj="Beğenilen güzel yorum",
        )
        comment.begenenler.add(self.owner)
        self.client.force_login(self.owner)

        saved_response = self.client.get(
            reverse("profil_icerikleri", args=[self.owner.username]),
            {"type": "kaydedilen", "page": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        liked_response = self.client.get(
            reverse("profil_icerikleri", args=[self.owner.username]),
            {"type": "begeni", "page": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(saved_response.status_code, 200)
        self.assertIn("Kaydedilen İçerik", saved_response.json()["html"])
        self.assertEqual(liked_response.status_code, 200)
        self.assertIn("Begenilen Icerik", liked_response.json()["html"])
        self.assertIn("Beğenilen güzel yorum", liked_response.json()["html"])

    def test_private_profile_lists_are_forbidden_to_non_owner_and_anonymous(self):
        self.client.force_login(self.other)
        private_url = reverse("profil_icerikleri", args=[self.owner.username])

        other_response = self.client.get(
            private_url,
            {"type": "kaydedilen", "page": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.client.logout()
        anonymous_response = self.client.get(
            private_url,
            {"type": "begeni", "page": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(other_response.status_code, 403)
        self.assertEqual(anonymous_response.status_code, 403)

    def test_invalid_type_returns_bad_request(self):
        response = self.client.get(
            reverse("profil_icerikleri", args=[self.owner.username]),
            {"type": "unknown", "page": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)

    def test_large_page_number_is_clamped_to_last_page(self):
        self._create_owner_posts(5)

        response = self.client.get(
            reverse("profil_icerikleri", args=[self.owner.username]),
            {"type": "paylasim", "page": 999},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["page"], 2)
        self.assertIn("Paylaşım 2", data["html"])
