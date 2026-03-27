from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Корзина
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    
    # Промокод
    path('cart/apply-promo/', views.apply_promo, name='apply_promo'),

    # Оформление заказа
    path('checkout/', views.checkout, name='checkout'),
    
    # Заказы
    path('', views.order_list, name='order_list'),
    path('<str:order_number>/', views.order_detail, name='order_detail'),
    path('<str:order_number>/cancel/', views.order_cancel, name='order_cancel'),
    path('<str:order_number>/repeat/', views.order_repeat, name='order_repeat'),
]