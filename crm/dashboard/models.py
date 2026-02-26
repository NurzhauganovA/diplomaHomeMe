"""
HomeMe CRM - Dashboard Models
Модели для CRM: пользователи, лиды, сессии, аналитика.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class BotUser(models.Model):
    """Унифицированный пользователь для всех платформ (Telegram, WhatsApp, Web)."""

    PLATFORM_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('web', 'Web'),
    ]

    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('kk', 'Қазақ'),
        ('en', 'English'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    user_id = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text="Phone for WhatsApp, ID for Telegram, email/uuid for Web"
    )
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active_at = models.DateTimeField(auto_now=True)
    total_searches = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    language = models.CharField(max_length=5, default='ru', choices=LANGUAGE_CHOICES)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['platform', 'user_id']),
            models.Index(fields=['last_active_at']),
        ]

    def __str__(self):
        return f"{self.name or 'Anonymous'} ({self.platform})"

    def increment_searches(self):
        self.total_searches += 1
        self.save(update_fields=['total_searches'])

    def increment_messages(self):
        self.total_messages += 1
        self.last_active_at = timezone.now()
        self.save(update_fields=['total_messages', 'last_active_at'])


class UserSession(models.Model):
    """Сессия пользователя - хранит контекст диалога."""

    user = models.OneToOneField(BotUser, on_delete=models.CASCADE, related_name='session')
    current_intent = models.CharField(
        max_length=50, default='greeting',
        help_text="Текущее намерение: greeting, search_objects, consult_location и т.д."
    )
    search_params = models.JSONField(default=dict, blank=True)
    conversation_history = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=50, default='START')

    class Meta:
        verbose_name = "Сессия пользователя"
        verbose_name_plural = "Сессии пользователей"

    def __str__(self):
        return f"Session of {self.user.name} ({self.current_intent})"

    def add_message_to_history(self, role: str, content: str):
        if not isinstance(self.conversation_history, list):
            self.conversation_history = []
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": timezone.now().isoformat()
        })
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        self.save(update_fields=['conversation_history', 'updated_at'])


class Lead(models.Model):
    """Лид - запрос на связь с экспертом."""

    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('contacted', 'Связались'),
        ('closed', 'Закрыт'),
        ('cancelled', 'Отменен'),
    ]

    PRIORITY_CHOICES = [
        (0, 'Обычный'),
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
        (4, 'Срочный'),
        (5, 'Критический'),
    ]

    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='leads')
    request_text = models.TextField("Текст запроса")
    search_params = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    assigned_to = models.CharField(max_length=100, null=True, blank=True)
    manager_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    contacted_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(
        default=0, choices=PRIORITY_CHOICES,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    class Meta:
        verbose_name = "Лид"
        verbose_name_plural = "Лиды"
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['-priority', '-created_at']),
        ]

    def __str__(self):
        return f"Lead #{self.id} from {self.user.name} ({self.status})"

    def mark_as_contacted(self, manager_name: str = None):
        self.status = 'contacted'
        self.contacted_at = timezone.now()
        if manager_name:
            self.assigned_to = manager_name
        self.save()

    def close(self, notes: str = ""):
        self.status = 'closed'
        self.closed_at = timezone.now()
        if notes:
            self.manager_notes = notes
        self.save()


class SearchLog(models.Model):
    """Лог поисковых запросов для аналитики."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, related_name='search_logs')
    query_text = models.TextField("Текст запроса")
    detected_intent = models.CharField("Обнаруженное намерение", max_length=50, blank=True)
    detected_city = models.CharField("Город", max_length=50, null=True, blank=True)
    detected_district = models.CharField("Район", max_length=100, null=True, blank=True)
    results_count = models.IntegerField("Количество результатов", default=0)
    search_duration_ms = models.IntegerField("Время поиска (мс)", default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Лог поиска"
        verbose_name_plural = "Логи поиска"
        ordering = ['-created_at']

    def __str__(self):
        return f"Search: {self.query_text[:50]} ({self.results_count} results)"


class UserFeedback(models.Model):
    """Обратная связь от пользователей."""

    FEEDBACK_TYPE_CHOICES = [
        ('property', 'По объекту'),
        ('bot', 'По работе бота'),
        ('search', 'По поиску'),
        ('other', 'Другое'),
    ]

    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='feedbacks')
    feedback_type = models.CharField("Тип", max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    rating = models.IntegerField("Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)],
                                  null=True, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    property_id = models.CharField("ID объекта", max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback from {self.user.name}: {self.rating}⭐"


class FavoriteProperty(models.Model):
    """Избранные объекты пользователя."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='favorites')
    source = models.CharField(max_length=20, db_index=True)
    object_kind = models.CharField(max_length=20, db_index=True)
    object_id = models.CharField(max_length=100, db_index=True)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Избранный объект"
        verbose_name_plural = "Избранные объекты"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'object_kind', 'object_id'],
                name='unique_favorite_object'
            ),
        ]

    def __str__(self):
        return f"Favorite {self.object_kind}:{self.object_id} ({self.user.name})"
