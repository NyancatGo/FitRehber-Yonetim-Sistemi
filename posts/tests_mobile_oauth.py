from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import MobileOAuthCode


VALID_STATE = 'a' * 43
VALID_CHALLENGE = 'b' * 43


class MobileOAuthStartTests(TestCase):
    def test_rejects_missing_or_invalid_params(self):
        response = self.client.get(reverse('mobile_google_start'))

        self.assertEqual(response.status_code, 400)

        response = self.client.get(
            reverse('mobile_google_start'),
            {'state': VALID_STATE, 'code_challenge': 'bad'},
        )

        self.assertEqual(response.status_code, 400)

    def test_redirects_to_google_login_with_mobile_callback_next(self):
        response = self.client.get(
            reverse('mobile_google_start'),
            {'state': VALID_STATE, 'code_challenge': VALID_CHALLENGE},
        )

        self.assertEqual(response.status_code, 302)
        location = response['Location']
        self.assertIn('/accounts/google/login/', location)

        query = parse_qs(urlparse(location).query)
        self.assertEqual(query['process'], ['login'])
        next_url = query['next'][0]
        self.assertTrue(next_url.startswith(reverse('mobile_auth_callback')))
        next_query = parse_qs(urlparse(next_url).query)
        self.assertEqual(next_query['state'], [VALID_STATE])
        self.assertEqual(next_query['code_challenge'], [VALID_CHALLENGE])

    def test_start_saves_params_to_session(self):
        """mobile_google_start çağrıldığında state ve code_challenge session'a yazılır."""
        self.client.get(
            reverse('mobile_google_start'),
            {'state': VALID_STATE, 'code_challenge': VALID_CHALLENGE},
        )

        session = self.client.session
        self.assertEqual(session.get('mobile_oauth_state'), VALID_STATE)
        self.assertEqual(session.get('mobile_oauth_code_challenge'), VALID_CHALLENGE)


class MobileOAuthCallbackTests(TestCase):
    def test_authenticated_callback_creates_code_and_redirects_to_app(self):
        """GET parametreleriyle çağrıldığında (geriye uyumluluk) başarıyla çalışır."""
        user = User.objects.create_user(username='mobile-user', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(
            reverse('mobile_auth_callback'),
            {'state': VALID_STATE, 'code_challenge': VALID_CHALLENGE},
        )

        self.assertEqual(response.status_code, 200)
        callback_url = response.context['callback_url']
        callback = urlparse(callback_url)
        self.assertEqual(callback.scheme, 'fitrehber')
        self.assertEqual(callback.netloc, 'oauth')
        self.assertEqual(callback.path, '/callback')

        query = parse_qs(callback.query)
        self.assertEqual(query['state'], [VALID_STATE])
        oauth_code = MobileOAuthCode.objects.get(code=query['code'][0])
        self.assertEqual(oauth_code.user, user)
        self.assertEqual(oauth_code.state, VALID_STATE)
        self.assertEqual(oauth_code.code_challenge, VALID_CHALLENGE)

    def test_authenticated_callback_rejects_invalid_params(self):
        user = User.objects.create_user(username='mobile-user', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(
            reverse('mobile_auth_callback'),
            {'state': 'bad', 'code_challenge': VALID_CHALLENGE},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MobileOAuthCode.objects.exists())


class MobileOAuthSessionTests(TestCase):
    """Session tabanlı PKCE akışını doğrulayan testler."""

    def test_callback_reads_from_session_without_get_params(self):
        """Session'da state/challenge varsa GET parametreleri olmadan bile çalışır.
        Bu, allauth'un query string'i sildiği gerçek senaryoyu simüle eder."""
        user = User.objects.create_user(username='session-user', password='pass12345')
        self.client.force_login(user)

        # Session'a el ile değer yaz (mobile_google_start'ın yapacağı iş)
        session = self.client.session
        session['mobile_oauth_state'] = VALID_STATE
        session['mobile_oauth_code_challenge'] = VALID_CHALLENGE
        session.save()

        # GET parametresi OLMADAN callback'i çağır
        response = self.client.get(reverse('mobile_auth_callback'))

        self.assertEqual(response.status_code, 200)
        callback_url = response.context['callback_url']
        callback = urlparse(callback_url)
        self.assertEqual(callback.scheme, 'fitrehber')
        self.assertEqual(callback.netloc, 'oauth')
        self.assertEqual(callback.path, '/callback')

        query = parse_qs(callback.query)
        self.assertEqual(query['state'], [VALID_STATE])
        oauth_code = MobileOAuthCode.objects.get(code=query['code'][0])
        self.assertEqual(oauth_code.user, user)
        self.assertEqual(oauth_code.state, VALID_STATE)
        self.assertEqual(oauth_code.code_challenge, VALID_CHALLENGE)

        # Session temizlenmiş olmalı
        session = self.client.session
        self.assertNotIn('mobile_oauth_state', session)
        self.assertNotIn('mobile_oauth_code_challenge', session)

    def test_end_to_end_start_then_callback_without_query_string(self):
        """Tam akış: start → allauth (query string kaybolur) → callback.
        Session sayesinde callback parametreleri korur."""
        user = User.objects.create_user(username='e2e-user', password='pass12345')

        # 1) start çağır — session'a yazar
        self.client.get(
            reverse('mobile_google_start'),
            {'state': VALID_STATE, 'code_challenge': VALID_CHALLENGE},
        )

        # 2) Allauth sürecini simüle et: kullanıcı giriş yapar
        self.client.force_login(user)

        # 3) Callback'e GET parametresi OLMADAN git (allauth query string'i sildi)
        response = self.client.get(reverse('mobile_auth_callback'))

        self.assertEqual(response.status_code, 200)
        callback_url = response.context['callback_url']
        callback = urlparse(callback_url)
        self.assertEqual(callback.scheme, 'fitrehber')

        query = parse_qs(callback.query)
        self.assertEqual(query['state'], [VALID_STATE])
        oauth_code = MobileOAuthCode.objects.get(code=query['code'][0])
        self.assertEqual(oauth_code.user, user)

    def test_callback_rejects_invalid_session_params(self):
        """Session'da geçersiz state varsa 400 döner."""
        user = User.objects.create_user(username='invalid-sess', password='pass12345')
        self.client.force_login(user)

        session = self.client.session
        session['mobile_oauth_state'] = 'bad'  # Regex'e uymayan kısa değer
        session['mobile_oauth_code_challenge'] = VALID_CHALLENGE
        session.save()

        response = self.client.get(reverse('mobile_auth_callback'))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MobileOAuthCode.objects.exists())

    def test_callback_no_session_no_get_returns_400(self):
        """Ne session ne GET parametresi varsa 400 döner."""
        user = User.objects.create_user(username='empty-user', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('mobile_auth_callback'))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MobileOAuthCode.objects.exists())


class MobileOAuthWebRedirectTests(TestCase):
    """Flutter web hibrit akışı: redirect_uri parametresiyle çalışan testler."""

    WEB_REDIRECT = 'http://localhost:58442/'

    def test_start_accepts_and_saves_localhost_redirect_uri(self):
        """localhost redirect_uri start'ta kabul edilir ve session'a yazılır."""
        response = self.client.get(
            reverse('mobile_google_start'),
            {
                'state': VALID_STATE,
                'code_challenge': VALID_CHALLENGE,
                'redirect_uri': self.WEB_REDIRECT,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session.get('mobile_oauth_redirect_uri'),
            self.WEB_REDIRECT,
        )
        next_url = parse_qs(urlparse(response['Location']).query)['next'][0]
        next_query = parse_qs(urlparse(next_url).query)
        self.assertEqual(next_query['redirect_uri'], [self.WEB_REDIRECT])

    def test_start_rejects_untrusted_redirect_uri(self):
        """Whitelist dışı bir origin start'ta 400 ile reddedilir (open redirect)."""
        response = self.client.get(
            reverse('mobile_google_start'),
            {
                'state': VALID_STATE,
                'code_challenge': VALID_CHALLENGE,
                'redirect_uri': 'https://evil.example.com/steal',
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_start_without_redirect_uri_defaults_to_native(self):
        """redirect_uri verilmezse native deep link varsayılır (eski sürüm uyumu)."""
        self.client.get(
            reverse('mobile_google_start'),
            {'state': VALID_STATE, 'code_challenge': VALID_CHALLENGE},
        )

        self.assertEqual(
            self.client.session.get('mobile_oauth_redirect_uri'),
            'fitrehber://oauth/callback',
        )

    def test_callback_with_web_redirect_uri_does_302_to_app(self):
        """Web redirect_uri varsa callback HTML değil, doğrudan 302 döner."""
        user = User.objects.create_user(username='web-user', password='pass12345')
        self.client.force_login(user)

        session = self.client.session
        session['mobile_oauth_state'] = VALID_STATE
        session['mobile_oauth_code_challenge'] = VALID_CHALLENGE
        session['mobile_oauth_redirect_uri'] = self.WEB_REDIRECT
        session.save()

        response = self.client.get(reverse('mobile_auth_callback'))

        self.assertEqual(response.status_code, 302)
        location = urlparse(response['Location'])
        self.assertEqual(location.scheme, 'http')
        self.assertEqual(location.netloc, 'localhost:58442')

        query = parse_qs(location.query)
        self.assertEqual(query['state'], [VALID_STATE])
        oauth_code = MobileOAuthCode.objects.get(code=query['code'][0])
        self.assertEqual(oauth_code.user, user)
        self.assertEqual(oauth_code.state, VALID_STATE)

    def test_callback_rejects_untrusted_redirect_uri_from_get(self):
        """GET üzerinden gelen güvenilmez redirect_uri callback'te 400 verir."""
        user = User.objects.create_user(username='web-evil', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(
            reverse('mobile_auth_callback'),
            {
                'state': VALID_STATE,
                'code_challenge': VALID_CHALLENGE,
                'redirect_uri': 'https://evil.example.com/',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MobileOAuthCode.objects.exists())

    @override_settings(MOBILE_OAUTH_WEB_ORIGINS=('https://app.fitrehber.com.tr',))
    def test_callback_accepts_whitelisted_production_origin(self):
        """settings.MOBILE_OAUTH_WEB_ORIGINS'teki prod origin kabul edilir."""
        user = User.objects.create_user(username='web-prod', password='pass12345')
        self.client.force_login(user)

        session = self.client.session
        session['mobile_oauth_state'] = VALID_STATE
        session['mobile_oauth_code_challenge'] = VALID_CHALLENGE
        session['mobile_oauth_redirect_uri'] = 'https://app.fitrehber.com.tr/'
        session.save()

        response = self.client.get(reverse('mobile_auth_callback'))

        self.assertEqual(response.status_code, 302)
        location = urlparse(response['Location'])
        self.assertEqual(location.netloc, 'app.fitrehber.com.tr')

