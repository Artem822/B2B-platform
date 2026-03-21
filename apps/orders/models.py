from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class Order(models.Model):
    """Модель заказа."""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждён'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
        ('refunded', 'Возврат'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('failed', 'Ошибка оплаты'),
        ('refunded', 'Возвращён'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Банковская карта'),
        ('invoice', 'Счёт на оплату'),
        ('cash', 'Наличные'),
    ]
    
    # Идентификаторы
    order_number = models.CharField(_('Номер заказа'), max_length=50, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_('Пользователь')
    )
    
    # Статусы
    status = models.CharField(
        _('Статус'), max_length=20,
        choices=STATUS_CHOICES, default='pending'
    )
    payment_status = models.CharField(
        _('Статус оплаты'), max_length=20,
        choices=PAYMENT_STATUS_CHOICES, default='pending'
    )
    payment_method = models.CharField(
        _('Способ оплаты'), max_length=20,
        choices=PAYMENT_METHOD_CHOICES, default='invoice'
    )
    
    # Адрес доставки
    delivery_address = models.TextField(_('Адрес доставки'))
    delivery_city = models.CharField(_('Город'), max_length=100)
    delivery_postal_code = models.CharField(_('Индекс'), max_length=10, blank=True)
    
    # Контакты
    contact_name = models.CharField(_('Контактное лицо'), max_length=200)
    contact_phone = models.CharField(_('Телефон'), max_length=20)
    contact_email = models.EmailField(_('Email'))
    
    # Суммы
    subtotal = models.DecimalField(
        _('Сумма товаров'), max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    discount = models.DecimalField(
        _('Скидка'), max_digits=12, decimal_places=2,
        default=0, validators=[MinValueValidator(0)]
    )
    delivery_cost = models.DecimalField(
        _('Стоимость доставки'), max_digits=10, decimal_places=2,
        default=0, validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(
        _('Итого'), max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Услуги
    include_installation = models.BooleanField(_('Включая установку'), default=False)
    installation_cost = models.DecimalField(
        _('Стоимость установки'), max_digits=10, decimal_places=2,
        default=0, validators=[MinValueValidator(0)]
    )
    installation_date = models.DateField(_('Дата установки'), null=True, blank=True)
    installation_notes = models.TextField(_('Примечания к установке'), blank=True)
    
    # Промокод
    promo_code = models.ForeignKey(
        'promotions.PromoCode', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
        verbose_name=_('Промокод')
    )
    
    # Примечания
    customer_notes = models.TextField(_('Комментарий клиента'), blank=True)
    admin_notes = models.TextField(_('Заметки администратора'), blank=True)
    
    # Даты
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    confirmed_at = models.DateTimeField(_('Дата подтверждения'), null=True, blank=True)
    shipped_at = models.DateTimeField(_('Дата отправки'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Дата доставки'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Дата отмены'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заказ #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_number():
        """Генерация уникального номера заказа."""
        timestamp = timezone.now().strftime('%Y%m%d%H%M')
        unique = uuid.uuid4().hex[:6].upper()
        return f"ORD-{timestamp}-{unique}"
    
    def calculate_total(self):
        """Расчёт итоговой суммы."""
        self.total = (
            self.subtotal 
            - self.discount 
            + self.delivery_cost 
            + self.installation_cost
        )
        return self.total
    
    def confirm(self):
        """Подтвердить заказ."""
        if self.status == 'pending':
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()
            # Списываем товары со склада
            for item in self.items.all():
                item.product.reduce_stock(item.quantity)
            return True
        return False
    
    def cancel(self, reason=''):
        """Отменить заказ."""
        if self.status not in ['completed', 'cancelled', 'refunded']:
            old_status = self.status
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            if reason:
                self.admin_notes += f"\nПричина отмены: {reason}"
            self.save()
            
            # Возвращаем товары на склад
            for item in self.items.all():
                if old_status == 'pending':
                    # Если заказ не был подтверждён, освобождаем резерв
                    item.product.release_reserved(item.quantity)
                else:
                    # Если заказ был подтверждён, возвращаем на склад
                    item.product.return_to_stock(item.quantity)
            
            return True
        return False
    
    def can_be_cancelled(self):
        """Можно ли отменить заказ."""
        return self.status in ['pending', 'confirmed', 'processing']


class OrderItem(models.Model):
    """Позиция заказа."""
    
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Заказ')
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name=_('Товар')
    )
    quantity = models.PositiveIntegerField(_('Количество'), default=1)
    price = models.DecimalField(
        _('Цена за единицу'), max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(
        _('Сумма'), max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Услуга установки для конкретного товара
    include_installation = models.BooleanField(_('Установка'), default=False)
    installation_price = models.DecimalField(
        _('Цена установки'), max_digits=10, decimal_places=2,
        default=0
    )
    
    class Meta:
        verbose_name = _('Позиция заказа')
        verbose_name_plural = _('Позиции заказа')
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        if self.include_installation:
            self.total += self.installation_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """История изменения статуса заказа."""
    
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name=_('Заказ')
    )
    old_status = models.CharField(_('Предыдущий статус'), max_length=20, blank=True)
    new_status = models.CharField(_('Новый статус'), max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name=_('Изменил')
    )
    comment = models.TextField(_('Комментарий'), blank=True)
    created_at = models.DateTimeField(_('Дата изменения'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('История статуса')
        verbose_name_plural = _('История статусов')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} -> {self.new_status}"