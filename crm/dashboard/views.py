from django.views.generic import TemplateView, ListView, DetailView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json

from .models import BotUser, Lead, SearchLog, UserFeedback, FavoriteProperty
from properties.models import BIComplex, BIUnit, SecondaryProperty


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Требует авторизации и прав staff"""
    login_url = '/crm/login/'

    def test_func(self):
        return self.request.user.is_staff


# ─────────────── AUTH ───────────────

class CRMLoginView(LoginView):
    template_name = 'crm/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/crm/'


# ─────────────── DASHBOARD ───────────────

class DashboardIndexView(StaffRequiredMixin, TemplateView):
    """Главная страница дашборда"""
    template_name = 'crm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # ── Ключевые метрики ──
        context['stats'] = {
            'new_leads': Lead.objects.filter(status='new').count(),
            'leads_today': Lead.objects.filter(created_at__date=today).count(),
            'active_properties': SecondaryProperty.objects.filter(is_active=True).count(),
            'total_users': BotUser.objects.count(),
            'users_today': BotUser.objects.filter(created_at__date=today).count(),
            'bi_complexes': BIComplex.objects.count(),
            'bi_units': BIUnit.objects.filter(is_active=True).count(),
            'total_searches': SearchLog.objects.count(),
            'avg_rating': UserFeedback.objects.filter(
                rating__isnull=False
            ).aggregate(avg=Avg('rating'))['avg'] or 0,
        }

        # ── Лиды за последние 7 дней (для графика) ──
        leads_chart = []
        for i in range(7):
            day = (week_ago + timedelta(days=i)).date()
            leads_chart.append({
                'date': day.strftime('%d.%m'),
                'count': Lead.objects.filter(created_at__date=day).count(),
                'new': Lead.objects.filter(created_at__date=day, status='new').count(),
            })
        context['leads_chart'] = json.dumps(leads_chart)

        # ── Пользователи по платформам ──
        context['platform_stats'] = list(
            BotUser.objects.values('platform').annotate(count=Count('id')).order_by('-count')
        )
        context['platform_stats_json'] = json.dumps(
            [{'platform': p['platform'], 'count': p['count']} for p in context['platform_stats']]
        )

        # ── Распределение лидов по статусам ──
        lead_statuses = {}
        for status, label in Lead.STATUS_CHOICES:
            lead_statuses[label] = Lead.objects.filter(status=status).count()
        context['lead_status_json'] = json.dumps(lead_statuses)

        # ── Последние лиды ──
        context['recent_leads'] = Lead.objects.select_related('user').order_by('-created_at')[:8]

        # ── Последние пользователи ──
        context['recent_users'] = BotUser.objects.order_by('-created_at')[:5]

        # ── Топ городов по поискам ──
        context['top_cities'] = list(
            SearchLog.objects.exclude(detected_city=None).exclude(detected_city='')
            .values('detected_city').annotate(count=Count('id')).order_by('-count')[:5]
        )

        return context


# ─────────────── LEADS ───────────────

class LeadListView(StaffRequiredMixin, ListView):
    """Список лидов с фильтрацией и поиском"""
    model = Lead
    template_name = 'crm/leads/list.html'
    context_object_name = 'leads'
    paginate_by = 20

    def get_queryset(self):
        qs = Lead.objects.select_related('user').order_by('-priority', '-created_at')
        status = self.request.GET.get('status')
        search = self.request.GET.get('q')
        priority = self.request.GET.get('priority')

        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if search:
            qs = qs.filter(
                Q(user__name__icontains=search) |
                Q(user__user_id__icontains=search) |
                Q(request_text__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Lead.STATUS_CHOICES
        ctx['priority_choices'] = Lead.PRIORITY_CHOICES
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['current_priority'] = self.request.GET.get('priority', '')
        ctx['search_query'] = self.request.GET.get('q', '')

        # Счетчики по статусам
        ctx['status_counts'] = {}
        for status, _ in Lead.STATUS_CHOICES:
            ctx['status_counts'][status] = Lead.objects.filter(status=status).count()
        return ctx


class LeadDetailView(StaffRequiredMixin, DetailView):
    model = Lead
    template_name = 'crm/leads/detail.html'
    context_object_name = 'lead'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user_leads'] = Lead.objects.filter(
            user=self.object.user
        ).exclude(pk=self.object.pk).order_by('-created_at')[:5]
        return ctx


class LeadStatusUpdateView(StaffRequiredMixin, View):
    """AJAX обновление статуса лида"""

    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        data = json.loads(request.body) if request.body else {}
        new_status = data.get('status') or request.POST.get('status')

        if new_status in dict(Lead.STATUS_CHOICES):
            lead.status = new_status
            if new_status == 'contacted':
                lead.contacted_at = timezone.now()
            elif new_status == 'closed':
                lead.closed_at = timezone.now()
            notes = data.get('notes') or request.POST.get('notes', '')
            if notes:
                lead.manager_notes = notes
            manager = data.get('assigned_to') or request.POST.get('assigned_to', '')
            if manager:
                lead.assigned_to = manager
            lead.save()
            return JsonResponse({
                'success': True,
                'status': lead.status,
                'status_display': lead.get_status_display()
            })

        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)


# ─────────────── USERS ───────────────

class UserListView(StaffRequiredMixin, ListView):
    model = BotUser
    template_name = 'crm/users/list.html'
    context_object_name = 'users'
    paginate_by = 30

    def get_queryset(self):
        qs = BotUser.objects.order_by('-last_active_at')
        platform = self.request.GET.get('platform')
        search = self.request.GET.get('q')
        if platform:
            qs = qs.filter(platform=platform)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(user_id__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['platform_choices'] = BotUser.PLATFORM_CHOICES
        ctx['current_platform'] = self.request.GET.get('platform', '')
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['platform_counts'] = {}
        for p, _ in BotUser.PLATFORM_CHOICES:
            ctx['platform_counts'][p] = BotUser.objects.filter(platform=p).count()
        return ctx


class UserDetailView(StaffRequiredMixin, DetailView):
    model = BotUser
    template_name = 'crm/users/detail.html'
    context_object_name = 'bot_user'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user_leads'] = Lead.objects.filter(user=self.object).order_by('-created_at')[:10]
        ctx['user_searches'] = SearchLog.objects.filter(user=self.object).order_by('-created_at')[:10]
        ctx['user_favorites'] = FavoriteProperty.objects.filter(user=self.object).order_by('-created_at')[:10]
        return ctx


# ─────────────── ANALYTICS ───────────────

class AnalyticsView(StaffRequiredMixin, TemplateView):
    template_name = 'crm/analytics.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()

        # Лиды за 30 дней
        leads_30 = []
        for i in range(30):
            day = (now - timedelta(days=29 - i)).date()
            leads_30.append({
                'date': day.strftime('%d.%m'),
                'count': Lead.objects.filter(created_at__date=day).count()
            })
        ctx['leads_30_json'] = json.dumps(leads_30)

        # Поиски по городам
        ctx['searches_by_city'] = list(
            SearchLog.objects.exclude(detected_city=None).exclude(detected_city='')
            .values('detected_city').annotate(count=Count('id')).order_by('-count')[:10]
        )

        # Конверсия лидов
        total_leads = Lead.objects.count()
        closed_leads = Lead.objects.filter(status='closed').count()
        ctx['conversion_rate'] = round((closed_leads / total_leads * 100) if total_leads > 0 else 0, 1)
        ctx['total_leads'] = total_leads
        ctx['closed_leads'] = closed_leads

        # Рейтинги
        ctx['avg_rating'] = UserFeedback.objects.filter(
            rating__isnull=False
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        ctx['feedback_count'] = UserFeedback.objects.count()

        return ctx
