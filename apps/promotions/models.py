from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django_ckeditor_5.fields import CKEditor5Field
from apps.products.models import generate_unique_slug


class Promotion(models.Model):
    """Акция/Промо-кампания."""
    
    TYPE_CHOICES = [
        ('discount', 'Скидка на товары'),
        ('service', 'Скидка на услуги'),
        ('bundle', 'Комплект'),
        ('seasonal', 'Сезонная'),
    ]
    
    title = models.CharField(_('Название'), max_length=300)
    slug = models.SlugField(_('URL'), max_length=300, unique=True, blank=True)
    type = models.CharField(_('Тип'), max_length=20, choices=TYPE_CHOICES)
    
    short_description = models.TextField(_('Краткое описание'), max_length=500)
    description = CKEditor5Field(_('Описание'))
    
    image = models.ImageField(_('Изображение'), upload_to='promotions/')
    banner_image = models.ImageField(_('Баннер'), upload_to='promotions/', blank=True, null=True)
    
    discount_percent = models.PositiveIntegerField(
        _('Скидка (%)'),
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True, blank=True
    )
    discount_amount = models.DecimalField(
        _('Скидка (сумма)'), max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    
    # Применимость
    products = models.ManyToManyField(
        'products.Product', blank=True,
        related_name='promotions',
        verbose_name=_('Товары')
    )
    categories = models.ManyToManyField(
        'products.Category', blank=True,
        related_name='promotions',
        verbose_name=_('Категории')
    )
    services = models.ManyToManyField(
        'services.Service', blank=True,
        related_name='promotions',
        verbose_name=_('Услуги')
    )
    
    # Даты
    start_date = models.DateTimeField(_('Дата начала'))
    end_date = models.DateTimeField(_('Дата окончания'))
    
    is_active = models.BooleanField(_('Активна'), default=True)
    is_featured = models.BooleanField(_('На главной'), default=False)
    
    terms = models.TextField(_('Условия акции'), blank=True)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('Акция')
        verbose_name_plural = _('Акции')
        ordering = ['-start_date']
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Promotion, self.title, self)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Акция действует."""
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
    
    @property
    def days_left(self):
        """Дней до окончания."""
        if self.end_date > timezone.now():
            return (self.end_date - timezone.now()).days
        return 0


class PromoCode(models.Model):
    """Промокод."""
    
    TYPE_CHOICES = [
        ('percent', 'Процент'),
        ('fixed', 'Фиксированная сумма'),
    ]
    
    code = models.CharField(_('Код'), max_length=50, unique=True)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='promo_codes',
        verbose_name=_('Акция')
    )
    
    type = models.CharField(_('Тип'), max_length=20, choices=TYPE_CHOICES, default='percent')
    value = models.DecimalField(
        _('Значение'), max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    min_order_amount = models.DecimalField(
        _('Минимальная сумма заказа'), max_digits=10, decimal_places=2,
        default=0
    )
    max_discount_amount = models.DecimalField(
        _('Максимальная скидка'), max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    
    usage_limit = models.PositiveIntegerField(_('Лимит использований'), null=True, blank=True)
    usage_limit_per_user = models.PositiveIntegerField(
        _('Лимит на пользователя'),
        default=1
    )
    times_used = models.PositiveIntegerField(_('Использовано раз'), default=0)
    
    start_date = models.DateTimeField(_('Дата начала'))
    end_date = models.DateTimeField(_('Дата окончания'))
    
    is_active = models.BooleanField(_('Активен'), default=True)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Промокод')
        verbose_name_plural = _('Промокоды')
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        """Промокод действителен."""
        now = timezone.now()
        if not self.is_active:
            return False
        if not (self.start_date <= now <= self.end_date):
            return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        return True
    
    def calculate_discount(self, order_total):
        """Рассчитать скидку."""
        if order_total < self.min_order_amount:
            return 0
        
        if self.type == 'percent':
            discount = order_total * (self.value / 100)
        else:
            discount = self.value
        
        if self.max_discount_amount:
            discount = min(discount, self.max_discount_amount)
        
        return round(discount, 2)


class Banner(models.Model):
    """Баннер на сайте."""
    
    POSITION_CHOICES = [
        ('home_top', 'Главная - верх'),
        ('home_middle', 'Главная - середина'),
        ('sidebar', 'Сайдбар'),
        ('catalog', 'Каталог'),
    ]
    
    title = models.CharField(_('Название'), max_length=200)
    image = models.ImageField(_('Изображение'), upload_to='banners/')
    image_mobile = models.ImageField(
        _('Изображение (мобильное)'),
        upload_to='banners/', blank=True, null=True
    )
    
    url = models.URLField(_('Ссылка'), blank=True)
    position = models.CharField(_('Позиция'), max_length=20, choices=POSITION_CHOICES)
    
    start_date = models.DateTimeField(_('Дата начала'), null=True, blank=True)
    end_date = models.DateTimeField(_('Дата окончания'), null=True, blank=True)
    
    is_active = models.BooleanField(_('Активен'), default=True)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Баннер')
        verbose_name_plural = _('Баннеры')
        ordering = ['position', 'order']
    
    def __str__(self):
        return self.title
    
    @property
    def is_visible(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True