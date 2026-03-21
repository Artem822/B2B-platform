from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field
from unidecode import unidecode


class BlogCategory(models.Model):
    """Категория блога."""
    
    name = models.CharField(_('Название'), max_length=200)
    slug = models.SlugField(_('URL'), max_length=200, unique=True)
    description = models.TextField(_('Описание'), blank=True)
    
    class Meta:
        verbose_name = _('Категория блога')
        verbose_name_plural = _('Категории блога')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Tag(models.Model):
    """Тег статьи."""
    
    name = models.CharField(_('Название'), max_length=100)
    slug = models.SlugField(_('URL'), max_length=100, unique=True)
    
    class Meta:
        verbose_name = _('Тег')
        verbose_name_plural = _('Теги')
    
    def __str__(self):
        return self.name


class Post(models.Model):
    """Статья блога."""
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликовано'),
    ]
    
    title = models.CharField(_('Заголовок'), max_length=300)
    slug = models.SlugField(_('URL'), max_length=300, unique=True, blank=True)
    
    category = models.ForeignKey(
        BlogCategory, on_delete=models.SET_NULL,
        null=True, related_name='posts',
        verbose_name=_('Категория')
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name=_('Теги'))
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='blog_posts',
        verbose_name=_('Автор')
    )
    
    excerpt = models.TextField(_('Краткое описание'), max_length=500, blank=True)
    content = CKEditor5Field(_('Содержание'))
    
    image = models.ImageField(_('Изображение'), upload_to='blog/', blank=True, null=True)
    
    status = models.CharField(
        _('Статус'), max_length=20,
        choices=STATUS_CHOICES, default='draft'
    )
    is_featured = models.BooleanField(_('Рекомендуемая'), default=False)
    
    views_count = models.PositiveIntegerField(_('Просмотры'), default=0)
    
    meta_title = models.CharField(_('Meta Title'), max_length=200, blank=True)
    meta_description = models.TextField(_('Meta Description'), blank=True)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    published_at = models.DateTimeField(_('Дата публикации'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Статья')
        verbose_name_plural = _('Статьи')
        ordering = ['-published_at', '-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(unidecode(self.title))
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})
    
    def increment_views(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])


class Comment(models.Model):
    """Комментарий к статье."""
    
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Статья')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='blog_comments',
        verbose_name=_('Пользователь')
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='replies',
        verbose_name=_('Родительский комментарий')
    )
    
    content = models.TextField(_('Комментарий'))
    
    is_approved = models.BooleanField(_('Одобрен'), default=True)
    
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('Комментарий')
        verbose_name_plural = _('Комментарии')
        ordering = ['created_at']
    
    def __str__(self):
        return f"Комментарий от {self.user.email} к {self.post.title}"