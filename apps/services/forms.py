from django import forms
from django.utils import timezone
from datetime import timedelta, time
from .models import ServiceRequest


class ServiceRequestForm(forms.ModelForm):
    """Форма заявки на услугу."""
    
    preferred_date = forms.DateField(
        label='Желаемая дата',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    
    preferred_time_from = forms.TimeField(
        label='Время с',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
        })
    )
    
    preferred_time_to = forms.TimeField(
        label='Время до',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
        })
    )
    
    class Meta:
        model = ServiceRequest
        fields = [
            'service', 'urgency', 'title', 'description',
            'contact_name', 'contact_phone', 'contact_email',
            'address_city', 'address_street',
            'preferred_date', 'preferred_time_from', 'preferred_time_to',
            'customer_notes', 'photo1', 'photo2', 'photo3'
        ]
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Кратко опишите проблему'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Подробное описание...'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (XXX) XXX-XX-XX'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address_city': forms.TextInput(attrs={'class': 'form-control'}),
            'address_street': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'customer_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_preferred_date(self):
        """Валидация даты."""
        date = self.cleaned_data.get('preferred_date')
        urgency = self.data.get('urgency', 'normal')
        
        if date < timezone.now().date():
            raise forms.ValidationError('Дата не может быть в прошлом.')
        
        # Для обычных заявок минимум через день
        if urgency == 'normal':
            min_date = timezone.now().date() + timedelta(days=1)
            if date < min_date:
                raise forms.ValidationError(
                    f'Для обычной заявки минимальная дата: {min_date.strftime("%d.%m.%Y")}'
                )
        
        # Максимум через 30 дней
        max_date = timezone.now().date() + timedelta(days=30)
        if date > max_date:
            raise forms.ValidationError(
                f'Максимальная дата: {max_date.strftime("%d.%m.%Y")}'
            )
        
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        time_from = cleaned_data.get('preferred_time_from')
        time_to = cleaned_data.get('preferred_time_to')
        
        if time_from and time_to:
            # Рабочее время с 8:00 до 20:00
            if time_from < time(8, 0) or time_to > time(20, 0):
                raise forms.ValidationError(
                    'Время должно быть в пределах рабочего дня (08:00 - 20:00)'
                )
            
            if time_from >= time_to:
                raise forms.ValidationError(
                    'Время "до" должно быть позже времени "с"'
                )
            
            # Минимальное окно 2 часа
            from datetime import datetime, date
            dt_from = datetime.combine(date.today(), time_from)
            dt_to = datetime.combine(date.today(), time_to)
            if (dt_to - dt_from).seconds < 7200:  # 2 часа
                raise forms.ValidationError(
                    'Минимальное временное окно: 2 часа'
                )
        
        return cleaned_data


class QuickServiceRequestForm(forms.Form):
    """Быстрая форма вызова мастера (для модального окна)."""
    
    service = forms.ModelChoiceField(
        queryset=None,
        label='Услуга',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (XXX) XXX-XX-XX'
        })
    )
    description = forms.CharField(
        label='Описание проблемы',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Опишите вашу проблему...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        from .models import Service
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.filter(is_active=True)