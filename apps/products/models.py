from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from unidecode import unidecode


def generate_unique_slug(model_class, text, instance=None):
    """Генерирует уникальный slug, добавляя суффикс при необходимости."""
    base_slug = slugify(unidecode(text))
    if not base_slug:
        base_slug = 'item'
    slug = base_slug
    counter = 2
    qs = model_class.objects.all()
    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug


class Category(models.Model):
    """Категория товаров."""

    name = models.CharField(_('Название'), max_length=200)
    slug = models.SlugField(_('URL'), max_length=200, unique=True, blank=True)
    description = models.TextField(_('Описание'), blank=True)
    image = models.ImageField(_('Изображение'), upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name=_('Родительская категория')
    )
    is_active = models.BooleanField(_('Активна'), default=True)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name, self)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('products:category', kwargs={'slug': self.slug})
    
    def get_all_children(self):
        """Получить все дочерние категории."""
        children = list(self.children.filter(is_active=True))
        for child in self.children.filter(is_active=True):
            children.extend(child.get_all_children())
        return children


class Brand(models.Model):
    """Бренд/Производитель."""
    
    name = models.CharField(_('Название'), max_length=200)
    slug = models.SlugField(_('URL'), max_length=200, unique=True, blank=True)
    logo = models.ImageField(_('Логотип'), upload_to='brands/', blank=True, null=True)
    description = models.TextField(_('Описание'), blank=True)
    website = models.URLField(_('Сайт'), blank=True)
    is_active = models.BooleanField(_('Активен'), default=True)
    
    class Meta:
        verbose_name = _('Бренд')
        verbose_name_plural = _('Бренды')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Brand, self.name, self)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Модель товара."""
    
    CONDITION_CHOICES = [
        ('new', 'Новый'),
        ('refurbished', 'Восстановленный'),
        ('used', 'Б/У'),
    ]
    
    name = models.CharField(_('Название'), max_length=300)
    slug = models.SlugField(_('URL'), max_length=300, unique=True, blank=True)
    sku = models.CharField(_('Артикул'), max_length=50, unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Категория')
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Бренд'),
        null=True, blank=True
    )
    description = models.TextField(_('Описание'))
    short_description = models.TextField(_('Краткое описание'), max_length=500, blank=True)
    
    # Цены
    price = models.DecimalField(
        _('Цена'), max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    old_price = models.DecimalField(
        _('Старая цена'), max_digits=12, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Склад
    stock = models.PositiveIntegerField(_('Количество на складе'), default=0)
    reserved = models.PositiveIntegerField(_('Зарезервировано'), default=0)
    
    # Характеристики
    condition = models.CharField(
        _('Состояние'), max_length=20,
        choices=CONDITION_CHOICES, default='new'
    )
    warranty_months = models.PositiveIntegerField(_('Гарантия (мес.)'), default=12)
    weight = models.DecimalField(
        _('Вес (кг)'), max_digits=10, decimal_places=3,
        null=True, blank=True
    )
    
    # Изображения
    main_image = models.ImageField(_('Главное изображение'), upload_to='products/')
    
    # Статусы
    is_active = models.BooleanField(_('Активен'), default=True)
    is_featured = models.BooleanField(_('Рекомендуемый'), default=False)
    
    # Мета
    meta_title = models.CharField(_('Meta Title'), max_length=200, blank=True)
    meta_description = models.TextField(_('Meta Description'), blank=True)
    
    # Даты
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('Товар')
        verbose_name_plural = _('Товары')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Product, self.name, self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'slug': self.slug})
    
    @property
    def main_image_url(self):
        """URL главного изображения (безопасный доступ)."""
        try:
            if self.main_image and self.main_image.name:
                return self.main_image.url
        except ValueError:
            pass
        return None

    @property
    def available_stock(self):
        """Доступное количество (за вычетом зарезервированного)."""
        return max(0, self.stock - self.reserved)
    
    @property
    def is_in_stock(self):
        """Товар в наличии."""
        return self.available_stock > 0
    
    @property
    def discount_percent(self):
        """Процент скидки."""
        if self.old_price and self.old_price > self.price:
            return int(100 - (self.price / self.old_price * 100))
        return 0
    
    @property
    def avg_rating(self):
        """Средний рейтинг товара."""
        from django.db.models import Avg
        result = self.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'))
        return result['avg'] or 0

    def reserve_stock(self, quantity):
        """Зарезервировать товар."""
        if quantity <= self.available_stock:
            self.reserved += quantity
            self.save(update_fields=['reserved'])
            return True
        return False
    
    def release_reserved(self, quantity):
        """Освободить резерв."""
        self.reserved = max(0, self.reserved - quantity)
        self.save(update_fields=['reserved'])
    
    def reduce_stock(self, quantity):
        """Списать со склада."""
        if quantity <= self.stock:
            self.stock -= quantity
            self.reserved = max(0, self.reserved - quantity)
            self.save(update_fields=['stock', 'reserved'])
            return True
        return False
    
    def return_to_stock(self, quantity):
        """Вернуть на склад."""
        self.stock += quantity
        self.save(update_fields=['stock'])


class ProductImage(models.Model):
    """Дополнительные изображения товара."""
    
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Товар')
    )
    image = models.ImageField(_('Изображение'), upload_to='products/')
    alt_text = models.CharField(_('Alt текст'), max_length=200, blank=True)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    
    class Meta:
        verbose_name = _('Изображение товара')
        verbose_name_plural = _('Изображения товаров')
        ordering = ['order']
    
    def __str__(self):
        return f"Изображение {self.product.name}"


class ProductSpecification(models.Model):
    """Характеристики товара."""
    
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='specifications',
        verbose_name=_('Товар')
    )
    name = models.CharField(_('Название'), max_length=100)
    value = models.CharField(_('Значение'), max_length=200)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    
    class Meta:
        verbose_name = _('Характеристика')
        verbose_name_plural = _('Характеристики')
        ordering = ['order']
    
    def __str__(self):
        return f"{self.name}: {self.value}"


class Wishlist(models.Model):
    """Список желаний."""
    
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name=_('Пользователь')
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='in_wishlists',
        verbose_name=_('Товар')
    )
    created_at = models.DateTimeField(_('Дата добавления'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Избранное')
        verbose_name_plural = _('Избранное')
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"