from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Главная
    path('', views.DashboardHomeView.as_view(), name='home'),
    
    # Заказы
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<str:order_number>/status/', views.order_update_status, name='order_update_status'),
    path('orders/<str:order_number>/payment/', views.order_update_payment, name='order_update_payment'),
    
    # Товары
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('products/<int:pk>/stock/', views.product_stock_update, name='product_stock_update'),
    
    # Заявки на услуги
    path('service-requests/', views.ServiceRequestListView.as_view(), name='service_request_list'),
    path('service-requests/<str:request_number>/', views.ServiceRequestDetailView.as_view(), name='service_request_detail'),
    path('service-requests/<str:request_number>/update/', views.service_request_update, name='service_request_update'),
    
    # Пользователи
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    
    # Отзывы
    path('reviews/', views.ReviewListView.as_view(), name='review_list'),
    path('reviews/<int:pk>/approve/', views.review_approve, name='review_approve'),
    path('reviews/<int:pk>/reject/', views.review_reject, name='review_reject'),
    
    # Блог
    path('posts/', views.PostListView.as_view(), name='post_list'),
    path('posts/add/', views.PostCreateView.as_view(), name='post_create'),
    path('posts/<int:pk>/edit/', views.PostUpdateView.as_view(), name='post_update'),
    path('posts/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),

    # Акции
    path('promotions/', views.PromotionListView.as_view(), name='promotion_list'),
    path('promotions/add/', views.PromotionCreateView.as_view(), name='promotion_create'),
    path('promotions/<int:pk>/edit/', views.PromotionUpdateView.as_view(), name='promotion_update'),
    path('promotions/<int:pk>/delete/', views.PromotionDeleteView.as_view(), name='promotion_delete'),
    
    # Настройки и отчёты
    path('settings/', views.settings_view, name='settings'),
    path('reports/', views.reports_view, name='reports'),
    
    # Панель мастера
    path('technician/', views.TechnicianDashboardView.as_view(), name='technician_home'),
]