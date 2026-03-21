from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Review, ReviewImage, ReviewVote, ServiceReview
from .forms import ReviewForm, ReviewImageForm, ServiceReviewForm
from apps.products.models import Product
from apps.orders.models import Order, OrderItem
from apps.services.models import ServiceRequest


@login_required
def add_review(request, product_slug):
    """Добавление отзыва о товаре."""
    product = get_object_or_404(Product, slug=product_slug, is_active=True)
    
    # Проверяем, не оставлял ли уже отзыв
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.warning(request, 'Вы уже оставляли отзыв на этот товар')
        return redirect('products:product_detail', slug=product_slug)
    
    # Проверяем, покупал ли пользователь этот товар
    is_verified = OrderItem.objects.filter(
        order__user=request.user,
        order__status='completed',
        product=product
    ).exists()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.is_verified_purchase = is_verified
            review.save()
            
            # Загрузка фото
            for image in request.FILES.getlist('images'):
                ReviewImage.objects.create(review=review, image=image)
            
            messages.success(request, 'Спасибо за отзыв! Он появится после модерации.')
            return redirect('products:product_detail', slug=product_slug)
    else:
        form = ReviewForm()
    
    return render(request, 'reviews/add_review.html', {
        'form': form,
        'product': product,
        'is_verified': is_verified,
    })


@login_required
@require_POST
def vote_review(request, review_id):
    """Голосование за отзыв."""
    review = get_object_or_404(Review, pk=review_id)
    is_helpful = request.POST.get('helpful') == 'true'
    
    vote, created = ReviewVote.objects.get_or_create(
        review=review,
        user=request.user,
        defaults={'is_helpful': is_helpful}
    )
    
    if not created:
        if vote.is_helpful != is_helpful:
            vote.is_helpful = is_helpful
            vote.save()
    
    # Обновляем счётчики
    review.helpful_count = review.votes.filter(is_helpful=True).count()
    review.not_helpful_count = review.votes.filter(is_helpful=False).count()
    review.save()
    
    return JsonResponse({
        'helpful_count': review.helpful_count,
        'not_helpful_count': review.not_helpful_count,
    })


@login_required
def add_service_review(request, request_number):
    """Добавление отзыва об услуге."""
    service_request = get_object_or_404(
        ServiceRequest,
        request_number=request_number,
        user=request.user,
        status='completed'
    )
    
    if hasattr(service_request, 'review'):
        messages.warning(request, 'Вы уже оставляли отзыв на эту услугу')
        return redirect('services:request_detail', request_number=request_number)
    
    if request.method == 'POST':
        form = ServiceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.service_request = service_request
            review.technician = service_request.technician
            review.save()
            
            # Обновляем рейтинг мастера
            service_request.technician.update_rating()
            
            messages.success(request, 'Спасибо за отзыв!')
            return redirect('services:request_detail', request_number=request_number)
    else:
        form = ServiceReviewForm()
    
    return render(request, 'reviews/add_service_review.html', {
        'form': form,
        'service_request': service_request,
    })


def product_reviews(request, product_slug):
    """Все отзывы о товаре."""
    product = get_object_or_404(Product, slug=product_slug, is_active=True)
    
    reviews = Review.objects.filter(
        product=product,
        is_approved=True
    ).select_related('user').prefetch_related('images')
    
    # Сортировка
    sort = request.GET.get('sort', '-created_at')
    if sort == 'helpful':
        reviews = reviews.order_by('-helpful_count')
    elif sort == 'rating_high':
        reviews = reviews.order_by('-rating')
    elif sort == 'rating_low':
        reviews = reviews.order_by('rating')
    else:
        reviews = reviews.order_by('-created_at')
    
    # Фильтр по рейтингу
    rating = request.GET.get('rating')
    if rating:
        reviews = reviews.filter(rating=rating)
    
    return render(request, 'reviews/product_reviews.html', {
        'product': product,
        'reviews': reviews,
    })