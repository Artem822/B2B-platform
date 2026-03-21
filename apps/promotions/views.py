from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.utils import timezone

from .models import Promotion


class PromotionListView(ListView):
    """Список акций."""
    
    model = Promotion
    template_name = 'promotions/promotion_list.html'
    context_object_name = 'promotions'
    
    def get_queryset(self):
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upcoming'] = Promotion.objects.filter(
            is_active=True,
            start_date__gt=timezone.now()
        )[:3]
        return context


class PromotionDetailView(DetailView):
    """Детальная страница акции."""
    
    model = Promotion
    template_name = 'promotions/promotion_detail.html'
    context_object_name = 'promotion'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Товары акции
        context['products'] = self.object.products.filter(is_active=True)[:12]
        
        # Услуги акции
        context['services'] = self.object.services.filter(is_active=True)
        
        # Промокоды
        if self.request.user.is_authenticated:
            context['promo_codes'] = self.object.promo_codes.filter(
                is_active=True,
                end_date__gte=timezone.now()
            )
        
        return context