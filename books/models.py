from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
import os


class Category(models.Model):
    """
    Kitap kategorileri - Flask Category modeli Django'ya uyarlandı
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Kategori Adı'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Açıklama'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    class Meta:
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategoriler'
        db_table = 'categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Book(models.Model):
    """
    Kitap modeli - Flask Book modeli Django'ya uyarlandı
    """
    isbn = models.CharField(
        max_length=20,
        primary_key=True,
        verbose_name='ISBN'
    )
    
    title = models.TextField(
        verbose_name='Başlık'
    )
    
    authors = models.TextField(
        verbose_name='Yazarlar'
    )
    
    publish_date = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Yayın Tarihi'
    )
    
    number_of_pages = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Sayfa Sayısı'
    )
    
    publishers = models.TextField(
        blank=True,
        verbose_name='Yayınevleri'
    )
    
    languages = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Diller'
    )
    
    quantity = models.IntegerField(
        default=1,
        verbose_name='Adet'
    )
    
    available_quantity = models.IntegerField(
        default=1,
        verbose_name='Mevcut Adet'
    )
    
    shelf = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Raf'
    )
    
    cupboard = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Dolap'
    )
    
    image_path = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Resim Yolu'
    )
    
    cover_image = models.ImageField(
        upload_to='book_covers/',
        blank=True,
        null=True,
        verbose_name='Kapak Resmi'
    )
    
    last_borrowed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Son Ödünç Alınma Tarihi'
    )
    
    total_borrow_count = models.IntegerField(
        default=0,
        verbose_name='Toplam Ödünç Alınma Sayısı'
    )
    
    qr_code = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='QR Kod Yolu'
    )
    
    barcode = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Barkod'
    )
    
    edition = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Basım'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Açıklama'
    )
    
    average_rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name='Ortalama Puan'
    )
    
    review_count = models.IntegerField(
        default=0,
        verbose_name='Değerlendirme Sayısı'
    )
    
    categories = models.ManyToManyField(
        Category,
        through='BookCategory',
        blank=True,
        verbose_name='Kategoriler'
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
        verbose_name = 'Kitap'
        verbose_name_plural = 'Kitaplar'
        db_table = 'books'
        ordering = ['title']
    
    def __str__(self):
        return f"{self.title} - {self.authors}"
    
    def get_absolute_url(self):
        return reverse('books:detail', kwargs={'isbn': self.isbn})
    
    def is_available(self):
        """Kitabın mevcut olup olmadığını kontrol eder"""
        return self.available_quantity > 0
    
    def can_borrow(self):
        """Kitabın ödünç alınabilir durumda olup olmadığını kontrol eder"""
        return self.is_available()
    
    def borrow(self):
        """Kitabı ödünç ver - mevcut adedi azalt"""
        if self.can_borrow():
            self.available_quantity -= 1
            self.total_borrow_count += 1
            self.last_borrowed_date = timezone.now()
            self.save()
            return True
        return False
    
    def return_book(self):
        """Kitabı iade et - mevcut adedi artır"""
        if self.available_quantity < self.quantity:
            self.available_quantity += 1
            self.save()
            return True
        return False
    
    def get_authors_list(self):
        """Yazarları liste olarak döndürür"""
        return [author.strip() for author in self.authors.split(',') if author.strip()]
    
    def get_publishers_list(self):
        """Yayınevlerini liste olarak döndürür"""
        if self.publishers:
            return [publisher.strip() for publisher in self.publishers.split(',') if publisher.strip()]
        return []
    
    def update_rating(self):
        """Kitabın ortalama puanını günceller"""
        reviews = self.reviews.all()
        if reviews:
            self.average_rating = reviews.aggregate(avg=models.Avg('rating'))['avg'] or 0.0
            self.review_count = reviews.count()
        else:
            self.average_rating = 0.0
            self.review_count = 0
        self.save()
    
    def get_qr_code_path(self):
        """QR kod dosya yolunu döndürür"""
        if self.qr_code:
            return self.qr_code
        return None
    
    def has_cover_image(self):
        """Kapak resminin olup olmadığını kontrol eder"""
        return bool(self.cover_image)


class BookCategory(models.Model):
    """
    Kitap-Kategori ilişkisi - Flask BookCategory modeli Django'ya uyarlandı
    """
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        verbose_name='Kitap'
    )
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name='Kategori'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    class Meta:
        verbose_name = 'Kitap Kategorisi'
        verbose_name_plural = 'Kitap Kategorileri'
        db_table = 'book_categories'
        unique_together = ['book', 'category']
    
    def __str__(self):
        return f"{self.book.title} - {self.category.name}"


class Review(models.Model):
    """
    Kitap değerlendirmesi - Flask Review modeli Django'ya uyarlandı
    """
    RATING_CHOICES = [
        (1, '1 - Çok Kötü'),
        (2, '2 - Kötü'),
        (3, '3 - Orta'),
        (4, '4 - İyi'),
        (5, '5 - Mükemmel'),
    ]
    
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Kitap'
    )
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Kullanıcı'
    )
    
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Puan'
    )
    
    comment = models.TextField(
        blank=True,
        verbose_name='Yorum'
    )
    
    helpful_count = models.IntegerField(
        default=0,
        verbose_name='Faydalı Bulunma Sayısı'
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
        verbose_name = 'Değerlendirme'
        verbose_name_plural = 'Değerlendirmeler'
        db_table = 'reviews'
        unique_together = ['book', 'user']  # Bir kullanıcı bir kitabı sadece bir kez değerlendirebilir
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.book.title} - {self.user.username} ({self.rating}/5)"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Kitabın ortalama puanını güncelle
        self.book.update_rating()


class Reservation(models.Model):
    """
    Kitap rezervasyonu - Flask Reservation modeli Django'ya uyarlandı
    """
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('fulfilled', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
        ('expired', 'Süresi Doldu'),
    ]
    
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Kitap'
    )
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Kullanıcı'
    )
    
    member = models.ForeignKey(
        'accounts.Member',
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Üye'
    )
    
    reservation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Rezervasyon Tarihi'
    )
    
    expiry_date = models.DateTimeField(
        verbose_name='Son Geçerlilik Tarihi'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Durum'
    )
    
    queue_position = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Sıra Numarası'
    )
    
    notification_sent = models.BooleanField(
        default=False,
        verbose_name='Bildirim Gönderildi'
    )
    
    fulfilled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Tamamlanma Tarihi'
    )
    
    class Meta:
        verbose_name = 'Rezervasyon'
        verbose_name_plural = 'Rezervasyonlar'
        db_table = 'reservations'
        ordering = ['queue_position', 'reservation_date']
    
    def __str__(self):
        return f"{self.book.title} - {self.user.username}"
    
    def is_expired(self):
        """Rezervasyonun süresi dolmuş mu kontrol eder"""
        return timezone.now() > self.expiry_date
    
    def cancel(self):
        """Rezervasyonu iptal eder"""
        self.status = 'cancelled'
        self.save()
    
    def fulfill(self):
        """Rezervasyonu tamamlar"""
        self.status = 'fulfilled'
        self.fulfilled_at = timezone.now()
        self.save()
    
    def save(self, *args, **kwargs):
        # İlk kayıt sırasında sona geçerlilik tarihi ayarla
        if not self.expiry_date:
            from django.conf import settings
            import datetime
            days = getattr(settings, 'LIBRARY_SETTINGS', {}).get('RESERVATION_EXPIRY_DAYS', 3)
            self.expiry_date = timezone.now() + datetime.timedelta(days=days)
        
        super().save(*args, **kwargs)


class OnlineBorrowRequest(models.Model):
    """
    Online ödünç alma talebi - Flask OnlineBorrowRequest modeli Django'ya uyarlandı
    """
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='online_requests',
        verbose_name='Kitap'
    )
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='online_requests',
        verbose_name='Kullanıcı'
    )
    
    member = models.ForeignKey(
        'accounts.Member',
        on_delete=models.CASCADE,
        related_name='online_requests',
        verbose_name='Üye'
    )
    
    pickup_date = models.DateField(
        verbose_name='Teslim Alma Tarihi'
    )
    
    pickup_time = models.TimeField(
        verbose_name='Teslim Alma Saati'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notlar'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Durum'
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name='Red Nedeni'
    )
    
    approved_by = models.CharField(
        max_length=80,
        blank=True,
        verbose_name='Onaylayan'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Onaylanma Tarihi'
    )
    
    class Meta:
        verbose_name = 'Online Ödünç Talebi'
        verbose_name_plural = 'Online Ödünç Talepleri'
        db_table = 'online_borrow_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.book.title} - {self.user.username} ({self.get_status_display()})"
    
    def approve(self, approved_by_user):
        """Talebi onaylar"""
        self.status = 'approved'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, reason):
        """Talebi reddeder"""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.save()
    
    def cancel(self):
        """Talebi iptal eder"""
        self.status = 'cancelled'
        self.save()


class SearchHistory(models.Model):
    """
    Arama geçmişi - Flask SearchHistory modeli Django'ya uyarlandı
    """
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='search_history',
        verbose_name='Kullanıcı'
    )
    
    search_term = models.CharField(
        max_length=200,
        verbose_name='Arama Terimi'
    )
    
    result_count = models.IntegerField(
        verbose_name='Sonuç Sayısı'
    )
    
    search_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Arama Tarihi'
    )
    
    class Meta:
        verbose_name = 'Arama Geçmişi'
        verbose_name_plural = 'Arama Geçmişleri'
        db_table = 'search_history'
        ordering = ['-search_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.search_term}"
