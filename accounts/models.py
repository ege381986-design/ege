from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """
    Özel kullanıcı modeli - Flask User modeli Django'ya uyarlandı
    """
    ROLE_CHOICES = [
        ('admin', 'Yönetici'),
        ('librarian', 'Kütüphaneci'),
        ('user', 'Kullanıcı'),
    ]
    
    THEME_CHOICES = [
        ('light', 'Açık'),
        ('dark', 'Koyu'),
    ]
    
    LANGUAGE_CHOICES = [
        ('tr', 'Türkçe'),
        ('en', 'English'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name='Rol'
    )
    
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Son Giriş IP'
    )
    
    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default='light',
        verbose_name='Tema'
    )
    
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='tr',
        verbose_name='Dil'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Güncellenme Tarihi'
    )
    
    class Meta:
        verbose_name = 'Kullanıcı'
        verbose_name_plural = 'Kullanıcılar'
        db_table = 'users'
    
    def __str__(self):
        return self.username
    
    def has_role(self, role):
        """Kullanıcının belirtilen role sahip olup olmadığını kontrol eder"""
        return self.role == role
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_librarian(self):
        return self.role in ['admin', 'librarian']
    
    def get_full_display_name(self):
        """Tam adı döndürür, yoksa kullanıcı adını"""
        return self.get_full_name() or self.username


class Member(models.Model):
    """
    Kütüphane üyesi modeli - Flask Member modeli Django'ya uyarlandı
    """
    MEMBER_TYPE_CHOICES = [
        ('ogrenci', 'Öğrenci'),
        ('ogretmen', 'Öğretmen'),
        ('personel', 'Personel'),
        ('misafir', 'Misafir'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='member_profile',
        verbose_name='Kullanıcı'
    )
    
    ad_soyad = models.CharField(
        max_length=200,
        verbose_name='Ad Soyad'
    )
    
    sinif = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Sınıf'
    )
    
    numara = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Numara'
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name='E-posta'
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefon'
    )
    
    address = models.TextField(
        blank=True,
        verbose_name='Adres'
    )
    
    uye_turu = models.CharField(
        max_length=20,
        choices=MEMBER_TYPE_CHOICES,
        default='ogrenci',
        verbose_name='Üye Türü'
    )
    
    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        verbose_name='Profil Fotoğrafı'
    )
    
    join_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Üyelik Tarihi'
    )
    
    total_borrowed = models.IntegerField(
        default=0,
        verbose_name='Toplam Ödünç Alınan'
    )
    
    current_borrowed = models.IntegerField(
        default=0,
        verbose_name='Şu An Ödünç Alınan'
    )
    
    reliability_score = models.FloatField(
        default=100.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        verbose_name='Güvenilirlik Skoru'
    )
    
    penalty_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ceza Bitiş Tarihi'
    )
    
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Bildirim Tercihleri'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktif'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Güncellenme Tarihi'
    )
    
    class Meta:
        verbose_name = 'Üye'
        verbose_name_plural = 'Üyeler'
        db_table = 'members'
    
    def __str__(self):
        return f"{self.ad_soyad} ({self.get_uye_turu_display()})"
    
    def is_penalized(self):
        """Cezalı durumda olup olmadığını kontrol eder"""
        if self.penalty_until:
            return timezone.now() < self.penalty_until
        return False
    
    def can_borrow(self):
        """Ödünç alabilir durumda olup olmadığını kontrol eder"""
        from django.conf import settings
        
        if not self.is_active:
            return False, "Üyelik aktif değil"
        
        if self.is_penalized():
            return False, f"Cezalı durumda (bitiş: {self.penalty_until})"
        
        max_books = getattr(settings, 'LIBRARY_SETTINGS', {}).get('MAX_BOOKS_PER_MEMBER', 5)
        if self.current_borrowed >= max_books:
            return False, f"Maksimum kitap limitine ulaşıldı ({max_books})"
        
        return True, "Ödünç alabilir"
    
    def get_borrowable_count(self):
        """Kaç kitap daha ödünç alabileceğini döndürür"""
        from django.conf import settings
        max_books = getattr(settings, 'LIBRARY_SETTINGS', {}).get('MAX_BOOKS_PER_MEMBER', 5)
        return max(0, max_books - self.current_borrowed)


class ActivityLog(models.Model):
    """
    Kullanıcı aktivite logu
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Kullanıcı'
    )
    
    action = models.CharField(
        max_length=100,
        verbose_name='İşlem'
    )
    
    details = models.TextField(
        blank=True,
        verbose_name='Detaylar'
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP Adresi'
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name='Tarayıcı Bilgisi'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Zaman'
    )
    
    class Meta:
        verbose_name = 'Aktivite Logu'
        verbose_name_plural = 'Aktivite Logları'
        db_table = 'activity_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"


class QRCode(models.Model):
    """
    QR kod modeli - Flask QRCode modeli Django'ya uyarlandı
    """
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('used', 'Kullanıldı'),
        ('expired', 'Süresi Doldu'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='qr_codes',
        verbose_name='Kullanıcı'
    )
    
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Token'
    )
    
    expiry_time = models.DateTimeField(
        verbose_name='Son Kullanma Tarihi'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Durum'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Kullanılma Tarihi'
    )
    
    class Meta:
        verbose_name = 'QR Kod'
        verbose_name_plural = 'QR Kodları'
        db_table = 'qrcodes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.token[:8]}..."
    
    def is_valid(self):
        """QR kodun geçerli olup olmadığını kontrol eder"""
        return (
            self.status == 'active' and 
            timezone.now() < self.expiry_time
        )
    
    def use(self):
        """QR kodu kullanıldı olarak işaretler"""
        self.status = 'used'
        self.used_at = timezone.now()
        self.save()
