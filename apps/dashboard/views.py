from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal

from .mixins import AdminRequiredMixin, TechnicianRequiredMixin
from .models import DashboardSettings, ActivityLog
from apps.accounts.models import User, Notification
from apps.products.models import Product, Category, Brand
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.services.models import ServiceRequest, Service, Technician, ServiceRequestHistory
from apps.blog.models import Post
from apps.promotions.models import Promotion, PromoCode
from apps.reviews.models import Review, ServiceReview


# ============ ГЛАВНАЯ ПАНЕЛЬ ============

class DashboardHomeView(AdminRequiredMixin, ListView):
    """Главная страница админ-панели."""
    
    template_name = 'dashboard/home.html'
    context_object_name = 'recent_orders'
    
    def get_queryset(self):
        return Order.objects.select_related('user').order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Статистика заказов
        context['orders_today'] = Order.objects.filter(
            created_at__date=today
        ).count()
        context['orders_month'] = Order.objects.filter(
            created_at__date__gte=month_start
        ).count()
        context['orders_pending'] = Order.objects.filter(
            status='pending'
        ).count()
        
        # Выручка
        context['revenue_today'] = Order.objects.filter(
            created_at__date=today,
            payment_status='paid'
        ).aggregate(total=Sum('total'))['total'] or 0
        
        context['revenue_month'] = Order.objects.filter(
            created_at__date__gte=month_start,
            payment_status='paid'
        ).aggregate(total=Sum('total'))['total'] or 0
        
        # Заявки на услуги
        context['service_requests_pending'] = ServiceRequest.objects.filter(
            status='pending'
        ).count()
        context['service_requests_today'] = ServiceRequest.objects.filter(
            created_at__date=today
        ).count()
        
        # Пользователи
        context['users_total'] = User.objects.filter(role='client').count()
        context['users_new_month'] = User.objects.filter(
            created_at__date__gte=month_start,
            role='client'
        ).count()
        
        # Товары
        context['products_total'] = Product.objects.filter(is_active=True).count()
        context['products_low_stock'] = Product.objects.filter(
            is_active=True,
            stock__lt=5
        ).count()
        
        # Последние заявки
        context['recent_service_requests'] = ServiceRequest.objects.select_related(
            'user', 'service'
        ).order_by('-created_at')[:5]
        
        # Отзывы на модерации
        context['pending_reviews'] = Review.objects.filter(is_approved=False).count()
        
        # График продаж за последние 7 дней
        week_ago = today - timedelta(days=7)
        sales_data = Order.objects.filter(
            created_at__date__gte=week_ago,
            payment_status='paid'
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Sum('total'),
            count=Count('id')
        ).order_by('date')
        
        context['sales_chart_labels'] = [
            item['date'].strftime('%d.%m') for item in sales_data
        ]
        context['sales_chart_data'] = [
            float(item['total']) for item in sales_data
        ]
        
        return context


# ============ ЗАКАЗЫ ============

class OrderListView(AdminRequiredMixin, ListView):
    """Список заказов."""
    
    model = Order
    template_name = 'dashboard/orders/list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Order.objects.select_related('user').order_by('-created_at')
        
        # Фильтры
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        payment = self.request.GET.get('payment')
        if payment:
            queryset = queryset.filter(payment_status=payment)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                order_number__icontains=search
            ) | queryset.filter(
                user__email__icontains=search
            )
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Order.STATUS_CHOICES
        context['payment_choices'] = Order.PAYMENT_STATUS_CHOICES
        return context


class OrderDetailView(AdminRequiredMixin, DetailView):
    """Детали заказа."""
    
    model = Order
    template_name = 'dashboard/orders/detail.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'
    
    def get_queryset(self):
        return Order.objects.select_related('user').prefetch_related(
            'items__product', 'status_history__changed_by'
        )


@login_required
def order_update_status(request, order_number):
    """Обновление статуса заказа."""
    if not (request.user.is_admin() or request.user.is_manager()):
        messages.error(request, 'Нет доступа')
        return redirect('dashboard:home')
    
    order = get_object_or_404(Order, order_number=order_number)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        comment = request.POST.get('comment', '')
        
        if new_status and new_status != order.status:
            old_status = order.status
            
            # Обработка отмены
            if new_status == 'cancelled':
                order.cancel(comment)
            else:
                order.status = new_status
                
                # Устанавливаем даты
                if new_status == 'confirmed' and not order.confirmed_at:
                    order.confirmed_at = timezone.now()
                    order.confirm()
                elif new_status == 'shipped' and not order.shipped_at:
                    order.shipped_at = timezone.now()
                elif new_status == 'delivered' and not order.delivered_at:
                    order.delivered_at = timezone.now()
                
                order.save()
            
            # История
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                comment=comment
            )
            
            # Уведомление клиенту
            status_display = dict(Order.STATUS_CHOICES).get(new_status)
            Notification.objects.create(
                user=order.user,
                type='order',
                title=f'Статус заказа изменён',
                message=f'Статус заказа #{order.order_number} изменён на: {status_display}'
            )
            
            # Лог активности
            ActivityLog.objects.create(
                user=request.user,
                action='update',
                model_name='Order',
                object_id=order.id,
                object_repr=str(order),
                details=f'Статус изменён: {old_status} -> {new_status}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Статус заказа изменён на: {status_display}')
    
    return redirect('dashboard:order_detail', order_number=order_number)


@login_required
def order_update_payment(request, order_number):
    """Обновление статуса оплаты."""
    if not (request.user.is_admin() or request.user.is_manager()):
        messages.error(request, 'Нет доступа')
        return redirect('dashboard:home')
    
    order = get_object_or_404(Order, order_number=order_number)
    
    if request.method == 'POST':
        new_status = request.POST.get('payment_status')
        
        if new_status and new_status != order.payment_status:
            order.payment_status = new_status
            order.save()
            
            status_display = dict(Order.PAYMENT_STATUS_CHOICES).get(new_status)
            messages.success(request, f'Статус оплаты изменён на: {status_display}')
    
    return redirect('dashboard:order_detail', order_number=order_number)


# ============ ТОВАРЫ ============

class ProductListView(AdminRequiredMixin, ListView):
    """Список товаров."""
    
    model = Product
    template_name = 'dashboard/products/list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'brand').order_by('-created_at')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search) | queryset.filter(sku__icontains=search)
        
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        stock = self.request.GET.get('stock')
        if stock == 'low':
            queryset = queryset.filter(stock__lt=5)
        elif stock == 'out':
            queryset = queryset.filter(stock=0)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        return context


class ProductCreateView(AdminRequiredMixin, CreateView):
    """Создание товара."""
    
    model = Product
    template_name = 'dashboard/products/form.html'
    fields = [
        'name', 'sku', 'category', 'brand', 'description', 'short_description',
        'price', 'old_price', 'stock', 'condition', 'warranty_months',
        'weight', 'main_image', 'is_active', 'is_featured'
    ]
    success_url = reverse_lazy('dashboard:product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавить товар'
        context['categories'] = Category.objects.filter(is_active=True)
        context['brands'] = Brand.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        ActivityLog.objects.create(
            user=self.request.user,
            action='create',
            model_name='Product',
            object_id=self.object.id,
            object_repr=str(self.object),
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        messages.success(self.request, 'Товар успешно добавлен')
        return response


class ProductUpdateView(AdminRequiredMixin, UpdateView):
    """Редактирование товара."""
    
    model = Product
    template_name = 'dashboard/products/form.html'
    fields = [
        'name', 'sku', 'category', 'brand', 'description', 'short_description',
        'price', 'old_price', 'stock', 'condition', 'warranty_months',
        'weight', 'main_image', 'is_active', 'is_featured'
    ]
    success_url = reverse_lazy('dashboard:product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактировать товар'
        context['categories'] = Category.objects.filter(is_active=True)
        context['brands'] = Brand.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        ActivityLog.objects.create(
            user=self.request.user,
            action='update',
            model_name='Product',
            object_id=self.object.id,
            object_repr=str(self.object),
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        messages.success(self.request, 'Товар успешно обновлён')
        return response


class ProductDeleteView(AdminRequiredMixin, DeleteView):
    """Удаление товара."""
    
    model = Product
    template_name = 'dashboard/products/confirm_delete.html'
    success_url = reverse_lazy('dashboard:product_list')
    
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Product',
            object_repr=str(obj),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, 'Товар удалён')
        return super().delete(request, *args, **kwargs)


@login_required
def product_stock_update(request, pk):
    """Быстрое обновление остатков."""
    if not (request.user.is_admin() or request.user.is_manager()):
        return JsonResponse({'success': False, 'message': 'Нет доступа'})
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        try:
            new_stock = int(request.POST.get('stock', 0))
            product.stock = max(0, new_stock)
            product.save()
            return JsonResponse({
                'success': True,
                'stock': product.stock,
                'available': product.available_stock
            })
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Неверное значение'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})


# ============ ЗАЯВКИ НА УСЛУГИ ============

class ServiceRequestListView(AdminRequiredMixin, ListView):
    """Список заявок на услуги."""
    
    model = ServiceRequest
    template_name = 'dashboard/services/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ServiceRequest.objects.select_related(
            'user', 'service', 'technician__user'
        ).order_by('-created_at')
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        urgency = self.request.GET.get('urgency')
        if urgency:
            queryset = queryset.filter(urgency=urgency)
        
        technician = self.request.GET.get('technician')
        if technician:
            if technician == 'none':
                queryset = queryset.filter(technician__isnull=True)
            else:
                queryset = queryset.filter(technician_id=technician)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ServiceRequest.STATUS_CHOICES
        context['urgency_choices'] = ServiceRequest.URGENCY_CHOICES
        context['technicians'] = Technician.objects.filter(is_available=True)
        return context


class ServiceRequestDetailView(AdminRequiredMixin, DetailView):
    """Детали заявки."""
    
    model = ServiceRequest
    template_name = 'dashboard/services/request_detail.html'
    context_object_name = 'request'
    slug_field = 'request_number'
    slug_url_kwarg = 'request_number'
    
    def get_queryset(self):
        return ServiceRequest.objects.select_related(
            'user', 'service', 'technician__user'
        ).prefetch_related('status_history__changed_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['technicians'] = Technician.objects.filter(is_available=True)
        context['status_choices'] = ServiceRequest.STATUS_CHOICES
        return context


@login_required
def service_request_update(request, request_number):
    """Обновление заявки на услугу."""
    if not (request.user.is_admin() or request.user.is_manager()):
        messages.error(request, 'Нет доступа')
        return redirect('dashboard:home')
    
    service_request = get_object_or_404(ServiceRequest, request_number=request_number)
    
    if request.method == 'POST':
        old_status = service_request.status
        
        # Обновление статуса
        new_status = request.POST.get('status')
        if new_status and new_status != old_status:
            service_request.status = new_status
            
            if new_status == 'completed':
                service_request.completed_at = timezone.now()
                service_request.final_cost = Decimal(request.POST.get('final_cost', 0))
                service_request.hours_worked = Decimal(request.POST.get('hours_worked', 0))
            
            if new_status == 'cancelled':
                service_request.cancelled_at = timezone.now()
        
        # Назначение мастера
        technician_id = request.POST.get('technician')
        if technician_id:
            service_request.technician_id = technician_id
            if service_request.status == 'confirmed':
                service_request.status = 'assigned'
        
        # Дата и время
        scheduled_date = request.POST.get('scheduled_date')
        scheduled_time = request.POST.get('scheduled_time')
        if scheduled_date:
            service_request.scheduled_date = scheduled_date
        if scheduled_time:
            service_request.scheduled_time = scheduled_time
        
        # Заметки
        admin_notes = request.POST.get('admin_notes')
        if admin_notes:
            service_request.admin_notes = admin_notes
        
        service_request.save()
        
        # История
        if new_status and new_status != old_status:
            ServiceRequestHistory.objects.create(
                request=service_request,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                comment=request.POST.get('comment', '')
            )
            
            # Уведомление клиенту
            status_display = dict(ServiceRequest.STATUS_CHOICES).get(new_status)
            Notification.objects.create(
                user=service_request.user,
                type='service',
                title='Статус заявки изменён',
                message=f'Статус заявки #{service_request.request_number} изменён на: {status_display}'
            )
        
        messages.success(request, 'Заявка обновлена')
    
    return redirect('dashboard:service_request_detail', request_number=request_number)


# ============ ПОЛЬЗОВАТЕЛИ ============

class UserListView(AdminRequiredMixin, ListView):
    """Список пользователей."""
    
    model = User
    template_name = 'dashboard/users/list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.order_by('-created_at')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(email__icontains=search) | \
                       queryset.filter(first_name__icontains=search) | \
                       queryset.filter(last_name__icontains=search)
        
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_choices'] = User.ROLE_CHOICES
        return context


class UserDetailView(AdminRequiredMixin, DetailView):
    """Детали пользователя."""
    
    model = User
    template_name = 'dashboard/users/detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        
        context['orders'] = Order.objects.filter(user=user).order_by('-created_at')[:10]
        context['service_requests'] = ServiceRequest.objects.filter(user=user).order_by('-created_at')[:10]
        context['orders_count'] = Order.objects.filter(user=user).count()
        context['orders_total'] = Order.objects.filter(
            user=user, payment_status='paid'
        ).aggregate(total=Sum('total'))['total'] or 0
        
        return context


# ============ ОТЗЫВЫ ============

class ReviewListView(AdminRequiredMixin, ListView):
    """Список отзывов."""
    
    model = Review
    template_name = 'dashboard/reviews/list.html'
    context_object_name = 'reviews'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Review.objects.select_related('user', 'product').order_by('-created_at')
        
        status = self.request.GET.get('status')
        if status == 'pending':
            queryset = queryset.filter(is_approved=False)
        elif status == 'approved':
            queryset = queryset.filter(is_approved=True)
        
        return queryset


@login_required
def review_approve(request, pk):
    """Одобрить отзыв."""
    if not (request.user.is_admin() or request.user.is_manager()):
        return JsonResponse({'success': False})
    
    review = get_object_or_404(Review, pk=pk)
    review.is_approved = True
    review.save()
    
    return JsonResponse({'success': True})


@login_required
def review_reject(request, pk):
    """Отклонить отзыв."""
    if not (request.user.is_admin() or request.user.is_manager()):
        return JsonResponse({'success': False})
    
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    
    return JsonResponse({'success': True})


# ============ СТАТЬИ ============

class PostListView(AdminRequiredMixin, ListView):
    """Список статей блога."""
    
    model = Post
    template_name = 'dashboard/blog/list.html'
    context_object_name = 'posts'
    paginate_by = 20
    
    def get_queryset(self):
        return Post.objects.select_related('author', 'category').order_by('-created_at')


class PostCreateView(AdminRequiredMixin, CreateView):
    """Создание статьи."""
    
    model = Post
    template_name = 'dashboard/blog/form.html'
    fields = ['title', 'category', 'excerpt', 'content', 'image', 'status', 'is_featured']
    success_url = reverse_lazy('dashboard:post_list')
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        if form.instance.status == 'published':
            form.instance.published_at = timezone.now()
        messages.success(self.request, 'Статья создана')
        return super().form_valid(form)


class PostUpdateView(AdminRequiredMixin, UpdateView):
    """Редактирование статьи."""
    
    model = Post
    template_name = 'dashboard/blog/form.html'
    fields = ['title', 'category', 'excerpt', 'content', 'image', 'status', 'is_featured']
    success_url = reverse_lazy('dashboard:post_list')
    
    def form_valid(self, form):
        if form.instance.status == 'published' and not form.instance.published_at:
            form.instance.published_at = timezone.now()
        messages.success(self.request, 'Статья обновлена')
        return super().form_valid(form)


# ============ АКЦИИ ============

class PromotionListView(AdminRequiredMixin, ListView):
    """Список акций."""
    
    model = Promotion
    template_name = 'dashboard/promotions/list.html'
    context_object_name = 'promotions'
    paginate_by = 20


class PromotionCreateView(AdminRequiredMixin, CreateView):
    """Создание акции."""
    
    model = Promotion
    template_name = 'dashboard/promotions/form.html'
    fields = [
        'title', 'slug', 'type', 'short_description', 'description',
        'image', 'discount_percent', 'discount_amount',
        'start_date', 'end_date', 'is_active', 'is_featured', 'terms'
    ]
    success_url = reverse_lazy('dashboard:promotion_list')


class PromotionUpdateView(AdminRequiredMixin, UpdateView):
    """Редактирование акции."""
    
    model = Promotion
    template_name = 'dashboard/promotions/form.html'
    fields = [
        'title', 'slug', 'type', 'short_description', 'description',
        'image', 'discount_percent', 'discount_amount',
        'start_date', 'end_date', 'is_active', 'is_featured', 'terms'
    ]
    success_url = reverse_lazy('dashboard:promotion_list')


# ============ НАСТРОЙКИ ============

@login_required
def settings_view(request):
    """Настройки сайта."""
    if not request.user.is_admin():
        messages.error(request, 'Нет доступа')
        return redirect('dashboard:home')
    
    settings = DashboardSettings.get_settings()
    
    if request.method == 'POST':
        # Обновление настроек
        settings.site_name = request.POST.get('site_name', settings.site_name)
        settings.site_description = request.POST.get('site_description', '')
        settings.email = request.POST.get('email', '')
        settings.phone = request.POST.get('phone', '')
        settings.address = request.POST.get('address', '')
        settings.vk_url = request.POST.get('vk_url', '')
        settings.telegram_url = request.POST.get('telegram_url', '')
        settings.whatsapp = request.POST.get('whatsapp', '')
        settings.min_order_amount = Decimal(request.POST.get('min_order_amount', 0))
        settings.free_delivery_amount = Decimal(request.POST.get('free_delivery_amount', 50000))
        settings.delivery_cost = Decimal(request.POST.get('delivery_cost', 500))
        
        if 'logo' in request.FILES:
            settings.logo = request.FILES['logo']
        
        settings.save()
        messages.success(request, 'Настройки сохранены')
        return redirect('dashboard:settings')
    
    return render(request, 'dashboard/settings.html', {'settings': settings})


# ============ ОТЧЁТЫ ============

@login_required
def reports_view(request):
    """Отчёты и аналитика."""
    if not request.user.is_admin():
        messages.error(request, 'Нет доступа')
        return redirect('dashboard:home')
    
    # Период
    period = request.GET.get('period', 'month')
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    # Продажи
    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        payment_status='paid'
    )
    
    sales_total = orders.aggregate(total=Sum('total'))['total'] or 0
    orders_count = orders.count()
    avg_order = sales_total / orders_count if orders_count > 0 else 0
    
    # Популярные товары
    popular_products = OrderItem.objects.filter(
        order__created_at__date__gte=start_date
    ).values(
        'product__name', 'product__id'
    ).annotate(
        total_qty=Sum('quantity'),
        total_sum=Sum('total')
    ).order_by('-total_qty')[:10]
    
    # По категориям
    category_stats = OrderItem.objects.filter(
        order__created_at__date__gte=start_date
    ).values(
        'product__category__name'
    ).annotate(
        total=Sum('total')
    ).order_by('-total')
    
    # График по дням
    daily_sales = orders.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('date')
    
    context = {
        'period': period,
        'start_date': start_date,
        'sales_total': sales_total,
        'orders_count': orders_count,
        'avg_order': avg_order,
        'popular_products': popular_products,
        'category_stats': category_stats,
        'daily_sales': list(daily_sales),
        'chart_labels': [item['date'].strftime('%d.%m') for item in daily_sales],
        'chart_data': [float(item['total']) for item in daily_sales],
    }
    
    return render(request, 'dashboard/reports.html', context)


# ============ ЛЕНДИНГ МАСТЕРА ============

class TechnicianDashboardView(TechnicianRequiredMixin, ListView):
    """Панель мастера."""
    
    template_name = 'dashboard/technician/home.html'
    context_object_name = 'requests'
    
    def get_queryset(self):
        try:
            technician = self.request.user.technician_profile
            return ServiceRequest.objects.filter(
                technician=technician
            ).exclude(
                status__in=['completed', 'cancelled']
            ).order_by('scheduled_date', 'scheduled_time')
        except:
            return ServiceRequest.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            technician = self.request.user.technician_profile
            today = timezone.now().date()
            
            context['today_requests'] = ServiceRequest.objects.filter(
                technician=technician,
                scheduled_date=today
            ).order_by('scheduled_time')
            
            context['completed_count'] = ServiceRequest.objects.filter(
                technician=technician,
                status='completed'
            ).count()
            
            context['rating'] = technician.rating
            
        except:
            pass
        
        return context