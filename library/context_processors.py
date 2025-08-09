from django.conf import settings

def library_settings(request):
    """
    Kütüphane ayarlarını template'lerde kullanılabilir hale getirir
    """
    return {
        'LIBRARY_SETTINGS': getattr(settings, 'LIBRARY_SETTINGS', {}),
        'LIBRARY_NAME': getattr(settings, 'LIBRARY_SETTINGS', {}).get('LIBRARY_NAME', 'Kütüphane'),
    }
