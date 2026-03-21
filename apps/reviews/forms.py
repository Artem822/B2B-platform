from django import forms
from .models import Review, ReviewImage, ServiceReview


class ReviewForm(forms.ModelForm):
    """Форма отзыва о товаре."""
    
    class Meta:
        model = Review
        fields = ['rating', 'title', 'content', 'quality_rating', 
                  'value_rating', 'pros', 'cons']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'quality_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'value_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'pros': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'cons': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ReviewImageForm(forms.ModelForm):
    """Форма загрузки фото к отзыву."""
    
    class Meta:
        model = ReviewImage
        fields = ['image']


class ServiceReviewForm(forms.ModelForm):
    """Форма отзыва об услуге."""
    
    class Meta:
        model = ServiceReview
        fields = ['rating', 'content', 'quality_rating', 
                  'punctuality_rating', 'communication_rating']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'quality_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'punctuality_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'communication_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }