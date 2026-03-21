from django.contrib import admin
from .models import Promotion, PromoCode, Banner


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'discount_percent', 'start_date', 'end_date', 'is_active']
    list_filter = ['type', 'is_active', 'is_featured']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['products', 'categories', 'services']


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'type', 'value', 'times_used', 'is_active']
    list_filter = ['type', 'is_active']


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'is_active', 'order']
    list_filter = ['position', 'is_active']