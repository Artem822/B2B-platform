from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Менеджер для кастомной модели пользователя."""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email обязателен'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Кастомная модель пользователя."""
    
    ROLE_CHOICES = [
        ('client', 'Клиент'),
        ('manager', 'Менеджер'),
        ('technician', 'Мастер'),
        ('admin', 'Администратор'),
    ]
    
    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(_('Телефон'), max_length=20, blank=True)
    company_name = models.CharField(_('Название компании'), max_length=200, blank=True)
    inn = models.CharField(_('ИНН'), max_length=12, blank=True)
    kpp = models.CharField(_('КПП'), max_length=9, blank=True)
    legal_address = models.TextField(_('Юридический адрес'), blank=True)
    actual_address = models.TextField(_('Фактический адрес'), blank=True)
    role = models.CharField(_('Роль'), max_length=20, choices=ROLE_CHOICES, default='client')
    avatar = models.ImageField(_('Аватар'), upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(_('Верифицирован'), default=False)
    created_at = models.DateTimeField(_('Дата регистрации'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    def is_manager(self):
        return self.role in ['admin', 'manager'] or self.is_superuser
    
    def is_technician(self):
        return self.role == 'technician'


class Address(models.Model):
    """Адреса доставки пользователя."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(_('Название'), max_length=100)
    city = models.CharField(_('Город'), max_length=100)
    street = models.CharField(_('Улица'), max_length=200)
    building = models.CharField(_('Дом'), max_length=20)
    office = models.CharField(_('Офис/Квартира'), max_length=20, blank=True)
    postal_code = models.CharField(_('Почтовый индекс'), max_length=10, blank=True)
    is_default = models.BooleanField(_('По умолчанию'), default=False)
    
    class Meta:
        verbose_name = _('Адрес')
        verbose_name_plural = _('Адреса')
    
    def __str__(self):
        return f"{self.title}: {self.city}, {self.street}, {self.building}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Notification(models.Model):
    """Уведомления пользователя."""
    
    TYPE_CHOICES = [
        ('order', 'Заказ'),
        ('service', 'Услуга'),
        ('promo', 'Акция'),
        ('system', 'Система'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(_('Тип'), max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(_('Заголовок'), max_length=200)
    message = models.TextField(_('Сообщение'))
    is_read = models.BooleanField(_('Прочитано'), default=False)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Уведомление')
        verbose_name_plural = _('Уведомления')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"