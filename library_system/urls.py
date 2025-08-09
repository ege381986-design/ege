"""
library_system URL Configuration
Cumhuriyet Anadolu Lisesi Kütüphane Yönetim Sistemi

Flask'tan Django'ya çevrilen ana URL yapılandırması
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from library import views as library_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Ana sayfa
    path('', library_views.IndexView.as_view(), name='index'),
    path('dashboard/', library_views.DashboardView.as_view(), name='dashboard'),
    
    # Accounts (kullanıcı yönetimi)
    path('accounts/', include('accounts.urls')),
    
    # Library (kütüphane ana işlemleri)
    path('library/', include('library.urls')),
    
    # Books (kitap yönetimi)
    path('books/', include('books.urls')),
    
    # Transactions (işlem yönetimi)  
    path('transactions/', include('transactions.urls')),
    
    # Notifications (bildirimler)
    path('notifications/', include('notifications.urls')),
    
    # API endpoints
    # path('api/v1/', include('library.api_urls')),
    
    # Favicon redirect
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico', permanent=True)),
]

# Static ve media dosyalar için URL patterns (development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site başlıkları
admin.site.site_header = 'Cumhuriyet Anadolu Lisesi Kütüphane Yönetim Sistemi'
admin.site.site_title = 'Kütüphane Admin'
admin.site.index_title = 'Kütüphane Yönetimi'
