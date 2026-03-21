from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Order


class CartAddForm(forms.Form):
    """Форма добавления товара в корзину."""
    
    quantity = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'style': 'width: 80px;'
        })
    )
    include_installation = forms.BooleanField(
        required=False,
        label='Добавить услугу установки',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class CheckoutForm(forms.ModelForm):
    """Форма оформления заказа."""
    
    installation_date = forms.DateField(
        required=False,
        label='Дата установки',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    
    class Meta:
        model = Order
        fields = [
            'delivery_city', 'delivery_address', 'delivery_postal_code',
            'contact_name', 'contact_phone', 'contact_email',
            'payment_method', 'include_installation', 'installation_date',
            'installation_notes', 'customer_notes'
        ]
        widgets = {
            'delivery_city': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'delivery_postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (XXX) XXX-XX-XX'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'payment_method': forms.RadioSelect(),
            'installation_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'customer_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_installation_date(self):
        """Валидация даты установки."""
        date = self.cleaned_data.get('installation_date')
        include_installation = self.cleaned_data.get('include_installation')
        
        if include_installation and date:
            # Проверка что дата не в прошлом
            if date < timezone.now().date():
                raise forms.ValidationError('Дата установки не может быть в прошлом.')
            
            # Минимум через 2 дня
            min_date = timezone.now().date() + timedelta(days=2)
            if date < min_date:
                raise forms.ValidationError(
                    f'Минимальная дата установки: {min_date.strftime("%d.%m.%Y")}. '
                    f'Установка возможна не ранее чем через 2 дня после заказа.'
                )
            
            # Максимум через 60 дней
            max_date = timezone.now().date() + timedelta(days=60)
            if date > max_date:
                raise forms.ValidationError(
                    f'Максимальная дата установки: {max_date.strftime("%d.%m.%Y")}'
                )
        
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        include_installation = cleaned_data.get('include_installation')
        installation_date = cleaned_data.get('installation_date')
        
        if include_installation and not installation_date:
            self.add_error('installation_date', 'Укажите желаемую дату установки.')
        
        return cleaned_data


class PromoCodeForm(forms.Form):
    """Форма промокода."""
    
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите промокод'
        })
    )