from apps.orders.models import Order
from apps.services.models import ServiceRequest
from apps.reviews.models import Review


def dashboard_context(request):
    """Контекст для админ-панели."""
    if not request.user.is_authenticated:
        return {}
    
    if not (request.user.is_admin() or request.user.is_manager()):
        return {}
    
    return {
        'pending_orders_count': Order.objects.filter(status='pending').count(),
        'pending_requests_count': ServiceRequest.objects.filter(status='pending').count(),
        'pending_reviews_count': Review.objects.filter(is_approved=False).count(),
    }