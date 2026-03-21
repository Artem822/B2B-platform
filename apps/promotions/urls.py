from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    path('', views.PromotionListView.as_view(), name='promotion_list'),
    path('<slug:slug>/', views.PromotionDetailView.as_view(), name='promotion_detail'),
]