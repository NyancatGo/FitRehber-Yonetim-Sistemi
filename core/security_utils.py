from __future__ import annotations

import ipaddress
from typing import Optional

from django.conf import settings


def _parse_ip(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def get_client_ip(request) -> str:
    """
    Güvenli istemci IP tespiti.

    - Varsayılan olarak yalnızca REMOTE_ADDR kullanılır.
    - TRUST_PROXY_HEADERS=True ise ve istek bir trusted proxy'den geliyorsa
      X-Forwarded-For zincirindeki ilk geçerli IP istemci IP'si kabul edilir.
    """
    remote_addr = _parse_ip(request.META.get('REMOTE_ADDR')) or '127.0.0.1'

    trust_proxy_headers = getattr(settings, 'TRUST_PROXY_HEADERS', False)
    trusted_proxy_ips = set(getattr(settings, 'TRUSTED_PROXY_IPS', []))

    if not trust_proxy_headers:
        return remote_addr

    if trusted_proxy_ips and remote_addr not in trusted_proxy_ips:
        return remote_addr

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if not x_forwarded_for:
        return remote_addr

    for part in [p.strip() for p in x_forwarded_for.split(',') if p.strip()]:
        parsed = _parse_ip(part)
        if parsed:
            return parsed

    return remote_addr

