from .models import Promotion, Banner


def active_promotions(request):
    """Добавление активных акций в контекст."""
    from django.utils import timezone
    
    now = timezone.now()
    
    return {
        'active_promotions': Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )[:3],
        'home_banners': Banner.objects.filter(
            is_active=True,
            position='home_top'
        ).order_by('order')[:5],
    }