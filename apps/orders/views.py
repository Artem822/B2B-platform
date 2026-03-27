from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import Order, OrderItem, OrderStatusHistory
from .forms import CartAddForm, CheckoutForm
from apps.products.models import Product
from apps.products.cart import Cart
from apps.promotions.models import PromoCode
from apps.accounts.models import Notification


def _get_valid_promo_from_session(request, cart_total):
    """Получить валидный промокод из сессии и рассчитанную скидку."""
    code = request.session.get('promo_code')
    if not code:
        return None, Decimal('0')
    
    try:
        promo = PromoCode.objects.get(code__iexact=code)
        if promo.is_valid():
            return promo, promo.calculate_discount(cart_total)
    except PromoCode.DoesNotExist:
        pass
    
    request.session.pop('promo_code', None)
    return None, Decimal('0')


def cart_view(request):
    """Просмотр корзины."""
    cart = Cart(request)
    
    for item in cart:
        item['update_form'] = CartAddForm(initial={
            'quantity': item['quantity'],
        })
    
    total_price = cart.get_total_price()
    free_delivery_remaining = max(Decimal('0'), Decimal('50000') - total_price)

    promo_code, discount = _get_valid_promo_from_session(request, total_price)

    return render(request, 'orders/cart.html', {
        'cart': cart,
        'free_delivery_remaining': free_delivery_remaining,
        'promo_code': promo_code,
        'discount': discount,
    })


@require_POST
def cart_add(request, product_id):
    """Добавление товара в корзину."""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    form = CartAddForm(request.POST)
    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        
        # Проверка наличия
        if quantity > product.available_stock:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Доступно только {product.available_stock} шт.'
                })
            messages.error(request, f'Доступно только {product.available_stock} шт.')
            return redirect(product.get_absolute_url())
        
        cart.add(product=product, quantity=quantity)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Товар добавлен в корзину',
                'cart_total': len(cart),
            })
        
        messages.success(request, 'Товар добавлен в корзину')
    
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))


@require_POST
def cart_update(request, product_id):
    """Обновление количества товара в корзине."""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    form = CartAddForm(request.POST)
    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        
        if quantity > product.available_stock:
            messages.error(request, f'Доступно только {product.available_stock} шт.')
            return redirect('orders:cart')
        
        cart.add(product=product, quantity=quantity, update_quantity=True)
        messages.success(request, 'Корзина обновлена')
    
    return redirect('orders:cart')


@require_POST
def cart_remove(request, product_id):
    """Удаление товара из корзины."""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.success(request, 'Товар удалён из корзины')
    return redirect('orders:cart')


@require_POST
def apply_promo(request):
    """Применение промокода (из корзины или чекаута)."""
    code = request.POST.get('code', '').strip()
    referer = request.META.get('HTTP_REFERER', '')

    if not code:
        messages.error(request, 'Введите промокод')
        request.session.pop('promo_code', None)
    else:
        try:
            promo = PromoCode.objects.get(code__iexact=code)
            if promo.is_valid():
                cart = Cart(request)
                total = cart.get_total_price()
                discount = promo.calculate_discount(total)
                if discount <= 0:
                    request.session.pop('promo_code', None)
                    if promo.min_order_amount and total < promo.min_order_amount:
                        messages.warning(
                            request,
                            f'Промокод действует при заказе от {promo.min_order_amount:,.0f} ₽. '
                            f'Сумма корзины: {total:,.0f} ₽'.replace(',', ' ')
                        )
                    else:
                        messages.error(request, 'Промокод не применим к данному заказу')
                else:
                    request.session['promo_code'] = promo.code
                    messages.success(request, f'Промокод применён! Скидка: {discount:,.0f} ₽'.replace(',', ' '))
            else:
                request.session.pop('promo_code', None)
                messages.error(request, 'Промокод недействителен или истёк')
        except PromoCode.DoesNotExist:
            request.session.pop('promo_code', None)
            messages.error(request, 'Промокод не найден')

    if 'checkout' in referer:
        return redirect('orders:checkout')
    return redirect('orders:cart')


@login_required
def checkout(request):
    """Оформление заказа."""
    cart = Cart(request)
    
    if len(cart) == 0:
        messages.warning(request, 'Ваша корзина пуста')
        return redirect('orders:cart')
    
    # Проверяем наличие всех товаров
    for item in cart:
        product = item['product']
        if item['quantity'] > product.available_stock:
            messages.error(
                request, 
                f'Товар "{product.name}" недоступен в нужном количестве. '
                f'Доступно: {product.available_stock} шт.'
            )
            return redirect('orders:cart')
    
    promo_code = None
    discount = Decimal('0')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)

        # Оформление заказа
        if form.is_valid():
            with transaction.atomic():
                subtotal = cart.get_total_price()
                promo_code, discount = _get_valid_promo_from_session(request, subtotal)
                
                # Рассчитываем стоимость доставки
                delivery_cost = Decimal('0')
                if subtotal < 50000:
                    delivery_cost = Decimal('500')
                
                # Рассчитываем стоимость установки
                installation_cost = Decimal('0')
                if form.cleaned_data['include_installation']:
                    installation_cost = subtotal * Decimal('0.05')  # 5% от суммы
                
                # Создаём заказ
                order = form.save(commit=False)
                order.user = request.user
                order.subtotal = subtotal
                order.discount = discount
                order.delivery_cost = delivery_cost
                order.installation_cost = installation_cost
                order.promo_code = promo_code
                order.calculate_total()
                order.save()
                
                # Добавляем позиции заказа
                for item in cart:
                    product = item['product']
                    
                    # Резервируем товар
                    if not product.reserve_stock(item['quantity']):
                        raise Exception(f'Недостаточно товара "{product.name}" на складе')
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item['quantity'],
                        price=item['price'],
                    )
                
                # Увеличиваем счётчик использований промокода
                if promo_code:
                    promo_code.times_used += 1
                    promo_code.save()
                
                # Записываем историю
                OrderStatusHistory.objects.create(
                    order=order,
                    new_status='pending',
                    changed_by=request.user,
                    comment='Заказ создан'
                )
                
                # Уведомление
                Notification.objects.create(
                    user=request.user,
                    type='order',
                    title='Заказ оформлен',
                    message=f'Ваш заказ #{order.order_number} успешно оформлен.'
                )
                
                # Очищаем корзину
                cart.clear()
                request.session.pop('promo_code', None)
                
                messages.success(request, f'Заказ #{order.order_number} успешно оформлен!')
                return redirect('orders:order_detail', order_number=order.order_number)
        else:
            promo_code, discount = _get_valid_promo_from_session(request, cart.get_total_price())
    else:
        # Предзаполняем форму данными пользователя
        initial = {
            'contact_name': request.user.full_name,
            'contact_phone': request.user.phone,
            'contact_email': request.user.email,
        }
        
        # Если есть адрес по умолчанию
        default_address = request.user.addresses.filter(is_default=True).first()
        if default_address:
            initial.update({
                'delivery_city': default_address.city,
                'delivery_address': f"{default_address.street}, {default_address.building}",
                'delivery_postal_code': default_address.postal_code,
            })
        
        form = CheckoutForm(initial=initial)
        promo_code, discount = _get_valid_promo_from_session(request, cart.get_total_price())

    # Расчёт стоимости
    subtotal = cart.get_total_price()
    delivery_cost = Decimal('0') if subtotal >= 50000 else Decimal('500')

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'subtotal': subtotal,
        'delivery_cost': delivery_cost,
        'discount': discount,
        'promo_code': promo_code,
        'total': subtotal + delivery_cost - discount,
    })


@login_required
def order_list(request):
    """Список заказов пользователя."""
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    
    # Фильтр по статусу
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'current_status': status,
    })


@login_required
def order_detail(request, order_number):
    """Детали заказа."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'status_history'),
        order_number=order_number,
        user=request.user
    )
    
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
@require_POST
def order_cancel(request, order_number):
    """Отмена заказа."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if not order.can_be_cancelled():
        messages.error(request, 'Этот заказ не может быть отменён')
        return redirect('orders:order_detail', order_number=order_number)
    
    reason = request.POST.get('reason', '')
    old_status = order.status
    
    if order.cancel(reason):
        # Записываем историю
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status='cancelled',
            changed_by=request.user,
            comment=f'Отменён клиентом. {reason}'
        )
        
        # Уведомление
        Notification.objects.create(
            user=request.user,
            type='order',
            title='Заказ отменён',
            message=f'Ваш заказ #{order.order_number} был отменён.'
        )
        
        messages.success(request, 'Заказ успешно отменён. Товары возвращены на склад.')
    else:
        messages.error(request, 'Не удалось отменить заказ')
    
    return redirect('orders:order_detail', order_number=order_number)


@login_required
def order_repeat(request, order_number):
    """Повторить заказ - добавить товары в корзину."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    cart = Cart(request)
    
    added_count = 0
    for item in order.items.all():
        if item.product.is_active and item.product.available_stock >= item.quantity:
            cart.add(product=item.product, quantity=item.quantity)
            added_count += 1
    
    if added_count > 0:
        messages.success(request, f'Добавлено {added_count} товар(ов) в корзину')
    else:
        messages.warning(request, 'Не удалось добавить товары. Возможно, они недоступны.')
    
    return redirect('orders:cart')






