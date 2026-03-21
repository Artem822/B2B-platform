from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory
from apps.accounts.models import Notification


@receiver(pre_save, sender=Order)
def track_status_change(sender, instance, **kwargs):
    """Отслеживание изменения статуса заказа."""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def notify_status_change(sender, instance, created, **kwargs):
    """Уведомление об изменении статуса."""
    if not created and hasattr(instance, '_old_status'):
        if instance._old_status and instance._old_status != instance.status:
            status_display = dict(Order.STATUS_CHOICES).get(instance.status, instance.status)
            
            Notification.objects.create(
                user=instance.user,
                type='order',
                title=f'Статус заказа изменён',
                message=f'Статус заказа #{instance.order_number} изменён на: {status_display}'
            )