from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'crm'

urlpatterns = [
    # Auth
    path('login/', views.CRMLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='/crm/login/'), name='logout'),

    # Dashboard
    path('', views.DashboardIndexView.as_view(), name='dashboard'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),

    # Leads
    path('leads/', views.LeadListView.as_view(), name='lead_list'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('leads/<int:pk>/status/', views.LeadStatusUpdateView.as_view(), name='lead_status'),

    # Users
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user_detail'),
]
