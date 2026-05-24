from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Icerik, Kategori


@override_settings(SITE_BASE_URL="https://fitrehber.com.tr")
class SeoEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seo_user", email="seo@example.com", password="pass")
        self.category = Kategori.objects.create(isim="Beslenme")
        self.article = Icerik.objects.create(
            baslik="Protein Alımı Nasıl Planlanır?",
            yazi="<p>Protein alımı; hedef, kilo ve antrenman düzenine göre planlanmalıdır.</p>",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )

    def test_home_has_fitrehber_seo_signals(self):
        response = self.client.get(reverse("anasayfa"))

        self.assertContains(response, "FitRehber | Bilimsel Fitness, Beslenme ve Supplement Rehberi")
        self.assertContains(response, '<meta property="og:site_name" content="FitRehber">')
        self.assertContains(response, "FitRehber: Bilimsel Fitness ve Beslenme Rehberi")
        self.assertNotContains(response, "Fit Rehber Logo")
        self.assertNotContains(response, "Fit Yaşam - Blog")

    def test_article_detail_has_article_schema_and_absolute_image(self):
        response = self.client.get(reverse("detay", args=[self.article.id]))

        self.assertContains(response, "Protein Alımı Nasıl Planlanır? | FitRehber")
        self.assertContains(response, '<meta property="og:type" content="article">')
        self.assertContains(response, '"@type":"BlogPosting"')
        self.assertContains(response, "https://fitrehber.com.tr/static/images/og-default.png")

    def test_robots_txt_exposes_sitemap(self):
        response = self.client.get(reverse("robots_txt"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        body = response.content.decode("utf-8")
        self.assertIn("User-agent: *", body)
        self.assertIn("Disallow: /admin/", body)
        self.assertIn("Sitemap: https://fitrehber.com.tr/sitemap.xml", body)

    def test_sitemap_uses_canonical_domain_and_public_urls(self):
        response = self.client.get(reverse("sitemap_xml"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/xml"))
        body = response.content.decode("utf-8")
        self.assertIn("<loc>https://fitrehber.com.tr/</loc>", body)
        self.assertIn(f"<loc>https://fitrehber.com.tr/detay/{self.article.id}/</loc>", body)
        self.assertNotIn("example.com", body)
        self.assertNotIn("?kategori=", body)
