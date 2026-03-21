from .cart import Cart


def cart_context(request):
    """Добавление корзины в контекст."""
    cart = Cart(request)
    return {
        'cart': cart,
        'cart_total_items': len(cart),
    }