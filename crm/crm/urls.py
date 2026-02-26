from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('crm/', include('dashboard.urls', namespace='crm')),
    path('', include('properties.urls', namespace='properties')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
