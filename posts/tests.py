from datetime import date
from pathlib import Path

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from .forms import KullaniciKayitFormu, OnboardingForm, ProfilFormu
from .models import (
    Aktivite,
    Icerik,
    Kategori,
    Profil,
    Yorum,
    check_rozet_aktiviteleri,
)
from .views import _build_biometric_summary


class ProfilFormuTests(SimpleTestCase):
    def test_biometric_fields_are_available(self):
        form = ProfilFormu()

        for field_name in (
            "boy",
            "kilo",
            "hedef_kilo",
            "fitness_hedefi",
            "dogum_tarihi",
        ):
            self.assertIn(field_name, form.fields)

    def test_cinsiyet_is_not_editable(self):
        # Cinsiyet immutable — onboarding'de bir kez secilir, profilden
        # degistirilemez. ProfilFormu fields'a dahil degil; POST edilse de
        # ignore edilir, DB'deki deger korunur.
        form = ProfilFormu()
        self.assertNotIn("cinsiyet", form.fields)

    def test_cinsiyet_in_post_data_is_silently_ignored(self):
        # Birisi DOM'u manuel manipule edip 'cinsiyet': 'K' gonderirse form
        # validasyondan gecmeli (alan yok), ama Profil instance.cinsiyet
        # degerine dokunulmamali.
        instance = Profil(
            is_onboarded=True,
            cinsiyet="E",
            boy=180,
            kilo=82,
            hedef_kilo=76,
            fitness_hedefi="Yağ kaybı",
            dogum_tarihi=date(1998, 3, 12),
        )
        form = ProfilFormu(
            data={
                "hakkinda": "Yeni hakkinda",
                "cinsiyet": "K",  # ignore edilmeli
                "boy": "180",
                "kilo": "82",
                "hedef_kilo": "76",
                "fitness_hedefi": "Yağ kaybı",
                "dogum_tarihi": "1998-03-12",
            },
            instance=instance,
        )
        self.assertTrue(form.is_valid(), form.errors)
        # form.save(commit=False) instance'i guncellemeli ama cinsiyet
        # alanini degistirmemeli — cunku Meta.fields'da yok.
        updated = form.save(commit=False)
        self.assertEqual(updated.cinsiyet, "E")

    def test_biometric_numbers_must_be_positive(self):
        form = ProfilFormu(
            data={
                "hakkinda": "Test profil",
                "boy": "-180",
                "kilo": "0",
                "hedef_kilo": "-75",
                "fitness_hedefi": "Kondisyon",
                "dogum_tarihi": "1998-03-12",
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("boy", form.errors)
        self.assertIn("kilo", form.errors)
        self.assertIn("hedef_kilo", form.errors)

    def test_onboarded_profile_cannot_clear_required_fields(self):
        form = ProfilFormu(
            data={
                "hakkinda": "Test profil",
                "boy": "",
                "kilo": "",
                "hedef_kilo": "",
                "fitness_hedefi": "",
                "dogum_tarihi": "",
            },
            instance=Profil(is_onboarded=True),
        )

        self.assertFalse(form.is_valid())
        for field_name in ("boy", "kilo", "hedef_kilo", "fitness_hedefi", "dogum_tarihi"):
            self.assertIn(field_name, form.errors)

    def test_profile_form_rejects_freetext_goal(self):
        # Profilde de fitness_hedefi serbest text yerine sabit listeden;
        # onboarding ile tutarli.
        form = ProfilFormu(
            data={
                "hakkinda": "Test",
                "boy": "180",
                "kilo": "82",
                "hedef_kilo": "76",
                "fitness_hedefi": "Maraton kosmak",
                "dogum_tarihi": "1998-03-12",
            },
            instance=Profil(is_onboarded=True),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fitness_hedefi", form.errors)

    def test_profile_form_accepts_all_three_allowed_goals(self):
        for goal in ("Yağ kaybı", "Kas kazanımı", "Kondisyon ve genel sağlık"):
            with self.subTest(goal=goal):
                form = ProfilFormu(
                    data={
                        "hakkinda": "Test",
                        "boy": "180",
                        "kilo": "82",
                        "hedef_kilo": "76",
                        "fitness_hedefi": goal,
                        "dogum_tarihi": "1998-03-12",
                    },
                    instance=Profil(is_onboarded=True),
                )
                self.assertTrue(form.is_valid(), form.errors)

    def test_profile_form_maps_legacy_goal_initial_to_allowed_choice(self):
        form = ProfilFormu(instance=Profil(fitness_hedefi="Yağ yakımı"))

        self.assertEqual(form.fields["fitness_hedefi"].initial, "Yağ kaybı")

    def test_profile_edit_template_does_not_expose_django_comment(self):
        template = Path(__file__).resolve().parent / "templates" / "profil_duzenle.html"

        self.assertNotIn("{# Cinsiyet", template.read_text(encoding="utf-8"))


class OnboardingFormTests(SimpleTestCase):
    def test_requires_core_biometric_fields(self):
        form = OnboardingForm(data={})

        self.assertFalse(form.is_valid())
        for field_name in (
            "cinsiyet",
            "boy",
            "kilo",
            "hedef_kilo",
            "fitness_hedefi",
            "dogum_tarihi",
        ):
            self.assertIn(field_name, form.errors)

    def test_accepts_valid_onboarding_payload(self):
        form = OnboardingForm(
            data={
                "first_name": "Baran",
                "last_name": "Fit",
                "cinsiyet": "E",
                "boy": "180",
                "kilo": "82.5",
                "hedef_kilo": "76",
                "fitness_hedefi": "Yağ kaybı",
                "dogum_tarihi": "1998-03-12",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_belirtmem_gender(self):
        # Onboarding'de 'B' kabul edilmez — kullanici acikca E veya K secmeli.
        form = OnboardingForm(
            data={
                "cinsiyet": "B",
                "boy": "180",
                "kilo": "82",
                "hedef_kilo": "76",
                "fitness_hedefi": "Yağ kaybı",
                "dogum_tarihi": "1998-03-12",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("cinsiyet", form.errors)

    def test_rejects_freetext_goal(self):
        # Sabit liste disinda bir hedef girilirse reddedilir.
        form = OnboardingForm(
            data={
                "cinsiyet": "E",
                "boy": "180",
                "kilo": "82",
                "hedef_kilo": "76",
                "fitness_hedefi": "Maraton kosmak",
                "dogum_tarihi": "1998-03-12",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fitness_hedefi", form.errors)

    def test_accepts_all_three_allowed_goals(self):
        # 3 sabit hedef de gecerli olmali.
        for goal in ("Yağ kaybı", "Kas kazanımı", "Kondisyon ve genel sağlık"):
            with self.subTest(goal=goal):
                form = OnboardingForm(
                    data={
                        "first_name": "Test",
                        "last_name": "Kullanici",
                        "cinsiyet": "K",
                        "boy": "165",
                        "kilo": "62",
                        "hedef_kilo": "60",
                        "fitness_hedefi": goal,
                        "dogum_tarihi": "1998-03-12",
                    }
                )
                self.assertTrue(form.is_valid(), form.errors)


class KullaniciKayitFormuTests(SimpleTestCase):
    """Kayit formu Ad/Soyad sormaz — bu bilgi onboarding adiminda alinir,
    boylece mobil uygulamayla tutarli kalir."""

    def test_kayit_formu_has_no_name_fields(self):
        form = KullaniciKayitFormu()
        self.assertNotIn("first_name", form.fields)
        self.assertNotIn("last_name", form.fields)
        # Temel alanlar yerinde kalmali.
        for field_name in ("username", "email", "password1", "password2"):
            self.assertIn(field_name, form.fields)

    def test_onboarding_form_requires_name(self):
        # Ad/Soyad onboarding'e tasindi ve zorunlu — bos birakilamaz.
        form = OnboardingForm()
        self.assertIn("first_name", form.fields)
        self.assertIn("last_name", form.fields)
        self.assertTrue(form.fields["first_name"].required)
        self.assertTrue(form.fields["last_name"].required)

    def test_onboarding_form_rejects_missing_name(self):
        form = OnboardingForm(
            data={
                "cinsiyet": "E",
                "boy": "180",
                "kilo": "82",
                "hedef_kilo": "76",
                "fitness_hedefi": "Yağ kaybı",
                "dogum_tarihi": "1998-03-12",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)
        self.assertIn("last_name", form.errors)


class BiometricSummaryTests(SimpleTestCase):
    """target_progress hesabi mobile profile_screen.dart ile birebir ayni
    olmali — yolculuk-bazli (start→target). Eski oran-bazli (current/baseline)
    mantik regresyon olarak donmemeli."""

    def _profil(self, *, start, current, target, **extras):
        return Profil(
            boy=180,
            baslangic_kilo=start,
            kilo=current,
            hedef_kilo=target,
            fitness_hedefi=extras.get("hedef", "Yağ kaybı"),
            dogum_tarihi=extras.get("dogum_tarihi", date(1998, 3, 12)),
        )

    def test_half_progress_when_traveled_half_path(self):
        # 90 -> 75 (15kg total). 82'dayiz: 8kg gidildi -> %53.
        biy = _build_biometric_summary(self._profil(start=90, current=82, target=75))
        self.assertTrue(biy["has_goal"])
        self.assertEqual(biy["target_progress"], 53)
        self.assertIn("Hedefe", biy["target_status"])

    def test_completed_when_current_matches_target(self):
        biy = _build_biometric_summary(self._profil(start=90, current=75, target=75))
        self.assertEqual(biy["target_progress"], 100)
        self.assertEqual(biy["target_status"], "Hedef kilodasın")

    def test_zero_progress_when_going_wrong_direction(self):
        # Hedef 75 ama kullanici 92'ye cikmis (start 90'di) -> ters yon, %0.
        biy = _build_biometric_summary(self._profil(start=90, current=92, target=75))
        self.assertEqual(biy["target_progress"], 0)

    def test_zero_progress_when_start_weight_missing(self):
        # baslangic_kilo NULL -> fallback olarak mevcut alinir, gidilen=0.
        biy = _build_biometric_summary(self._profil(start=None, current=82, target=75))
        self.assertEqual(biy["target_progress"], 0)
        # Status hala "Hedefe X kaldı" formatinda
        self.assertIn("Hedefe", biy["target_status"])

    def test_bulk_path_traveling_up(self):
        # Kas kazanma: 70 -> 80 (10kg total). 73'tesin -> 3kg gidildi -> %30.
        biy = _build_biometric_summary(self._profil(start=70, current=73, target=80))
        self.assertEqual(biy["target_progress"], 30)
        self.assertIn("artış", biy["target_status"])

    def test_no_progress_value_when_goal_missing(self):
        biy = _build_biometric_summary(self._profil(start=80, current=80, target=None))
        self.assertFalse(biy["has_goal"])
        self.assertEqual(biy["target_progress"], 0)
        self.assertEqual(biy["target_status"], "Hedef kilo eklenmedi")

    def test_progress_does_not_exceed_100_when_overshoot(self):
        # Hedef 75'ti, kullanici 70'e indi (hedefi 5kg gecmis) -> bar dolu.
        biy = _build_biometric_summary(self._profil(start=90, current=70, target=75))
        self.assertEqual(biy["target_progress"], 100)


class BadgeLikeMetricTests(TestCase):
    def test_content_likes_count_toward_like_badge(self):
        liker = User.objects.create_user(username="liker", password="pass")
        author = User.objects.create_user(username="author", password="pass")
        category = Kategori.objects.create(isim="Genel")
        items = [
            Icerik(
                baslik=f"Icerik {index}",
                yazi="Test",
                yazar=author,
                kategori=category,
            )
            for index in range(200)
        ]
        Icerik.objects.bulk_create(items)
        items = list(Icerik.objects.filter(yazar=author).order_by("id"))
        through_model = Icerik.begenenler.through
        through_model.objects.bulk_create(
            [through_model(user=liker, icerik=item) for item in items]
        )

        check_rozet_aktiviteleri(liker)

        self.assertTrue(
            Aktivite.objects.filter(
                user=liker,
                tur="rozet",
                detay="Beğenme rozetini kazandın",
            ).exists()
        )


class OnboardingMiddlewareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="newbie", password="pass12345")

    def test_redirects_unonboarded_user_from_main_content(self):
        self.client.login(username="newbie", password="pass12345")

        response = self.client.get("/forum/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/onboarding/")

    def test_allows_onboarding_page_for_unonboarded_user(self):
        self.client.login(username="newbie", password="pass12345")

        response = self.client.get("/onboarding/")

        self.assertEqual(response.status_code, 200)

    def test_allows_onboarded_user_to_reach_home(self):
        self.user.profil.boy = 180
        self.user.profil.kilo = 82
        self.user.profil.hedef_kilo = 76
        self.user.profil.fitness_hedefi = "Yağ kaybı"
        self.user.profil.dogum_tarihi = "1998-03-12"
        self.user.profil.is_onboarded = True
        self.user.profil.save()
        self.client.login(username="newbie", password="pass12345")

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)


class ContentLikeActivityCleanupTests(TestCase):
    """Beğeni/kayıt geri alındığında ilgili Aktivite kaydı da silinmeli.

    m2m_changed post_remove sinyalleri — API'deki _aktivite_sil davranışıyla
    parite. Beğeni geri alma sonrası aktivite akışında bayat kayıt kalmamalı."""

    def setUp(self):
        self.user = User.objects.create_user("liker", password="pass12345")
        self.author = User.objects.create_user("author", password="pass12345")
        self.icerik = Icerik.objects.create(
            baslik="Test", yazi="icerik", tur="haber", yazar=self.author,
        )

    def test_unliking_content_removes_its_activity(self):
        self.icerik.begenenler.add(self.user)
        self.assertTrue(
            Aktivite.objects.filter(
                user=self.user, tur="begeni",
                icerik=self.icerik, yorum__isnull=True,
            ).exists()
        )

        self.icerik.begenenler.remove(self.user)

        self.assertFalse(
            Aktivite.objects.filter(
                user=self.user, tur="begeni", icerik=self.icerik,
            ).exists()
        )

    def test_unliking_content_keeps_comment_like_activity(self):
        """İçerik beğenisi geri alınınca, aynı makaledeki yorum-beğeni
        Aktivite'si silinmemeli."""
        yorum = Yorum.objects.create(
            mesaj="yorum", icerik=self.icerik, yazar=self.author, depth=0,
        )
        yorum.begenenler.add(self.user)
        self.icerik.begenenler.add(self.user)

        self.icerik.begenenler.remove(self.user)

        self.assertTrue(
            Aktivite.objects.filter(
                user=self.user, tur="begeni", yorum=yorum,
            ).exists()
        )

    def test_unliking_comment_removes_its_activity(self):
        yorum = Yorum.objects.create(
            mesaj="yorum", icerik=self.icerik, yazar=self.author, depth=0,
        )
        yorum.begenenler.add(self.user)
        self.assertTrue(
            Aktivite.objects.filter(
                user=self.user, tur="begeni", yorum=yorum,
            ).exists()
        )

        yorum.begenenler.remove(self.user)

        self.assertFalse(
            Aktivite.objects.filter(
                user=self.user, tur="begeni", yorum=yorum,
            ).exists()
        )

    def test_unsaving_content_removes_its_activity(self):
        self.icerik.kaydedenler.add(self.user)
        self.assertTrue(
            Aktivite.objects.filter(
                user=self.user, tur="kayit", icerik=self.icerik,
            ).exists()
        )

        self.icerik.kaydedenler.remove(self.user)

        self.assertFalse(
            Aktivite.objects.filter(
                user=self.user, tur="kayit", icerik=self.icerik,
            ).exists()
        )
