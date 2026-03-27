from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order


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
