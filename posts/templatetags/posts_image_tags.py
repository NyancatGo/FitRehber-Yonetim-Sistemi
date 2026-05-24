from django import template
from django.template.defaultfilters import timesince as django_timesince
from django.utils import timezone
from datetime import datetime

from posts.image_optimization import add_local_image_dimensions, mark_local_image_loading_attributes

register = template.Library()


@register.filter(name="local_image_attrs")
def local_image_attrs(value):
    # Önce width/height ekle (CLS icin), sonra loading/decoding ekle
    with_dims = add_local_image_dimensions(value)
    return mark_local_image_loading_attributes(with_dims)


@register.filter(name="avatar_url")
def avatar_url(user):
    if not user:
        return ""

    try:
        profil = user.profil
        photo = profil.foto
    except Exception:
        return ""

    if not photo:
        return ""

    try:
        if photo.name and photo.storage.exists(photo.name):
            return photo.url
    except Exception:
        return ""

    return ""


@register.filter(name="safe_timesince")
def safe_timesince(value):
    """
    timesince filter'ı timezone-aware datetime bekler.
    Eğer datetime naive ise, timezone-aware hale getirir.
    """
    if value is None:
        return ""
    try:
        # Eğer zaten timezone-aware ise direkt kullan
        if timezone.is_aware(value):
            return django_timesince(value)
        # Naive datetime ise Europe/Istanbul timezone'u ekle
        else:
            local_tz = timezone.get_current_timezone()
            aware_value = timezone.make_aware(value, local_tz)
            return django_timesince(aware_value)
    except Exception:
        return ""


@register.filter(name="safe_image_width")
def safe_image_width(image_field, default=""):
    """
    Resim dosyası disk üzerinde yoksa FileNotFoundError yerine default döner.
    """
    try:
        if image_field and image_field.name:
            return image_field.width
    except (FileNotFoundError, OSError, Exception):
        pass
    return default


@register.filter(name="safe_image_height")
def safe_image_height(image_field, default=""):
    """
    Resim dosyası disk üzerinde yoksa FileNotFoundError yerine default döner.
    """
    try:
        if image_field and image_field.name:
            return image_field.height
    except (FileNotFoundError, OSError, Exception):
        pass
    return default
