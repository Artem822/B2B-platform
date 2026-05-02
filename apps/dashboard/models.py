from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DashboardSettings(models.Model):
    """Настройки сайта."""
    
    site_name = models.CharField(_('Название сайта'), max_length=200, default='Интернет-магазин комплектующих для серверов')
    site_description = models.TextField(_('Описание'), blank=True)
    logo = models.ImageField(_('Логотип'), upload_to='settings/', blank=True, null=True)
    favicon = models.ImageField(_('Favicon'), upload_to='settings/', blank=True, null=True)
    
    # Контакты
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Телефон'), max_length=20, blank=True)
    address = models.TextField(_('Адрес'), blank=True)
    
    # Социальные сети
    vk_url = models.URLField(_('VK'), blank=True)
    telegram_url = models.URLField(_('Telegram'), blank=True)
    whatsapp = models.CharField(_('WhatsApp'), max_length=20, blank=True)
    
    # SEO
    meta_title = models.CharField(_('Meta Title'), max_length=200, blank=True)
    meta_description = models.TextField(_('Meta Description'), blank=True)
    meta_keywords = models.TextField(_('Meta Keywords'), blank=True)
    
    # Настройки магазина
    min_order_amount = models.DecimalField(
        _('Минимальная сумма заказа'),
        max_digits=10, decimal_places=2, default=0
    )
    free_delivery_amount = models.DecimalField(
        _('Бесплатная доставка от'),
        max_digits=10, decimal_places=2, default=50000
    )
    delivery_cost = models.DecimalField(
        _('Стоимость доставки'),
        max_digits=10, decimal_places=2, default=500
    )
    
    class Meta:
        verbose_name = _('Настройки сайта')
        verbose_name_plural = _('Настройки сайта')
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class ActivityLog(models.Model):
    """Лог активности в админ-панели."""
    
    ACTION_CHOICES = [
        ('create', 'Создание'),
        ('update', 'Изменение'),
        ('delete', 'Удаление'),
        ('login', 'Вход'),
        ('logout', 'Выход'),
        ('other', 'Другое'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='activity_logs',
        verbose_name=_('Пользователь')
    )
    action = models.CharField(_('Действие'), max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(_('Модель'), max_length=100, blank=True)
    object_id = models.PositiveIntegerField(_('ID объекта'), null=True, blank=True)
    object_repr = models.CharField(_('Объект'), max_length=300, blank=True)
    details = models.TextField(_('Детали'), blank=True)
    ip_address = models.GenericIPAddressField(_('IP адрес'), null=True, blank=True)
    created_at = models.DateTimeField(_('Дата'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Лог активности')
        verbose_name_plural = _('Логи активности')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"