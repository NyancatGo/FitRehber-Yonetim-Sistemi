from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
from functools import wraps

def check_ban(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'profil') and request.user.profil.is_banned:
                from django.contrib.auth import logout
                from .views import log_ihlali
                log_ihlali(request) # Logla
                logout(request)
                # Banlı kullanıcıyı sessizce yönlendirmek yerine kilit ekranıyla korkutuyoruz
                return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def check_timeout(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profil'):
            if request.user.profil.timeout_until and request.user.profil.timeout_until > timezone.now():
                # AJAX isteği ise JSON dön
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'mesaj': 'Susturulduğunuz için bu işlemi yapamazsınız.'}, status=403)
                
                # Normal istek ise kilit ekranını göster (redirect yerine)
                return render(request, 'yetkisiz_erisim.html', {'now': timezone.now()})
        return view_func(request, *args, **kwargs)
    return _wrapped_view

