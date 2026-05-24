from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from .models import Icerik, Kategori, GunlukAktivite
from django.urls import reverse
from core.security_utils import get_client_ip


def _rate_limit_cache_key(*parts):
    prefix = getattr(settings, "RATELIMIT_CACHE_PREFIX", "rate_limit_v2")
    clean_parts = [str(part).strip(":") for part in parts]
    return ":".join([prefix, *clean_parts])


def _request_actor_key(request):
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return f"user:{user.pk}"
    return f"ip:{get_client_ip(request)}"


def _increment_counter(key, window):
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        return 1

@login_required
@csrf_protect
def aktivite_kaydet(request):
    # ... existing code ...
    if request.method == 'POST':
        # --- RATE LIMITING (30 saniye) ---
        cache_key = f"aktivite_ping:{request.user.id}"
        if cache.get(cache_key):
            return JsonResponse({'status': 'throttled'}, status=429)
        cache.set(cache_key, True, 30)
        
        today = timezone.now().date()
        aktivite, created = GunlukAktivite.objects.get_or_create(
            user=request.user,
            tarih=today
        )
        
        aktivite.sure_dk += 1
        aktivite.save()
        
        return JsonResponse({'status': 'success', 'yeni_sure': aktivite.sure_dk})
    return JsonResponse({'status': 'error'}, status=400)

def canli_arama(request):
    """Anlık arama sonuçlarını JSON olarak döner."""
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 1:
        return JsonResponse({'results': []})

    limit = getattr(settings, "RATELIMIT_SEARCH_MAX", 20)
    window = getattr(settings, "RATELIMIT_SEARCH_WINDOW", 10)
    cache_key = _rate_limit_cache_key("search", _request_actor_key(request))
    if _increment_counter(cache_key, window) > limit:
        return JsonResponse({'results': [], 'throttled': True})

    # Başlıkta veya yazıda ara, ilk 5 sonucu getir
    sonuclar = Icerik.objects.filter(
        Q(baslik__icontains=query) | Q(yazi__icontains=query)
    ).select_related('kategori').order_by('-tarih')[:7]

    data = []
    for s in sonuclar:
        data.append({
            'id': s.id,
            'baslik': s.baslik,
            'url': reverse('detay', args=[s.id]),
            'tur': s.get_tur_display(),
            'tur_raw': s.tur,
            'kategori': s.kategori.isim if s.kategori else None
        })

    return JsonResponse({'results': data})
