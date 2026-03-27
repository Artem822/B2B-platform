from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('', include('apps.products.urls')),
    path('orders/', include('apps.orders.urls')),
    path('services/', include('apps.services.urls')),
    path('blog/', include('apps.blog.urls')),
    path('promotions/', include('apps.promotions.urls')),
    path('reviews/', include('apps.reviews.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('chatbot/', include('apps.chatbot.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])