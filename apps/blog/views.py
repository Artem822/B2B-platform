from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Post, BlogCategory, Tag, Comment
from .forms import CommentForm


class PostListView(ListView):
    """Список статей блога."""
    
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Post.objects.filter(status='published').select_related(
            'category', 'author'
        ).prefetch_related('tags')
        
        # Поиск
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(excerpt__icontains=search)
            )
        
        # Категория
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Тег
        tag = self.request.GET.get('tag')
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = BlogCategory.objects.all()
        context['tags'] = Tag.objects.all()[:20]
        context['featured_posts'] = Post.objects.filter(
            status='published', is_featured=True
        )[:3]
        context['current_category'] = self.request.GET.get('category')
        context['current_tag'] = self.request.GET.get('tag')
        return context


class PostDetailView(DetailView):
    """Детальная страница статьи."""
    
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        return Post.objects.filter(status='published').select_related(
            'category', 'author'
        ).prefetch_related('tags')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.increment_views()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Комментарии
        context['comments'] = self.object.comments.filter(
            is_approved=True, parent=None
        ).select_related('user').prefetch_related('replies__user')
        
        # Форма комментария
        context['comment_form'] = CommentForm()
        
        # Похожие статьи
        context['related_posts'] = Post.objects.filter(
            status='published',
            category=self.object.category
        ).exclude(pk=self.object.pk)[:4]
        
        return context


@login_required
def add_comment(request, slug):
    """Добавление комментария."""
    post = get_object_or_404(Post, slug=slug, status='published')
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user
            
            # Проверка на ответ
            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = Comment.objects.get(pk=parent_id)
            
            comment.save()
            messages.success(request, 'Комментарий добавлен!')
    
    return redirect('blog:post_detail', slug=slug)


@login_required
def delete_comment(request, pk):
    """Удаление своего комментария."""
    comment = get_object_or_404(Comment, pk=pk, user=request.user)
    post_slug = comment.post.slug
    comment.delete()
    messages.success(request, 'Комментарий удалён')
    return redirect('blog:post_detail', slug=post_slug)