from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    """Форма комментария."""
    
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Напишите комментарий...'
            })
        }