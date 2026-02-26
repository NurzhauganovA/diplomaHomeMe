from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q, Min, Max, Count
from django.shortcuts import get_object_or_404
from .models import BIComplex, BIUnit, BICommercialComplex, BICommercialUnit, SecondaryProperty


class HomeView(TemplateView):
    """Главная страница сайта"""
    template_name = 'site/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['featured_complexes'] = BIComplex.objects.order_by('-updated_at')[:6]
        ctx['recent_secondary'] = SecondaryProperty.objects.filter(is_active=True).order_by('-created_at')[:8]
        ctx['stats'] = {
            'complexes': BIComplex.objects.count(),
            'apartments': BIUnit.objects.filter(is_active=True).count(),
            'secondary': SecondaryProperty.objects.filter(is_active=True).count(),
        }
        return ctx


class ComplexListView(ListView):
    """Список ЖК BI Group"""
    model = BIComplex
    template_name = 'site/complexes/list.html'
    context_object_name = 'complexes'
    paginate_by = 12

    def get_queryset(self):
        qs = BIComplex.objects.annotate(
            units_count=Count('units', filter=Q(units__is_active=True))
        ).order_by('-updated_at')

        q = self.request.GET.get('q')
        class_name = self.request.GET.get('class')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q))
        if class_name:
            qs = qs.filter(class_name=class_name)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['class_choices'] = BIComplex.objects.values_list('class_name', flat=True).distinct()
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['current_class'] = self.request.GET.get('class', '')
        return ctx


class ComplexDetailView(DetailView):
    """Детальная страница ЖК"""
    model = BIComplex
    template_name = 'site/complexes/detail.html'
    context_object_name = 'complex'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        units = BIUnit.objects.filter(complex=self.object, is_active=True)
        ctx['units'] = units.order_by('price')[:20]
        ctx['units_count'] = units.count()
        agg = units.aggregate(
            min_price=Min('price_discount'),
            max_price=Max('price'),
            min_area=Min('area'),
            max_area=Max('area'),
        )
        ctx.update(agg)
        ctx['rooms_available'] = sorted(units.values_list('room_count', flat=True).distinct())
        return ctx


class SecondaryListView(ListView):
    """Список вторичной недвижимости"""
    model = SecondaryProperty
    template_name = 'site/secondary/list.html'
    context_object_name = 'properties'
    paginate_by = 12

    def get_queryset(self):
        qs = SecondaryProperty.objects.filter(is_active=True).order_by('-created_at')

        q = self.request.GET.get('q')
        city = self.request.GET.get('city')
        rooms = self.request.GET.get('rooms')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        deal_type = self.request.GET.get('deal_type')

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(address__icontains=q) | Q(description__icontains=q))
        if city:
            qs = qs.filter(city=city)
        if rooms:
            qs = qs.filter(rooms=rooms)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if deal_type:
            qs = qs.filter(deal_type=deal_type)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cities'] = SecondaryProperty.objects.filter(
            is_active=True, city__isnull=False
        ).values_list('city', flat=True).distinct().order_by('city')
        ctx['deal_types'] = SecondaryProperty.DEAL_TYPE_CHOICES
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['current_city'] = self.request.GET.get('city', '')
        ctx['current_rooms'] = self.request.GET.get('rooms', '')
        ctx['current_deal_type'] = self.request.GET.get('deal_type', '')
        return ctx


class SecondaryDetailView(DetailView):
    """Детальная страница объекта вторички"""
    model = SecondaryProperty
    template_name = 'site/secondary/detail.html'
    context_object_name = 'property'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.increment_views()
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Похожие объекты
        similar = SecondaryProperty.objects.filter(
            is_active=True,
            city=self.object.city,
            rooms=self.object.rooms,
        ).exclude(pk=self.object.pk)[:4]
        ctx['similar_properties'] = similar
        return ctx
