from .cart import Cart
from .models import Wishlist


def cart_context(request):
    """Добавление корзины и счётчика уведомлений в контекст."""
    cart = Cart(request)
    context = {
        'cart': cart,
        'cart_total_items': len(cart),
    }
    if request.user.is_authenticated:
        context['unread_notifications_count'] = (
            request.user.notifications.filter(is_read=False).count()
        )
        context['user_wishlist_ids'] = set(
            Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    return context