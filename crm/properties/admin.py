from django.contrib import admin
from .models import BIComplex, BIUnit, BICommercialComplex, BICommercialUnit, SecondaryProperty


@admin.register(BIComplex)
class BIComplexAdmin(admin.ModelAdmin):
    list_display = ['name', 'class_name', 'deadline', 'min_price', 'updated_at']
    search_fields = ['name', 'address']
    list_filter = ['class_name']


@admin.register(BIUnit)
class BIUnitAdmin(admin.ModelAdmin):
    list_display = ['complex', 'room_count', 'area', 'floor', 'price', 'is_active']
    list_filter = ['is_active', 'room_count']
    search_fields = ['complex__name']


@admin.register(BICommercialComplex)
class BICommercialComplexAdmin(admin.ModelAdmin):
    list_display = ['name', 'class_name', 'deadline', 'min_price', 'updated_at']
    search_fields = ['name', 'address']


@admin.register(BICommercialUnit)
class BICommercialUnitAdmin(admin.ModelAdmin):
    list_display = ['complex', 'area', 'floor', 'price', 'is_active']
    list_filter = ['is_active']


@admin.register(SecondaryProperty)
class SecondaryPropertyAdmin(admin.ModelAdmin):
    list_display = ['title', 'city', 'rooms', 'area', 'price', 'is_active', 'created_at']
    list_filter = ['is_active', 'city', 'rooms', 'has_renovation']
    search_fields = ['title', 'address', 'description']
