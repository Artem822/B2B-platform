from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.db.models import Avg

from .models import Service, ServiceCategory, ServiceRequest, Technician, ServiceRequestHistory
from .forms import ServiceRequestForm, QuickServiceRequestForm
from apps.accounts.models import Notification


class ServiceListView(ListView):
    """Список услуг."""
    
    model = Service
    template_name = 'services/service_list.html'
    context_object_name = 'services'
    
    def get_queryset(self):
        queryset = Service.objects.filter(is_active=True).select_related('category')
        
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        context['popular_services'] = Service.objects.filter(is_active=True, is_popular=True)[:6]
        context['current_category'] = self.request.GET.get('category')
        context['technicians'] = Technician.objects.filter(
            is_available=True
        ).select_related('user')[:4]
        return context


class ServiceDetailView(DetailView):
    """Детальная страница услуги."""
    
    model = Service
    template_name = 'services/service_detail.html'
    context_object_name = 'service'
    
    def get_queryset(self):
        return Service.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Доступные мастера
        context['technicians'] = Technician.objects.filter(
            is_available=True,
            specializations=self.object.category
        ).order_by('-rating')[:3]
        
        # Похожие услуги
        context['related_services'] = Service.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(pk=self.object.pk)[:4]
        
        return context


@login_required
def create_service_request(request, service_slug=None):
    """Создание заявки на услугу."""
    
    initial = {}
    service = None
    
    if service_slug:
        service = get_object_or_404(Service, slug=service_slug, is_active=True)
        initial['service'] = service
    
    # Предзаполнение данных пользователя
    initial.update({
        'contact_name': request.user.full_name,
        'contact_phone': request.user.phone,
        'contact_email': request.user.email,
    })
    
    # Адрес по умолчанию
    default_address = request.user.addresses.filter(is_default=True).first()
    if default_address:
        initial.update({
            'address_city': default_address.city,
            'address_street': f"{default_address.street}, {default_address.building}",
        })
    
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.user = request.user
            
            # Расчёт предварительной стоимости
            selected_service = form.cleaned_data['service']
            if selected_service.pricing_type == 'fixed':
                service_request.estimated_cost = selected_service.price
            elif selected_service.pricing_type == 'hourly':
                service_request.estimated_cost = (
                    selected_service.price_per_hour * selected_service.duration_hours
                )
            
            # Наценка за срочность
            if service_request.urgency == 'urgent':
                service_request.estimated_cost *= 1.5
            elif service_request.urgency == 'emergency':
                service_request.estimated_cost *= 2
            
            service_request.save()
            
            # История
            ServiceRequestHistory.objects.create(
                request=service_request,
                new_status='pending',
                changed_by=request.user,
                comment='Заявка создана'
            )
            
            # Уведомление
            Notification.objects.create(
                user=request.user,
                type='service',
                title='Заявка создана',
                message=f'Ваша заявка #{service_request.request_number} принята в обработку.'
            )
            
            messages.success(
                request,
                f'Заявка #{service_request.request_number} успешно создана! '
                f'Мы свяжемся с вами в ближайшее время.'
            )
            return redirect('services:request_detail', request_number=service_request.request_number)
    else:
        form = ServiceRequestForm(initial=initial)
    
    return render(request, 'services/service_request_form.html', {
        'form': form,
        'service': service,
    })


@login_required
def request_list(request):
    """Список заявок пользователя."""
    requests = ServiceRequest.objects.filter(user=request.user).select_related(
        'service', 'technician__user'
    )
    
    status = request.GET.get('status')
    if status:
        requests = requests.filter(status=status)
    
    return render(request, 'services/request_list.html', {
        'requests': requests,
        'current_status': status,
    })


@login_required
def request_detail(request, request_number):
    """Детали заявки."""
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related(
            'service', 'technician__user', 'user'
        ).prefetch_related('status_history'),
        request_number=request_number,
        user=request.user
    )
    
    return render(request, 'services/request_detail.html', {
        'request': service_request,
    })


@login_required
def request_cancel(request, request_number):
    """Отмена заявки."""
    service_request = get_object_or_404(
        ServiceRequest,
        request_number=request_number,
        user=request.user
    )
    
    if not service_request.can_be_cancelled():
        messages.error(request, 'Эту заявку нельзя отменить')
        return redirect('services:request_detail', request_number=request_number)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        old_status = service_request.status
        
        if service_request.cancel(reason):
            ServiceRequestHistory.objects.create(
                request=service_request,
                old_status=old_status,
                new_status='cancelled',
                changed_by=request.user,
                comment=f'Отменена клиентом. {reason}'
            )
            
            Notification.objects.create(
                user=request.user,
                type='service',
                title='Заявка отменена',
                message=f'Заявка #{service_request.request_number} была отменена.'
            )
            
            messages.success(request, 'Заявка успешно отменена')
        else:
            messages.error(request, 'Не удалось отменить заявку')
    
    return redirect('services:request_detail', request_number=request_number)


def quick_request(request):
    """Быстрая заявка (AJAX)."""
    if request.method == 'POST':
        form = QuickServiceRequestForm(request.POST)
        if form.is_valid():
            # Если пользователь авторизован - создаём полноценную заявку
            if request.user.is_authenticated:
                from django.utils import timezone
                from datetime import timedelta, time
                
                service_request = ServiceRequest.objects.create(
                    user=request.user,
                    service=form.cleaned_data['service'],
                    title=f"Быстрая заявка: {form.cleaned_data['service'].name}",
                    description=form.cleaned_data['description'],
                    contact_name=request.user.full_name,
                    contact_phone=form.cleaned_data['phone'],
                    contact_email=request.user.email,
                    address_city='Уточнить',
                    address_street='Уточнить',
                    preferred_date=timezone.now().date() + timedelta(days=1),
                    preferred_time_from=time(9, 0),
                    preferred_time_to=time(18, 0),
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Заявка #{service_request.request_number} создана! Мы перезвоним вам.',
                    'request_number': service_request.request_number,
                })
            else:
                # Для неавторизованных - просто сохраняем контакт
                return JsonResponse({
                    'success': True,
                    'message': 'Спасибо! Мы перезвоним вам в ближайшее время.',
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            })
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})


def technician_list(request):
    """Список мастеров."""
    technicians = Technician.objects.filter(
        is_available=True,
        user__is_active=True
    ).select_related('user').prefetch_related('specializations')
    
    category = request.GET.get('category')
    if category:
        technicians = technicians.filter(specializations__slug=category)
    
    return render(request, 'services/technician_list.html', {
        'technicians': technicians,
        'categories': ServiceCategory.objects.filter(is_active=True),
    })