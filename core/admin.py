from django.contrib import admin
from .models import BannedIP

@admin.register(BannedIP)
class BannedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'reason', 'created_at')
    search_fields = ('ip_address', 'reason')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
