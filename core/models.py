from django.db import models
from django.utils import timezone

class BannedIP(models.Model):
    """
    Sınırsız (kalıcı) ban giyen IP adreslerinin tutulduğu model.
    RateLimitMiddleware sadece okur; kayıtlar admin tarafından manuel yönetilir.
    """
    ip_address = models.GenericIPAddressField(unique=True, verbose_name="Yasaklı IP Adresi")
    reason = models.CharField(max_length=255, blank=True, null=True, verbose_name="Yasaklanma Nedeni")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yasaklanma Tarihi")

    class Meta:
        verbose_name = "Yasaklı IP"
        verbose_name_plural = "Yasaklı IP'ler"
        db_table = 'yasakli_ipler'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ip_address} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
