from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('backup/', views.BackupView.as_view(), name='backup'),
    path('shelf-map/', views.ShelfMapView.as_view(), name='shelf_map'),
    path('site-map/', views.SiteMapView.as_view(), name='site_map'),
    path('inventory/', views.InventoryView.as_view(), name='inventory'),
    path('mobile-app/', views.MobileAppView.as_view(), name='mobile_app'),
]
