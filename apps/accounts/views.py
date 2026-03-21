from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, ListView
from django.urls import reverse_lazy
from django.http import JsonResponse

from .models import User, Address, Notification
from .forms import (CustomUserCreationForm, CustomAuthenticationForm, 
                    ProfileForm, AddressForm, PasswordResetRequestForm)


class RegisterView(CreateView):
    """Регистрация пользователя."""
    
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Регистрация успешна! Теперь вы можете войти.')
        return response


def login_view(request):
    """Вход пользователя."""
    if request.user.is_authenticated:
        return redirect('products:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.full_name}!')
            next_url = request.GET.get('next', 'products:home')
            return redirect(next_url)
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Выход пользователя."""
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('products:home')


@login_required
def profile_view(request):
    """Просмотр и редактирование профиля."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    
    addresses = request.user.addresses.all()
    notifications = request.user.notifications.filter(is_read=False)[:5]
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'addresses': addresses,
        'notifications': notifications,
    })


@login_required
def address_list(request):
    """Список адресов пользователя."""
    addresses = request.user.addresses.all()
    return render(request, 'accounts/address_list.html', {'addresses': addresses})


@login_required
def address_create(request):
    """Создание адреса."""
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Адрес добавлен.')
            return redirect('accounts:address_list')
    else:
        form = AddressForm()
    
    return render(request, 'accounts/address_form.html', {'form': form})


@login_required
def address_edit(request, pk):
    """Редактирование адреса."""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Адрес обновлён.')
            return redirect('accounts:address_list')
    else:
        form = AddressForm(instance=address)
    
    return render(request, 'accounts/address_form.html', {'form': form, 'address': address})


@login_required
def address_delete(request, pk):
    """Удаление адреса."""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Адрес удалён.')
    return redirect('accounts:address_list')


@login_required
def notifications_view(request):
    """Список уведомлений."""
    notifications = request.user.notifications.all()
    return render(request, 'accounts/notifications.html', {'notifications': notifications})


@login_required
def notification_mark_read(request, pk):
    """Отметить уведомление как прочитанное."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('accounts:notifications')


@login_required
def mark_all_notifications_read(request):
    """Отметить все уведомления как прочитанные."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'Все уведомления отмечены как прочитанные.')
    return redirect('accounts:notifications')


class CustomPasswordResetView(PasswordResetView):
    """Сброс пароля."""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Подтверждение сброса пароля."""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')