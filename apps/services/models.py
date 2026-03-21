from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class ServiceCategory(models.Model):
    """Категория услуг."""
    
    name = models.CharField(_('Название'), max_length=200)
    slug = models.SlugField(_('URL'), max_length=200, unique=True)
    description = models.TextField(_('Описание'), blank=True)
    icon = models.CharField(_('Иконка (CSS класс)'), max_length=50, blank=True)
    image = models.ImageField(_('Изображение'), upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(_('Активна'), default=True)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    
    class Meta:
        verbose_name = _('Категория услуг')
        verbose_name_plural = _('Категории услуг')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Service(models.Model):
    """Услуга."""
    
    PRICING_TYPE_CHOICES = [
        ('fixed', 'Фиксированная цена'),
        ('hourly', 'Почасовая оплата'),
        ('negotiable', 'По договорённости'),
    ]
    
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.CASCADE,
        related_name='services',
        verbose_name=_('Категория')
    )
    name = models.CharField(_('Название'), max_length=200)
    slug = models.SlugField(_('URL'), max_length=200, unique=True)
    description = models.TextField(_('Описание'))
    short_description = models.CharField(_('Краткое описание'), max_length=300, blank=True)
    
    pricing_type = models.CharField(
        _('Тип цены'), max_length=20,
        choices=PRICING_TYPE_CHOICES, default='fixed'
    )
    price = models.DecimalField(
        _('Цена'), max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    price_per_hour = models.DecimalField(
        _('Цена за час'), max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    min_hours = models.PositiveIntegerField(_('Минимум часов'), default=1)
    
    duration_hours = models.PositiveIntegerField(_('Примерная длительность (часов)'), default=1)
    
    image = models.ImageField(_('Изображение'), upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(_('Активна'), default=True)
    is_popular = models.BooleanField(_('Популярная'), default=False)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('Услуга')
        verbose_name_plural = _('Услуги')
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name
    
    def get_price_display(self):
        if self.pricing_type == 'hourly':
            return f"от {self.price_per_hour} ₽/час"
        elif self.pricing_type == 'negotiable':
            return "По договорённости"
        return f"{self.price} ₽"


class Technician(models.Model):
    """Мастер/Специалист."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='technician_profile',
        verbose_name=_('Пользователь')
    )
    specializations = models.ManyToManyField(
        ServiceCategory, related_name='technicians',
        verbose_name=_('Специализации')
    )
    bio = models.TextField(_('О себе'), blank=True)
    experience_years = models.PositiveIntegerField(_('Опыт работы (лет)'), default=0)
    certifications = models.TextField(_('Сертификаты'), blank=True)
    hourly_rate = models.DecimalField(
        _('Ставка в час'), max_digits=10, decimal_places=2,
        default=0
    )
    is_available = models.BooleanField(_('Доступен'), default=True)
    rating = models.DecimalField(
        _('Рейтинг'), max_digits=3, decimal_places=2,
        default=0
    )
    completed_orders = models.PositiveIntegerField(_('Выполнено заказов'), default=0)
    
    class Meta:
        verbose_name = _('Мастер')
        verbose_name_plural = _('Мастера')
    
    def __str__(self):
        return f"{self.user.full_name} - Мастер"
    
    def update_rating(self):
        """Обновить рейтинг на основе отзывов."""
        from django.db.models import Avg
        avg = self.service_requests.filter(
            status='completed',
            review__isnull=False
        ).aggregate(avg=Avg('review__rating'))['avg']
        
        if avg:
            self.rating = round(avg, 2)
            self.save(update_fields=['rating'])


class ServiceRequest(models.Model):
    """Заявка на услугу / Вызов мастера."""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('confirmed', 'Подтверждена'),
        ('assigned', 'Мастер назначен'),
        ('in_progress', 'Выполняется'),
        ('completed', 'Выполнена'),
        ('cancelled', 'Отменена'),
    ]
    
    URGENCY_CHOICES = [
        ('normal', 'Обычная'),
        ('urgent', 'Срочная'),
        ('emergency', 'Экстренная'),
    ]
    
    # Идентификаторы
    request_number = models.CharField(
        _('Номер заявки'), max_length=50,
        unique=True, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='service_requests',
        verbose_name=_('Клиент')
    )
    
    # Услуга
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT,
        related_name='requests',
        verbose_name=_('Услуга')
    )
    
    # Связь с заказом (если установка при покупке)
    related_order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='service_requests',
        verbose_name=_('Связанный заказ')
    )
    
    # Мастер
    technician = models.ForeignKey(
        Technician, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='service_requests',
        verbose_name=_('Мастер')
    )
    
    # Статус и срочность
    status = models.CharField(
        _('Статус'), max_length=20,
        choices=STATUS_CHOICES, default='pending'
    )
    urgency = models.CharField(
        _('Срочность'), max_length=20,
        choices=URGENCY_CHOICES, default='normal'
    )
    
    # Описание проблемы
    title = models.CharField(_('Заголовок'), max_length=200)
    description = models.TextField(_('Описание проблемы'))
    
    # Контактная информация
    contact_name = models.CharField(_('Контактное лицо'), max_length=200)
    contact_phone = models.CharField(_('Телефон'), max_length=20)
    contact_email = models.EmailField(_('Email'))
    
    # Адрес
    address_city = models.CharField(_('Город'), max_length=100)
    address_street = models.CharField(_('Адрес'), max_length=300)
    
    # Дата и время
    preferred_date = models.DateField(_('Желаемая дата'))
    preferred_time_from = models.TimeField(_('Время с'))
    preferred_time_to = models.TimeField(_('Время до'))
    
    scheduled_date = models.DateField(_('Назначенная дата'), null=True, blank=True)
    scheduled_time = models.TimeField(_('Назначенное время'), null=True, blank=True)
    
    # Стоимость
    estimated_cost = models.DecimalField(
        _('Предварительная стоимость'), max_digits=10, decimal_places=2,
        default=0
    )
    final_cost = models.DecimalField(
        _('Итоговая стоимость'), max_digits=10, decimal_places=2,
        default=0
    )
    hours_worked = models.DecimalField(
        _('Отработано часов'), max_digits=5, decimal_places=2,
        default=0
    )
    
    # Примечания
    customer_notes = models.TextField(_('Примечания клиента'), blank=True)
    technician_notes = models.TextField(_('Заметки мастера'), blank=True)
    admin_notes = models.TextField(_('Заметки администратора'), blank=True)
    
    # Фото проблемы
    photo1 = models.ImageField(_('Фото 1'), upload_to='service_requests/', blank=True, null=True)
    photo2 = models.ImageField(_('Фото 2'), upload_to='service_requests/', blank=True, null=True)
    photo3 = models.ImageField(_('Фото 3'), upload_to='service_requests/', blank=True, null=True)
    
    # Даты
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    completed_at = models.DateTimeField(_('Дата выполнения'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Дата отмены'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Заявка на услугу')
        verbose_name_plural = _('Заявки на услуги')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заявка #{self.request_number}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = self.generate_request_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_request_number():
        timestamp = timezone.now().strftime('%Y%m%d')
        unique = uuid.uuid4().hex[:6].upper()
        return f"SRV-{timestamp}-{unique}"
    
    def complete(self, hours_worked, final_cost):
        """Завершить заявку."""
        self.status = 'completed'
        self.hours_worked = hours_worked
        self.final_cost = final_cost
        self.completed_at = timezone.now()
        self.save()
        
        # Обновляем счётчик мастера
        if self.technician:
            self.technician.completed_orders += 1
            self.technician.save()
            self.technician.update_rating()
    
    def cancel(self, reason=''):
        """Отменить заявку."""
        if self.status not in ['completed', 'cancelled']:
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            if reason:
                self.admin_notes += f"\nПричина отмены: {reason}"
            self.save()
            return True
        return False
    
    def can_be_cancelled(self):
        return self.status in ['pending', 'confirmed', 'assigned']


class ServiceRequestHistory(models.Model):
    """История изменения статуса заявки."""
    
    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name=_('Заявка')
    )
    old_status = models.CharField(_('Предыдущий статус'), max_length=20, blank=True)
    new_status = models.CharField(_('Новый статус'), max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name=_('Изменил')
    )
    comment = models.TextField(_('Комментарий'), blank=True)
    created_at = models.DateTimeField(_('Дата'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('История статуса заявки')
        verbose_name_plural = _('История статусов заявок')
        ordering = ['-created_at']