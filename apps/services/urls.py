from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.ServiceListView.as_view(), name='service_list'),
    path('technicians/', views.technician_list, name='technician_list'),
    path('request/create/', views.create_service_request, name='create_request'),
    path('request/create/<slug:service_slug>/', views.create_service_request, name='create_request_for_service'),
    path('request/quick/', views.quick_request, name='quick_request'),
    
    # Заявки пользователя
    path('my-requests/', views.request_list, name='request_list'),
    path('my-requests/<str:request_number>/', views.request_detail, name='request_detail'),
    path('my-requests/<str:request_number>/cancel/', views.request_cancel, name='request_cancel'),
    
    path('<slug:slug>/', views.ServiceDetailView.as_view(), name='service_detail'),
]