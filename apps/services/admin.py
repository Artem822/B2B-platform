from django.contrib import admin
from .models import ServiceCategory, Service, Technician, ServiceRequest


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_active', 'is_popular']
    list_filter = ['category', 'is_active', 'is_popular']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'completed_orders', 'is_available']
    list_filter = ['is_available', 'specializations']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'service', 'user', 'status', 'urgency', 'created_at']
    list_filter = ['status', 'urgency', 'created_at']
    search_fields = ['request_number', 'user__email']