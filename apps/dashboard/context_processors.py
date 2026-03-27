from apps.orders.models import Order
from apps.services.models import ServiceRequest
from apps.reviews.models import Review
from apps.accounts.models import Notification
from .models import DashboardSettings


def dashboard_context(request):
    """Контекст для админ-панели."""
    if not request.user.is_authenticated:
        return {}

    if not (request.user.is_admin() or request.user.is_manager()):
        return {}

    # Последние уведомления для admin dropdown
    recent_notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).order_by('-created_at')[:5]

    return {
        'pending_orders_count': Order.objects.filter(status='pending').count(),
        'pending_requests_count': ServiceRequest.objects.filter(status='pending').count(),
        'pending_reviews_count': Review.objects.filter(is_approved=False).count(),
        'admin_notifications': recent_notifications,
        'admin_notifications_count': recent_notifications.count(),
    }


def site_settings_context(request):
    """Настройки сайта — доступны во всех шаблонах."""
    return {
        'site_settings': DashboardSettings.get_settings(),
    }