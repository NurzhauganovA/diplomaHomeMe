from django.contrib import admin
from .models import BotUser, UserSession, Lead, SearchLog, UserFeedback, FavoriteProperty


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'user_id', 'total_messages', 'total_searches', 'last_active_at']
    list_filter = ['platform', 'is_active', 'language']
    search_fields = ['name', 'user_id', 'email', 'phone']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'priority', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['user__name', 'request_text', 'assigned_to']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['query_text', 'user', 'detected_city', 'results_count', 'created_at']
    list_filter = ['detected_city', 'detected_intent']
    readonly_fields = ['created_at']


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'feedback_type', 'rating', 'created_at']
    list_filter = ['feedback_type', 'rating']


admin.site.register(UserSession)
admin.site.register(FavoriteProperty)
