from __future__ import annotations

from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
import shutil
import uuid

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image, ImageDraw

from posts.forms import ProfilFormu
from posts.image_optimization import add_local_image_loading_attributes, optimize_profile_photo, optimize_uploaded_image
from posts.models import Icerik, Kategori, Profil


def build_noisy_image_bytes(fmt="JPEG", size=(2600, 1800)):
    image = Image.effect_noise(size, 96).convert("RGB")
    buffer = BytesIO()
    save_kwargs = {}
    if fmt == "JPEG":
        save_kwargs["quality"] = 95
    image.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


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


def build_alpha_png_bytes(size=(1200, 800)):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(100, 900):
        for y in range(100, 500):
            image.putpixel((x, y), (255, 64, 64, 160))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_rgb_png_bytes(size=(1200, 800)):
    image = Image.new("RGB", size, (48, 96, 160))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_gif_bytes(size=(320, 240)):
    image = Image.new("P", size, 1)
    buffer = BytesIO()
    image.save(buffer, format="GIF")
    return buffer.getvalue()


def build_oriented_jpeg_bytes():
    image = Image.new("RGB", (600, 1200), (24, 120, 220))
    exif = Image.Exif()
    exif[274] = 6
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95, exif=exif)
    return buffer.getvalue()


def build_center_crop_source_bytes(size=(900, 500)):
    image = Image.new("RGB", size, (220, 48, 48))
    draw = ImageDraw.Draw(image)
    left = (size[0] - size[1]) // 2
    right = left + size[1]
    draw.rectangle((left, 0, right, size[1]), fill=(48, 180, 96))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class TemporaryMediaRootMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        test_media_root = Path.cwd() / ".test_media"
        test_media_root.mkdir(exist_ok=True)
        cls._temp_media_path = test_media_root / f"{cls.__name__}-{uuid.uuid4().hex}"
        cls._temp_media_path.mkdir(parents=True, exist_ok=True)
        cls._media_override = override_settings(MEDIA_ROOT=str(cls._temp_media_path))
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media_path, ignore_errors=True)
        try:
            cls._temp_media_path.parent.rmdir()
        except OSError:
            pass
        super().tearDownClass()

    def media_path(self, relative_path):
        return self._temp_media_path / Path(relative_path.replace("/", "\\"))


class ImageOptimizationHelperTests(SimpleTestCase):
    def test_jpeg_upload_is_converted_to_webp_and_resized(self):
        original_bytes = build_noisy_image_bytes(fmt="JPEG", size=(2600, 1800))
        upload = SimpleUploadedFile("protein-photo.jpg", original_bytes, content_type="image/jpeg")

        optimized = optimize_uploaded_image(upload)
        optimized.file.seek(0)

        self.assertTrue(optimized.file.name.endswith(".webp"))
        self.assertLess(len(optimized.file.read()), len(original_bytes))

        optimized.file.seek(0)
        with Image.open(optimized.file) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertLessEqual(max(image.size), 1600)

    def test_png_with_alpha_stays_png(self):
        upload = SimpleUploadedFile("transparent.png", build_alpha_png_bytes(), content_type="image/png")

        optimized = optimize_uploaded_image(upload)
        optimized.file.seek(0)

        self.assertTrue(optimized.file.name.endswith(".png"))
        with Image.open(optimized.file) as image:
            self.assertEqual(image.format, "PNG")
            self.assertTrue(image.mode in {"RGBA", "LA", "P"})

    def test_png_without_alpha_is_converted_to_webp(self):
        upload = SimpleUploadedFile("cover.png", build_rgb_png_bytes(), content_type="image/png")

        optimized = optimize_uploaded_image(upload)

        self.assertTrue(optimized.file.name.endswith(".webp"))
        optimized.file.seek(0)
        with Image.open(optimized.file) as image:
            self.assertEqual(image.format, "WEBP")

    def test_exif_orientation_is_applied(self):
        upload = SimpleUploadedFile("phone-photo.jpg", build_oriented_jpeg_bytes(), content_type="image/jpeg")

        optimized = optimize_uploaded_image(upload)
        optimized.file.seek(0)

        with Image.open(optimized.file) as image:
            self.assertGreater(image.width, image.height)

    def test_gif_upload_is_kept_as_gif(self):
        original_bytes = build_gif_bytes()
        upload = SimpleUploadedFile("loop.gif", original_bytes, content_type="image/gif")

        optimized = optimize_uploaded_image(upload)
        optimized.file.seek(0)

        self.assertTrue(optimized.file.name.endswith(".gif"))
        self.assertEqual(optimized.file.read(), original_bytes)

    def test_local_image_attrs_filter_only_marks_local_media_images(self):
        html = (
            '<p><img src="/media/ckeditor_resimleri/photo.jpg" alt="Local"></p>'
            '<p><img src="https://example.com/external.jpg" alt="External"></p>'
        )

        rendered = add_local_image_loading_attributes(html)

        self.assertIn('src="/media/ckeditor_resimleri/photo.jpg" alt="Local" loading="lazy" decoding="async"', rendered)
        self.assertIn('src="https://example.com/external.jpg" alt="External"', rendered)
        self.assertNotIn('external.jpg" alt="External" loading="lazy"', rendered)


class ImageUploadIntegrationTests(TemporaryMediaRootMixin, TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser("admin", "admin@example.com", "password123")
        mark_onboarded(self.admin_user)
        self.category = Kategori.objects.create(isim="Supplement")

    def test_content_creation_optimizes_uploaded_image(self):
        self.client.force_login(self.admin_user)
        upload = SimpleUploadedFile("hero.jpg", build_noisy_image_bytes(), content_type="image/jpeg")

        response = self.client.post(
            f"{reverse('ekle')}?tur=haber",
            {
                "baslik": "Optimize edilen içerik",
                "yazi": "<p>İçerik gövdesi</p>",
                "kategori": self.category.id,
                "resim": upload,
            },
        )

        self.assertEqual(response.status_code, 302)

        icerik = Icerik.objects.get()
        self.assertTrue(icerik.resim.name.endswith(".webp"))
        self.assertTrue(self.media_path(icerik.resim.name).exists())

        with Image.open(self.media_path(icerik.resim.name)) as image:
            self.assertLessEqual(max(image.size), 1600)

    def test_ckeditor_upload_returns_optimized_url(self):
        self.client.force_login(self.admin_user)
        upload = SimpleUploadedFile("editor-image.jpg", build_noisy_image_bytes(), content_type="image/jpeg")

        response = self.client.post(
            reverse("ckeditor_resim_yukle"),
            {"upload": upload},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["url"].endswith(".webp"))
        relative_path = payload["url"].replace("/media/", "", 1)
        self.assertTrue(self.media_path(relative_path).exists())


class OptimizeMediaAssetsCommandTests(TemporaryMediaRootMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("writer", "writer@example.com", "password123")
        self.category = Kategori.objects.create(isim="Genel")

    def create_media_file(self, relative_path, raw_bytes):
        target = self.media_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw_bytes)
        return target

    def test_dry_run_does_not_change_database_or_write_files(self):
        self.create_media_file("icerik_resimleri/dry-run-original.jpg", build_noisy_image_bytes())
        self.create_media_file(
            "ckeditor_resimleri/ChatGPT Dry Run Image 13 Mar 2026 15_45_21.png",
            build_rgb_png_bytes(),
        )
        icerik = Icerik.objects.create(
            baslik="Dry run içerik",
            yazi='<p><img src="/media/ckeditor_resimleri/ChatGPT%20Dry%20Run%20Image%2013%20Mar%202026%2015_45_21.png"></p>',
            resim="icerik_resimleri/dry-run-original.jpg",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )

        stdout = StringIO()
        call_command("optimize_media_assets", "--dry-run", stdout=stdout)
        icerik.refresh_from_db()

        self.assertEqual(icerik.resim.name, "icerik_resimleri/dry-run-original.jpg")
        self.assertIn("ChatGPT%20Dry%20Run%20Image%2013%20Mar%202026%2015_45_21.png", icerik.yazi)
        self.assertFalse(self.media_path("icerik_resimleri/dry-run-original-optimized.webp").exists())
        self.assertFalse(self.media_path("ckeditor_resimleri/ChatGPT Dry Run Image 13 Mar 2026 15_45_21-optimized.webp").exists())

    def test_apply_updates_resim_and_ckeditor_src_and_is_idempotent(self):
        self.create_media_file("icerik_resimleri/original.jpg", build_noisy_image_bytes())
        self.create_media_file(
            "ckeditor_resimleri/ChatGPT Image 13 Mar 2026 15_45_21.png",
            build_rgb_png_bytes(),
        )
        icerik = Icerik.objects.create(
            baslik="Apply içerik",
            yazi=(
                '<p><img src="/media/ckeditor_resimleri/ChatGPT%20Image%2013%20Mar%202026%2015_45_21.png"></p>'
                '<p><img src="https://example.com/external.png"></p>'
            ),
            resim="icerik_resimleri/original.jpg",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )

        first_stdout = StringIO()
        call_command("optimize_media_assets", "--apply", stdout=first_stdout)
        icerik.refresh_from_db()

        self.assertEqual(icerik.resim.name, "icerik_resimleri/original-optimized.webp")
        self.assertIn("/media/ckeditor_resimleri/ChatGPT%20Image%2013%20Mar%202026%2015_45_21-optimized.webp", icerik.yazi)
        self.assertIn("https://example.com/external.png", icerik.yazi)
        self.assertTrue(self.media_path("icerik_resimleri/original-optimized.webp").exists())
        self.assertTrue(self.media_path("ckeditor_resimleri/ChatGPT Image 13 Mar 2026 15_45_21-optimized.webp").exists())

        second_stdout = StringIO()
        call_command("optimize_media_assets", "--apply", stdout=second_stdout)
        icerik.refresh_from_db()

        self.assertEqual(icerik.resim.name, "icerik_resimleri/original-optimized.webp")
        self.assertNotIn("-optimized-optimized", icerik.yazi)

    def test_missing_files_are_reported_without_crashing(self):
        icerik = Icerik.objects.create(
            baslik="Eksik dosya içerik",
            yazi='<p><img src="/media/ckeditor_resimleri/missing-file.png"></p>',
            resim="icerik_resimleri/missing-file.jpg",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )

        stdout = StringIO()
        call_command("optimize_media_assets", "--apply", stdout=stdout)
        icerik.refresh_from_db()

        output = stdout.getvalue()
        self.assertIn("bulunamadi", output)
        self.assertEqual(icerik.resim.name, "icerik_resimleri/missing-file.jpg")
        self.assertIn("/media/ckeditor_resimleri/missing-file.png", icerik.yazi)


class ImageRenderingTests(TemporaryMediaRootMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("writer", "writer@example.com", "password123")
        self.category = Kategori.objects.create(isim="Beslenme")

    def test_homepage_card_images_have_lazy_and_async(self):
        Icerik.objects.create(
            baslik="Ana sayfa kartı",
            yazi="<p>Test içerik</p>",
            resim="icerik_resimleri/card-image.webp",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )

        response = self.client.get(reverse("anasayfa"))

        self.assertContains(
            response,
            'class="card-img-top" alt="Ana sayfa kartı" loading="lazy" decoding="async"',
            html=False,
        )

    def test_detail_blog_template_marks_content_images_and_keeps_hero_image_eager(self):
        icerik = Icerik.objects.create(
            baslik="Detay içerik",
            yazi=(
                '<p><img src="/media/ckeditor_resimleri/local-image.jpg" alt="Local"></p>'
                '<p><img src="https://example.com/external.jpg" alt="External"></p>'
            ),
            resim="icerik_resimleri/detail-image.webp",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )

        response = self.client.get(reverse("detay", args=[icerik.id]))
        content = response.content.decode("utf-8")

        self.assertIn('src="/media/icerik_resimleri/detail-image.webp" class="img-fluid rounded shadow-sm" loading="eager" decoding="async"', content)
        self.assertIn('src="/media/ckeditor_resimleri/local-image.jpg" alt="Local" loading="lazy" decoding="async"', content)
        self.assertIn('src="https://example.com/external.jpg" alt="External"', content)
        self.assertNotIn('src="https://example.com/external.jpg" alt="External" loading="lazy"', content)

    def test_detail_question_template_marks_content_images_and_keeps_hero_image_eager(self):
        icerik = Icerik.objects.create(
            baslik="Forum soru",
            yazi='<p><img src="/media/ckeditor_resimleri/question-image.jpg" alt="Question"></p>',
            resim="icerik_resimleri/question-detail.webp",
            yazar=self.user,
            kategori=self.category,
            tur="soru",
        )

        response = self.client.get(reverse("detay", args=[icerik.id]))
        content = response.content.decode("utf-8")

        self.assertIn('src="/media/icerik_resimleri/question-detail.webp" class="img-fluid rounded border" loading="eager" decoding="async"', content)
        self.assertIn('src="/media/ckeditor_resimleri/question-image.jpg" alt="Question" loading="lazy" decoding="async"', content)


class ProfilePhotoOptimizationTests(SimpleTestCase):
    def test_profile_photo_is_cropped_to_center_square_and_saved_as_webp(self):
        upload = SimpleUploadedFile(
            "avatar.png",
            build_center_crop_source_bytes(),
            content_type="image/png",
        )

        optimized = optimize_profile_photo(upload)
        optimized.file.seek(0)

        # Avatar artık JPEG olarak kaydediliyor (Flutter decoder uyumluluğu için).
        self.assertTrue(optimized.file.name.endswith(".jpg"))
        with Image.open(optimized.file) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (512, 512))
            red, green, blue = image.convert("RGB").getpixel((8, 8))
            self.assertGreater(green, red)
            self.assertGreater(green, blue)

    def test_profile_photo_applies_exif_orientation(self):
        upload = SimpleUploadedFile("avatar.jpg", build_oriented_jpeg_bytes(), content_type="image/jpeg")

        optimized = optimize_profile_photo(upload)
        optimized.file.seek(0)

        with Image.open(optimized.file) as image:
            self.assertEqual(image.size, (512, 512))

    def test_transparent_png_profile_photo_stays_valid_after_optimization(self):
        upload = SimpleUploadedFile("avatar.png", build_alpha_png_bytes(), content_type="image/png")

        optimized = optimize_profile_photo(upload)
        optimized.file.seek(0)

        with Image.open(optimized.file) as image:
            # Transparent PNG → beyaz arka plan üstüne kompoze edilip JPEG.
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (512, 512))


class ProfilePhotoFormTests(TemporaryMediaRootMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("avatar-owner", "avatar@example.com", "password123")
        self.profile = self.user.profil

    def test_profile_form_saves_optimized_photo_and_can_remove_it(self):
        upload = SimpleUploadedFile(
            "avatar.jpg",
            build_noisy_image_bytes(fmt="JPEG", size=(1200, 900)),
            content_type="image/jpeg",
        )

        form = ProfilFormu(
            data={"hakkinda": "Yeni biyografi"},
            files={"foto": upload},
            instance=self.profile,
        )

        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save()
        first_photo_name = profile.foto.name

        self.assertTrue(first_photo_name.endswith(".jpg"))
        self.assertTrue(self.media_path(first_photo_name).exists())

        removal_form = ProfilFormu(
            data={"hakkinda": "Yeni biyografi", "foto_sil": "on"},
            instance=profile,
        )

        self.assertTrue(removal_form.is_valid(), removal_form.errors)
        removal_form.save()
        profile.refresh_from_db()

        self.assertFalse(profile.foto)
        self.assertFalse(self.media_path(first_photo_name).exists())

    def test_profile_form_rejects_gif_uploads(self):
        upload = SimpleUploadedFile("avatar.gif", build_gif_bytes(), content_type="image/gif")

        form = ProfilFormu(
            data={"hakkinda": "GIF kabul edilmemeli"},
            files={"foto": upload},
            instance=self.profile,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Sadece şu dosya türleri kabul edilir", form.errors["foto"][0])


class ProfilePhotoViewTests(TemporaryMediaRootMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("avatar-user", "avatar-user@example.com", "password123")
        mark_onboarded(self.user)

    def test_quick_profile_photo_upload_requires_authentication(self):
        response = self.client.post(reverse("profil_foto_guncelle"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/giris/", response.url)

    def test_quick_profile_photo_upload_updates_current_user(self):
        other_user = User.objects.create_user("other-user", "other@example.com", "password123")
        self.client.force_login(self.user)

        upload = SimpleUploadedFile(
            "avatar.jpg",
            build_noisy_image_bytes(fmt="JPEG", size=(1500, 1000)),
            content_type="image/jpeg",
        )
        response = self.client.post(reverse("profil_foto_guncelle"), {"foto": upload})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profil", args=[self.user.username]))

        self.user.refresh_from_db()
        other_user.refresh_from_db()
        self.assertTrue(self.user.profil.foto.name.endswith(".jpg"))
        self.assertFalse(other_user.profil.foto)
        self.assertTrue(self.media_path(self.user.profil.foto.name).exists())

    def test_profile_photo_remove_endpoint_clears_current_user_photo(self):
        self.client.force_login(self.user)
        photo_path = "profil_fotograflari/remove-me.webp"
        target = self.media_path(photo_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(build_noisy_image_bytes(fmt="WEBP", size=(512, 512)))
        self.user.profil.foto = photo_path
        self.user.profil.save(update_fields=["foto"])

        response = self.client.post(reverse("profil_foto_sil"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profil", args=[self.user.username]))
        self.user.refresh_from_db()
        self.assertFalse(self.user.profil.foto)
        self.assertFalse(target.exists())

    def test_profile_edit_view_accepts_upload_and_can_remove_photo(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile(
            "avatar.png",
            build_rgb_png_bytes(),
            content_type="image/png",
        )

        response = self.client.post(
            reverse("profil_duzenle"),
            {
                "username": self.user.username,
                "first_name": "",
                "last_name": "",
                "email": self.user.email,
                "hakkinda": "Profil güncellendi",
                "cinsiyet": "B",
                "boy": "180",
                "kilo": "82",
                "hedef_kilo": "76",
                "fitness_hedefi": "Yağ kaybı",
                "dogum_tarihi": "1998-03-12",
                "foto": upload,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        photo_name = self.user.profil.foto.name
        self.assertTrue(photo_name.endswith(".jpg"))
        self.assertTrue(self.media_path(photo_name).exists())

        response = self.client.post(
            reverse("profil_duzenle"),
            {
                "username": self.user.username,
                "first_name": "",
                "last_name": "",
                "email": self.user.email,
                "hakkinda": "Profil güncellendi",
                "cinsiyet": "B",
                "boy": "180",
                "kilo": "82",
                "hedef_kilo": "76",
                "fitness_hedefi": "Yağ kaybı",
                "dogum_tarihi": "1998-03-12",
                "foto_sil": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profil.foto)
        self.assertFalse(self.media_path(photo_name).exists())


class ProfilePhotoRenderingTests(TemporaryMediaRootMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("writer", "writer@example.com", "password123")
        self.admin = User.objects.create_superuser("admin-photo", "admin-photo@example.com", "password123")
        mark_onboarded(self.user)
        mark_onboarded(self.admin)
        self.category = Kategori.objects.create(isim="Avatar Test")

    def create_media_file(self, relative_path, raw_bytes):
        target = self.media_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw_bytes)
        return target

    def assign_avatar(self, user, relative_path):
        self.create_media_file(relative_path, build_noisy_image_bytes(fmt="WEBP", size=(512, 512)))
        profile = user.profil
        profile.foto = relative_path
        profile.save(update_fields=["foto"])
        return profile

    def test_profile_page_renders_avatar_and_quick_upload_only_for_owner(self):
        self.assign_avatar(self.user, "profil_fotograflari/profile-owner.webp")
        self.client.force_login(self.user)

        owner_response = self.client.get(reverse("profil", args=[self.user.username]))
        owner_content = owner_response.content.decode("utf-8")
        self.assertIn("/media/profil_fotograflari/profile-owner.webp", owner_content)
        self.assertIn("quick-profile-photo-input", owner_content)
        self.assertIn("profile-photo-upload-button", owner_content)
        self.assertIn(reverse("profil_foto_sil"), owner_content)

        viewer = User.objects.create_user("viewer", "viewer@example.com", "password123")
        mark_onboarded(viewer)
        self.client.force_login(viewer)
        viewer_response = self.client.get(reverse("profil", args=[self.user.username]))
        viewer_content = viewer_response.content.decode("utf-8")
        self.assertIn("/media/profil_fotograflari/profile-owner.webp", viewer_content)
        self.assertNotIn("quick-profile-photo-input", viewer_content)
        self.assertNotIn("profile-photo-upload-button", viewer_content)

    def test_profile_page_renders_without_avatar(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("profil", args=[self.user.username]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username[0].upper())
        self.assertNotContains(response, "profil.foto.url")
        self.assertNotContains(response, reverse("profil_foto_sil"))

    def test_homepage_forum_and_navbar_render_avatar_images(self):
        self.assign_avatar(self.user, "profil_fotograflari/list-avatar.webp")
        Icerik.objects.create(
            baslik="Avatarlı blog",
            yazi="<p>İçerik</p>",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )
        Icerik.objects.create(
            baslik="Avatarlı soru",
            yazi="<p>Soru</p>",
            yazar=self.user,
            kategori=self.category,
            tur="soru",
        )

        self.client.force_login(self.user)
        homepage = self.client.get(reverse("anasayfa")).content.decode("utf-8")
        forum = self.client.get(reverse("forum")).content.decode("utf-8")

        self.assertIn("/media/profil_fotograflari/list-avatar.webp", homepage)
        self.assertIn("/media/profil_fotograflari/list-avatar.webp", forum)

    def test_detail_and_admin_surfaces_render_avatar_images(self):
        self.assign_avatar(self.user, "profil_fotograflari/detail-avatar.webp")
        icerik = Icerik.objects.create(
            baslik="Detay avatar",
            yazi="<p>Detay içeriği</p>",
            yazar=self.user,
            kategori=self.category,
            tur="haber",
        )

        self.client.force_login(self.user)
        detail_content = self.client.get(reverse("detay", args=[icerik.id])).content.decode("utf-8")
        self.assertIn("/media/profil_fotograflari/detail-avatar.webp", detail_content)

        self.client.force_login(self.admin)
        admin_monitor_content = self.client.get(reverse("admin_monitor")).content.decode("utf-8")
        admin_detail_content = self.client.get(reverse("admin_user_detail", args=[self.user.id])).content.decode("utf-8")

        self.assertIn("/media/profil_fotograflari/detail-avatar.webp", admin_monitor_content)
        self.assertIn("/media/profil_fotograflari/detail-avatar.webp", admin_detail_content)
