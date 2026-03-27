from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Avg, Count, F
from django.contrib import messages
from django.core.paginator import Paginator

from .models import Product, Category, Brand, Wishlist
from apps.reviews.models import Review
from apps.blog.models import Post


class HomeView(ListView):
    """Главная страница."""
    
    model = Product
    template_name = 'products/home.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        return Product.objects.filter(
            is_active=True, 
            is_featured=True
        ).select_related('category', 'brand')[:8]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(
            is_active=True, parent=None
        ).annotate(
            products_count=Count('products') + Count('children__products')
        )[:6]
        context['new_products'] = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
        context['brands'] = Brand.objects.filter(is_active=True)[:12]
        context['testimonials'] = Review.objects.filter(
            is_approved=True
        ).select_related('user', 'product').order_by('-created_at')[:3]
        context['blog_posts'] = Post.objects.filter(
            status='published'
        ).select_related('author', 'category').order_by('-published_at', '-created_at')[:3]
        return context


class ProductListView(ListView):
    """Список товаров с фильтрацией."""
    
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category', 'brand')
        
        # Поиск
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(sku__icontains=search)
            )
        
        # Категория
        category_slug = self.request.GET.get('category')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            categories = [category] + category.get_all_children()
            queryset = queryset.filter(category__in=categories)
        
        # Бренд
        brand_slug = self.request.GET.get('brand')
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)
        
        # Цена
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # В наличии
        in_stock = self.request.GET.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(stock__gt=F('reserved'))
        
        # Состояние
        condition = self.request.GET.get('condition')
        if condition:
            queryset = queryset.filter(condition=condition)
        
        # Сортировка
        sort = self.request.GET.get('sort', '-created_at')
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'name':
            queryset = queryset.order_by('name')
        elif sort == 'popular':
            queryset = queryset.annotate(
                order_count=Count('order_items')
            ).order_by('-order_count')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True, parent=None)
        context['brands'] = Brand.objects.filter(is_active=True)
        context['current_category'] = self.request.GET.get('category')
        context['current_brand'] = self.request.GET.get('brand')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        return context


class ProductDetailView(DetailView):
    """Детальная страница товара."""
    
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category', 'brand')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Характеристики
        context['specifications'] = product.specifications.all()
        
        # Изображения
        context['images'] = product.images.all()
        
        # Отзывы
        context['reviews'] = Review.objects.filter(
            product=product, 
            is_approved=True
        ).select_related('user').order_by('-created_at')[:5]
        
        # Средний рейтинг
        context['avg_rating'] = Review.objects.filter(
            product=product, 
            is_approved=True
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Похожие товары
        context['related_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(pk=product.pk)[:4]
        
        # В избранном?
        if self.request.user.is_authenticated:
            context['in_wishlist'] = Wishlist.objects.filter(
                user=self.request.user, 
                product=product
            ).exists()
        
        return context


class CategoryView(ListView):
    """Страница категории."""
    
    model = Product
    template_name = 'products/category.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'], is_active=True)
        categories = [self.category] + self.category.get_all_children()
        return Product.objects.filter(
            category__in=categories,
            is_active=True
        ).select_related('category', 'brand')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['subcategories'] = self.category.children.filter(is_active=True)
        return context


@require_POST
@login_required
def toggle_wishlist(request, product_id):
    """Добавить/удалить из избранного."""
    product = get_object_or_404(Product, pk=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if not created:
        wishlist_item.delete()
        added = False
        message = 'Товар удалён из избранного'
    else:
        added = True
        message = 'Товар добавлен в избранное'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'added': added, 'message': message})
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))


@login_required
def wishlist_view(request):
    """Список избранного."""
    wishlist = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'products/wishlist.html', {'wishlist': wishlist})


def search_view(request):
    """Поиск товаров."""
    query = request.GET.get('q', '')
    products = Product.objects.none()
    
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query) |
            Q(brand__name__icontains=query),
            is_active=True
        ).select_related('category', 'brand')
    
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    return render(request, 'products/search.html', {
        'products': products,
        'query': query,
    })
