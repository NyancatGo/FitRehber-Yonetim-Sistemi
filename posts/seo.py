import json
import re
from html import unescape
from urllib.parse import urlsplit

from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator


def site_url():
    return getattr(settings, "SITE_BASE_URL", "https://fitrehber.com.tr").rstrip("/")


def absolute_url(path_or_url):
    value = str(path_or_url or "").strip()
    if not value:
        return site_url()

    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        return value

    if not value.startswith("/"):
        value = f"/{value}"

    return f"{site_url()}{value}"


def static_absolute_url(path):
    static_url = getattr(settings, "STATIC_URL", "/static/")
    if not static_url.startswith("/"):
        static_url = f"/{static_url}"
    return absolute_url(f"{static_url.rstrip('/')}/{path.lstrip('/')}")


def clean_text(value, max_chars=None):
    text = strip_tags(str(value or ""))
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_chars:
        text = Truncator(text).chars(max_chars, truncate="...")
    return text


def content_description(icerik, max_chars=160):
    summary = getattr(icerik, "mizanpajli_ozet", None) or getattr(icerik, "yazi", "")
    description = clean_text(summary, max_chars=max_chars)
    if description:
        return description
    title = clean_text(getattr(icerik, "baslik", ""), max_chars=90)
    return clean_text(f"{title} hakkında FitRehber içeriği.", max_chars=max_chars)


def content_image_url(icerik):
    cover = getattr(icerik, "kapak_fotografi", None)
    if cover:
        return absolute_url(cover)
    return static_absolute_url("images/og-default.png")


def json_ld(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def iso_datetime(value):
    if not value:
        return None
    return value.isoformat()


def author_entity(user):
    username = getattr(user, "username", "") or "FitRehber"
    return {
        "@type": "Person",
        "name": username,
        "url": absolute_url(reverse("profil", args=[username])),
    }


def publisher_entity():
    return {
        "@type": "Organization",
        "name": getattr(settings, "SITE_NAME", "FitRehber"),
        "alternateName": getattr(settings, "SITE_ALTERNATE_NAME", "Fit Rehber"),
        "url": site_url(),
        "logo": {
            "@type": "ImageObject",
            "url": static_absolute_url("images/favicons/android-icon-192x192.png"),
        },
    }


def blog_posting_json_ld(icerik):
    url = absolute_url(reverse("detay", args=[icerik.id]))
    image = content_image_url(icerik)
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": clean_text(icerik.baslik, max_chars=110),
        "description": content_description(icerik, max_chars=220),
        "image": [image],
        "datePublished": iso_datetime(icerik.tarih),
        "dateModified": iso_datetime(icerik.tarih),
        "author": author_entity(icerik.yazar),
        "publisher": publisher_entity(),
        "url": url,
        "inLanguage": "tr-TR",
    }
    if getattr(icerik, "kategori", None):
        data["articleSection"] = icerik.kategori.isim
    return json_ld(data)


def discussion_posting_json_ld(icerik, comments=None):
    url = absolute_url(reverse("detay", args=[icerik.id]))
    data = {
        "@context": "https://schema.org",
        "@type": "DiscussionForumPosting",
        "headline": clean_text(icerik.baslik, max_chars=110),
        "text": clean_text(icerik.yazi, max_chars=5000),
        "url": url,
        "datePublished": iso_datetime(icerik.tarih),
        "dateModified": iso_datetime(icerik.tarih),
        "author": author_entity(icerik.yazar),
        "publisher": publisher_entity(),
        "image": [content_image_url(icerik)],
        "inLanguage": "tr-TR",
        "interactionStatistic": {
            "@type": "InteractionCounter",
            "interactionType": "https://schema.org/CommentAction",
            "userInteractionCount": icerik.yorumlar.count(),
        },
    }
    if getattr(icerik, "kategori", None):
        data["articleSection"] = icerik.kategori.isim

    rendered_comments = []
    if comments is not None:
        for comment in list(comments)[:10]:
            rendered_comments.append(
                {
                    "@type": "Comment",
                    "text": clean_text(comment.mesaj, max_chars=1000),
                    "datePublished": iso_datetime(comment.tarih),
                    "author": author_entity(comment.yazar),
                }
            )
    if rendered_comments:
        data["comment"] = rendered_comments

    return json_ld(data)


def breadcrumb_json_ld(breadcrumbs: list[dict]) -> str:
    """
    BreadcrumbList structured data oluşturur.

    Args:
        breadcrumbs: [{'name': 'Ana Sayfa', 'url': '/'},
                     {'name': 'Forum', 'url': '/forum/'},
                     {'name': 'İçerik Başlığı', 'url': '/detay/123/'}]
    """
    items = []
    for i, crumb in enumerate(breadcrumbs, 1):
        item = {
            "@type": "ListItem",
            "position": i,
            "name": crumb['name'],
        }
        if crumb.get('url'):
            item['item'] = absolute_url(crumb['url'])
        items.append(item)

    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }
    return json_ld(data)
