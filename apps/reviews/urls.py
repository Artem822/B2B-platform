from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('product/<slug:product_slug>/', views.product_reviews, name='product_reviews'),
    path('product/<slug:product_slug>/add/', views.add_review, name='add_review'),
    path('vote/<int:review_id>/', views.vote_review, name='vote_review'),
    path('service/<str:request_number>/add/', views.add_service_review, name='add_service_review'),
]