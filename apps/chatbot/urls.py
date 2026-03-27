from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('send/', views.chat_send, name='send'),
    path('clear/', views.chat_clear, name='clear'),
    path('history/', views.chat_history, name='history'),
]
