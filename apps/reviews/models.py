from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class Review(models.Model):
    """Отзыв о товаре."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Пользователь')
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Товар')
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviews',
        verbose_name=_('Заказ')
    )
    
    rating = models.PositiveIntegerField(
        _('Рейтинг'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(_('Заголовок'), max_length=200, blank=True)
    content = models.TextField(_('Отзыв'))
    
    # Оценки по критериям
    quality_rating = models.PositiveIntegerField(
        _('Качество'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    value_rating = models.PositiveIntegerField(
        _('Соотношение цена/качество'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    
    # Плюсы и минусы
    pros = models.TextField(_('Достоинства'), blank=True)
    cons = models.TextField(_('Недостатки'), blank=True)
    
    is_approved = models.BooleanField(_('Одобрен'), default=False)
    is_verified_purchase = models.BooleanField(_('Проверенная покупка'), default=False)
    
    # Полезность
    helpful_count = models.PositiveIntegerField(_('Полезно'), default=0)
    not_helpful_count = models.PositiveIntegerField(_('Не полезно'), default=0)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')
        ordering = ['-created_at']
        unique_together = ['user', 'product']  # Один отзыв на товар от пользователя
    
    def __str__(self):
        return f"Отзыв от {self.user.email} на {self.product.name}"


class ReviewImage(models.Model):
    """Фото к отзыву."""
    
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Отзыв')
    )
    image = models.ImageField(_('Изображение'), upload_to='reviews/')
    
    class Meta:
        verbose_name = _('Фото отзыва')
        verbose_name_plural = _('Фото отзывов')


class ReviewVote(models.Model):
    """Голос за отзыв (полезно/не полезно)."""
    
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE,
        related_name='votes',
        verbose_name=_('Отзыв')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='review_votes',
        verbose_name=_('Пользователь')
    )
    is_helpful = models.BooleanField(_('Полезно'))
    created_at = models.DateTimeField(_('Дата'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Голос за отзыв')
        verbose_name_plural = _('Голоса за отзывы')
        unique_together = ['review', 'user']


class ServiceReview(models.Model):
    """Отзыв об услуге/мастере."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='service_reviews',
        verbose_name=_('Пользователь')
    )
    service_request = models.OneToOneField(
        'services.ServiceRequest', on_delete=models.CASCADE,
        related_name='review',
        verbose_name=_('Заявка на услугу')
    )
    technician = models.ForeignKey(
        'services.Technician', on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Мастер'),
        null=True, blank=True
    )
    
    rating = models.PositiveIntegerField(
        _('Рейтинг'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    content = models.TextField(_('Отзыв'))
    
    quality_rating = models.PositiveIntegerField(
        _('Качество работы'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    punctuality_rating = models.PositiveIntegerField(
        _('Пунктуальность'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication_rating = models.PositiveIntegerField(
        _('Общение'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    is_approved = models.BooleanField(_('Одобрен'), default=False)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Отзыв об услуге')
        verbose_name_plural = _('Отзывы об услугах')
        ordering = ['-created_at']