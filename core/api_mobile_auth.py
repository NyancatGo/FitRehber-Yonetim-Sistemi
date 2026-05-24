import json
import logging
from functools import wraps

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.forms import CustomPasswordResetForm
from core.security_utils import get_client_ip
from posts.forms import KullaniciKayitFormu

logger = logging.getLogger(__name__)

SIGNUP_RATE_LIMIT_SECONDS = 86400
# Ayni IP'den 24 saatte izin verilen azami kayit sayisi. Tek hesap (1)
# cok katiydi — ayni ev/ofis/okul agindaki birden cok kisi kayit olamiyordu.
SIGNUP_RATE_LIMIT_MAX = 5
VERIFICATION_RESEND_COOLDOWN_SECONDS = 300

_ALLOWED_CORS_ORIGINS = {
    "https://fitrehber.com.tr",
    "https://www.fitrehber.com.tr",
}
_ALLOWED_DEV_ORIGIN_PREFIXES = (
    "http://localhost:",
    "https://localhost:",
    "http://127.0.0.1:",
    "https://127.0.0.1:",
)


def _is_allowed_origin(origin):
    return (
        origin in _ALLOWED_CORS_ORIGINS
        or origin.startswith(_ALLOWED_DEV_ORIGIN_PREFIXES)
    )


def _add_cors_headers(request, response):
    origin = request.headers.get("Origin")
    if not origin or not _is_allowed_origin(origin):
        return response

    response["Access-Control-Allow-Origin"] = origin
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    response["Access-Control-Max-Age"] = "86400"

    vary = response.get("Vary")
    if vary:
        vary_values = {value.strip().lower() for value in vary.split(",")}
        if "origin" not in vary_values:
            response["Vary"] = f"{vary}, Origin"
    else:
        response["Vary"] = "Origin"

    return response


def mobile_auth_cors(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.method == "OPTIONS":
            return _add_cors_headers(request, JsonResponse({}, status=204))

        return _add_cors_headers(request, view_func(request, *args, **kwargs))

    return wrapped


def _json_error(message, status=400, **extra):
    payload = {"hata": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _parse_json_body(request):
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None, _json_error("Geçersiz JSON.", status=400)

    if not isinstance(data, dict):
        return None, _json_error("Geçersiz JSON gövdesi.", status=400)

    return data, None


def _form_errors(form):
    return {
        field: [str(error) for error in errors]
        for field, errors in form.errors.items()
    }


def _first_form_error(form, default="Bilgilerini kontrol et."):
    for errors in form.errors.values():
        if errors:
            return str(errors[0])
    return default


def _signup_limit_key(request):
    return f"signup_limit_{get_client_ip(request)}"


def _resend_limit_keys(request, email):
    normalized_email = email.strip().lower()
    return (
        f"resend_limit_ip_{get_client_ip(request)}",
        f"resend_limit_email_{normalized_email}",
    )


@csrf_exempt
@mobile_auth_cors
def mobile_register(request):
    if request.method != "POST":
        return _json_error("Geçersiz method.", status=405)

    data, error_response = _parse_json_body(request)
    if error_response:
        return error_response

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    password2 = data.get("password2") or ""

    form = KullaniciKayitFormu(
        {
            "username": username,
            "email": email,
            "password1": password,
            "password2": password2,
        }
    )
    if not form.is_valid():
        return _json_error(
            _first_form_error(form),
            status=400,
            errors=_form_errors(form),
        )

    signup_limit_key = _signup_limit_key(request)
    # Sayac mantigi: ayni IP'den 24 saatte SIGNUP_RATE_LIMIT_MAX kayda izin var.
    signup_count = cache.get(signup_limit_key, 0)
    if not isinstance(signup_count, int):
        # Eski binary deger (True) ile geriye uyumluluk.
        signup_count = 1 if signup_count else 0
    if signup_count >= SIGNUP_RATE_LIMIT_MAX:
        return _json_error(
            "Bu cihazdan son 24 saat içinde çok fazla hesap oluşturuldu. "
            "Lütfen daha sonra tekrar deneyin.",
            status=429,
            retry_after_seconds=SIGNUP_RATE_LIMIT_SECONDS,
        )

    with transaction.atomic():
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        email_address, _ = EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"verified": False, "primary": True},
        )

    try:
        email_address.send_confirmation(request, signup=True)
    except Exception as exc:
        logger.error("Mobil kayıt doğrulama e-postası gönderilemedi: %s", exc)
        user.delete()
        return _json_error(
            "Doğrulama e-postası şu anda gönderilemedi. Lütfen biraz sonra tekrar deneyin.",
            status=500,
        )

    cache.set(
        signup_limit_key,
        signup_count + 1,
        timeout=SIGNUP_RATE_LIMIT_SECONDS,
    )
    return JsonResponse(
        {
            "code": "email_verification_required",
            "email": user.email,
            "message": "Doğrulama bağlantısı e-posta adresinize gönderildi.",
            "resend_after_seconds": VERIFICATION_RESEND_COOLDOWN_SECONDS,
        },
        status=201,
    )


@csrf_exempt
@mobile_auth_cors
def mobile_resend_verification(request):
    if request.method != "POST":
        return _json_error("Geçersiz method.", status=405)

    data, error_response = _parse_json_body(request)
    if error_response:
        return error_response

    email = (data.get("email") or "").strip()
    if not email:
        return _json_error("E-posta adresi zorunludur.", status=400)

    ip_limit_key, email_limit_key = _resend_limit_keys(request, email)
    if cache.get(ip_limit_key) or cache.get(email_limit_key):
        return _json_error(
            "Çok sık deniyorsunuz. Lütfen birkaç dakika bekleyin.",
            status=429,
            retry_after_seconds=VERIFICATION_RESEND_COOLDOWN_SECONDS,
        )

    generic_message = (
        "Eğer e-posta adresi sistemde kayıtlıysa ve henüz doğrulanmamışsa, "
        "doğrulama bağlantısı gönderildi."
    )

    try:
        # .get() yerine .filter().first(): ayni e-postaya sahip birden cok
        # eski kayit olsa bile MultipleObjectsReturned ile patlamaz.
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            email_address = EmailAddress.objects.filter(
                user=user,
                email__iexact=email,
            ).first()
            if (
                user.is_active is False
                and email_address
                and not email_address.verified
            ):
                email_address.send_confirmation(request, signup=False)
    except Exception as exc:
        logger.error("Mobil doğrulama e-postası tekrar gönderilemedi: %s", exc)
        return _json_error("Bir hata oluştu.", status=500)

    cache.set(ip_limit_key, True, timeout=VERIFICATION_RESEND_COOLDOWN_SECONDS)
    cache.set(email_limit_key, True, timeout=VERIFICATION_RESEND_COOLDOWN_SECONDS)
    return JsonResponse({"message": generic_message})


@csrf_exempt
@mobile_auth_cors
def mobile_password_reset_request(request):
    if request.method != "POST":
        return _json_error("Geçersiz method.", status=405)

    data, error_response = _parse_json_body(request)
    if error_response:
        return error_response

    email = (data.get("email") or "").strip()
    if not email:
        return _json_error("E-posta adresi zorunludur.", status=400)

    form = CustomPasswordResetForm(data={"email": email}, request=request)
    if not form.is_valid():
        message = _first_form_error(form)
        status_code = 429 if "24 saat" in message or "çok fazla" in message.lower() else 400
        return _json_error(
            message,
            status=status_code,
            errors=_form_errors(form),
        )

    form.save(request=request, use_https=request.is_secure())
    return JsonResponse(
        {
            "message": (
                "Eğer e-posta adresi sistemde kayıtlıysa, şifre sıfırlama "
                "bağlantısı gönderildi."
            )
        }
    )
