from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import Address

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Форма регистрации пользователя."""
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
    )
    first_name = forms.CharField(
        label='Имя',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя'})
    )
    last_name = forms.CharField(
        label='Фамилия',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите фамилию'})
    )
    phone = forms.CharField(
        label='Телефон',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (XXX) XXX-XX-XX'})
    )
    company_name = forms.CharField(
        label='Название компании',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ООО "Название"'})
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'})
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'})
    )
    agree_terms = forms.BooleanField(
        label='Я согласен с условиями использования',
        required=True
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'company_name', 'password1', 'password2']


class CustomAuthenticationForm(AuthenticationForm):
    """Форма входа."""
    
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'})
    )


class ProfileForm(forms.ModelForm):
    """Форма редактирования профиля."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'company_name', 'inn', 'kpp', 
                  'legal_address', 'actual_address', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'inn': forms.TextInput(attrs={'class': 'form-control'}),
            'kpp': forms.TextInput(attrs={'class': 'form-control'}),
            'legal_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'actual_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AddressForm(forms.ModelForm):
    """Форма адреса доставки."""
    
    class Meta:
        model = Address
        fields = ['title', 'city', 'street', 'building', 'office', 'postal_code', 'is_default']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'office': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PasswordResetRequestForm(forms.Form):
    """Форма запроса сброса пароля."""
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email не найден')
        return email