import json
from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.adapters import MyAccountAdapter
from core.email_service import get_email_service, reset_email_service


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "email-tests",
    }
}


@override_settings(CACHES=TEST_CACHES, RESEND_API_KEY="test-key")
class EmailInfrastructureTest(TestCase):
    def setUp(self):
        reset_email_service()
        cache.clear()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            is_active=False,
        )
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=False,
        )
        self.active_user = User.objects.create_user(
            username="activeuser",
            email="active@example.com",
            password="testpassword",
            is_active=True,
        )
        self.service = get_email_service()

    def tearDown(self):
        reset_email_service()
        cache.clear()

    def test_email_service_singleton(self):
        service1 = get_email_service()
        service2 = get_email_service()
        self.assertIs(service1, service2)

    @patch("core.email_service.EmailService.send_email")
    def test_send_template_email(self, mock_send_email):
        mock_send_email.return_value = {"id": "test-id"}

        response = self.service.send_template_email(
            to="recipient@example.com",
            subject="Test Subject",
            template_name="emails/email_verification.html",
            context={"username": "testuser", "verification_url": "http://test.com"},
        )

        self.assertEqual(response, {"id": "test-id"})
        mock_send_email.assert_called_once()

    @patch("core.email_service.get_email_service")
    def test_account_adapter_uses_email_service_for_confirmation(self, mock_get_service):
        fake_service = Mock()
        fake_service.send_template_email.return_value = {"id": "sent"}
        mock_get_service.return_value = fake_service

        adapter = MyAccountAdapter()
        adapter.send_mail(
            "account/email/email_confirmation",
            "recipient@example.com",
            {
                "user": self.user,
                "activate_url": "https://fitrehber.com.tr/confirm/test",
            },
        )

        fake_service.send_template_email.assert_called_once()

    @patch("core.forms.get_email_service")
    def test_password_reset_uses_premium_email_template_for_inactive_user(self, mock_get_service):
        fake_service = Mock()
        fake_service.send_template_email.return_value = {"id": "reset-id"}
        mock_get_service.return_value = fake_service

        response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.email},
        )

        self.assertRedirects(
            response,
            reverse("password_reset_done"),
            fetch_redirect_response=False,
        )
        fake_service.send_template_email.assert_called_once()

        kwargs = fake_service.send_template_email.call_args.kwargs
        self.assertEqual(kwargs["to"], self.user.email)
        self.assertEqual(kwargs["template_name"], "emails/password_reset.html")
        self.assertEqual(kwargs["context"]["username"], self.user.username)
        self.assertTrue(kwargs["context"]["reset_url"].startswith("https://testserver/"))
        self.assertIn("/hesap/reset/", kwargs["context"]["reset_url"])

    @patch("core.forms.get_email_service")
    def test_password_reset_redirects_unknown_email_to_signup(self, mock_get_service):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "missing@example.com"},
        )

        self.assertRedirects(
            response,
            f"{reverse('kayit')}?email=missing%40example.com",
            fetch_redirect_response=False,
        )
        mock_get_service.assert_not_called()

    def test_signup_page_prefills_email_from_query_string(self):
        response = self.client.get(
            reverse("kayit"),
            {"email": "missing@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="missing@example.com"')

    @patch("core.forms.get_email_service")
    def test_password_reset_applies_email_cooldown(self, mock_get_service):
        fake_service = Mock()
        fake_service.send_template_email.return_value = {"id": "reset-id"}
        mock_get_service.return_value = fake_service

        first_response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.email},
        )
        second_response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.email},
        )

        self.assertRedirects(
            first_response,
            reverse("password_reset_done"),
            fetch_redirect_response=False,
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertIn("24 saat", second_response.context["form"].errors["email"][0])
        self.assertEqual(fake_service.send_template_email.call_count, 1)

    @patch("core.forms.get_email_service")
    def test_password_reset_applies_ip_cooldown_after_three_requests(self, mock_get_service):
        extra_users = [
            User.objects.create_user(
                username="thirduser",
                email="third@example.com",
                password="testpassword",
                is_active=True,
            ),
            User.objects.create_user(
                username="fourthuser",
                email="fourth@example.com",
                password="testpassword",
                is_active=True,
            ),
        ]
        fake_service = Mock()
        fake_service.send_template_email.return_value = {"id": "reset-id"}
        mock_get_service.return_value = fake_service

        emails = [
            self.user.email,
            self.active_user.email,
            extra_users[0].email,
            extra_users[1].email,
        ]

        responses = [
            self.client.post(reverse("password_reset"), {"email": email})
            for email in emails
        ]

        self.assertRedirects(
            responses[0],
            reverse("password_reset_done"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            responses[1],
            reverse("password_reset_done"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            responses[2],
            reverse("password_reset_done"),
            fetch_redirect_response=False,
        )
        self.assertEqual(responses[3].status_code, 200)
        self.assertIn("Bu cihazdan", responses[3].context["form"].errors["email"][0])
        self.assertEqual(fake_service.send_template_email.call_count, 3)

    def test_password_reset_confirm_redirects_to_login(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.active_user.pk))
        token = default_token_generator.make_token(self.active_user)
        confirm_url = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": token},
        )

        initial_response = self.client.get(confirm_url)
        self.assertEqual(initial_response.status_code, 302)

        response = self.client.post(
            initial_response.url,
            {
                "new_password1": "YeniGucluSifre123!",
                "new_password2": "YeniGucluSifre123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("giris"),
            fetch_redirect_response=False,
        )
        self.active_user.refresh_from_db()
        self.assertTrue(self.active_user.check_password("YeniGucluSifre123!"))

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_resend_endpoint_hides_unknown_email(self, mock_send_confirmation):
        response = self.client.post(
            reverse("dogrulama_mail_gonder"),
            {"email": "unknown@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        mock_send_confirmation.assert_not_called()

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_resend_endpoint_applies_cooldown(self, mock_send_confirmation):
        first_response = self.client.post(
            reverse("dogrulama_mail_gonder"),
            {"email": self.user.email},
        )
        second_response = self.client.post(
            reverse("dogrulama_mail_gonder"),
            {"email": self.user.email},
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        mock_send_confirmation.assert_called_once()

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_mobile_register_creates_inactive_user_and_sends_confirmation(self, mock_send_confirmation):
        response = self.client.post(
            reverse("mobile_register"),
            data=json.dumps(
                {
                    "username": "mobileuser",
                    "email": "mobile@example.com",
                    "password": "GucluSifre123!",
                    "password2": "GucluSifre123!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["code"], "email_verification_required")
        self.assertEqual(response.json()["resend_after_seconds"], 300)

        user = User.objects.get(username="mobileuser")
        self.assertFalse(user.is_active)
        email_address = EmailAddress.objects.get(user=user, email="mobile@example.com")
        self.assertTrue(email_address.primary)
        self.assertFalse(email_address.verified)
        mock_send_confirmation.assert_called_once()

    def test_mobile_auth_endpoints_allow_flutter_web_preflight(self):
        response = self.client.options(
            reverse("mobile_password_reset_request"),
            HTTP_ORIGIN="http://localhost:51002",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "http://localhost:51002",
        )
        self.assertIn("POST", response["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", response["Access-Control-Allow-Headers"])

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_mobile_register_applies_signup_rate_limit(self, mock_send_confirmation):
        # Ayni IP'den izin verilen sinir (5) kadar kayit basarili olmali.
        for i in range(5):
            response = self.client.post(
                reverse("mobile_register"),
                data=json.dumps(
                    {
                        "username": f"mobileuser{i}",
                        "email": f"mobile{i}@example.com",
                        "password": "GucluSifre123!",
                        "password2": "GucluSifre123!",
                    }
                ),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 201, response.content)

        # 6. kayit sinirin asilmasiyla 429 dönmeli.
        blocked_response = self.client.post(
            reverse("mobile_register"),
            data=json.dumps(
                {
                    "username": "mobileuser_blocked",
                    "email": "blocked@example.com",
                    "password": "GucluSifre123!",
                    "password2": "GucluSifre123!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response.json()["retry_after_seconds"], 86400)
        self.assertEqual(mock_send_confirmation.call_count, 5)

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_mobile_register_cleans_up_user_when_confirmation_fails(self, mock_send_confirmation):
        mock_send_confirmation.side_effect = Exception("mail down")

        response = self.client.post(
            reverse("mobile_register"),
            data=json.dumps(
                {
                    "username": "brokenmail",
                    "email": "brokenmail@example.com",
                    "password": "GucluSifre123!",
                    "password2": "GucluSifre123!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(User.objects.filter(username="brokenmail").exists())

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_mobile_resend_endpoint_is_enumeration_safe_and_rate_limited(self, mock_send_confirmation):
        unknown_response = self.client.post(
            reverse("mobile_resend_verification"),
            data=json.dumps({"email": "unknown@example.com"}),
            content_type="application/json",
        )
        self.assertEqual(unknown_response.status_code, 200)
        mock_send_confirmation.assert_not_called()

        cache.clear()
        first_response = self.client.post(
            reverse("mobile_resend_verification"),
            data=json.dumps({"email": self.user.email}),
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("mobile_resend_verification"),
            data=json.dumps({"email": self.user.email}),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        self.assertEqual(second_response.json()["retry_after_seconds"], 300)
        mock_send_confirmation.assert_called_once()

    @patch("core.forms.get_email_service")
    def test_mobile_password_reset_uses_custom_form_and_template(self, mock_get_service):
        fake_service = Mock()
        fake_service.send_template_email.return_value = {"id": "reset-id"}
        mock_get_service.return_value = fake_service

        response = self.client.post(
            reverse("mobile_password_reset_request"),
            data=json.dumps({"email": self.user.email}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        fake_service.send_template_email.assert_called_once()
        kwargs = fake_service.send_template_email.call_args.kwargs
        self.assertEqual(kwargs["to"], self.user.email)
        self.assertEqual(kwargs["template_name"], "emails/password_reset.html")

    def test_confirmation_link_is_invalid_after_successful_use(self):
        email_address = EmailAddress.objects.get(user=self.user, email=self.user.email)
        confirmation = EmailConfirmationHMAC.create(email_address)
        confirm_url = reverse("email_confirm_magic", args=[confirmation.key])

        first_response = self.client.post(confirm_url)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(first_response.url, reverse("anasayfa"))

        self.user.refresh_from_db()
        email_address.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(email_address.verified)
        self.assertIsNone(EmailConfirmationHMAC.from_key(confirmation.key))

        second_response = self.client.get(confirm_url)

        self.assertEqual(second_response.status_code, 200)
        self.assertContains(second_response, "bağlantı geçersizdir")
