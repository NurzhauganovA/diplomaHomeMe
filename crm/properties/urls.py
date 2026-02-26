from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    # Home
    path('', views.HomeView.as_view(), name='home'),

    # ЖК BI Group
    path('complexes/', views.ComplexListView.as_view(), name='complex_list'),
    path('complexes/<uuid:pk>/', views.ComplexDetailView.as_view(), name='complex_detail'),

    # Вторичная недвижимость
    path('secondary/', views.SecondaryListView.as_view(), name='secondary_list'),
    path('secondary/<uuid:pk>/', views.SecondaryDetailView.as_view(), name='secondary_detail'),
]
