from django.contrib import admin
from .models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    readonly_fields = ('role', 'content', 'created_at')
    extra = 0


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'created_at', 'updated_at')
    inlines = [ChatMessageInline]
