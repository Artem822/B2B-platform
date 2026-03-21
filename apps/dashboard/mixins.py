from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Миксин для проверки прав администратора."""
    
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_manager()
    
    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет доступа к этой странице')
        return redirect('products:home')


class TechnicianRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Миксин для проверки прав мастера."""
    
    def test_func(self):
        return (self.request.user.is_technician() or 
                self.request.user.is_admin() or 
                self.request.user.is_manager())
    
    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет доступа к этой странице')
        return redirect('products:home')