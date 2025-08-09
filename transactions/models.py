from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from datetime import timedelta


class Transaction(models.Model):
    """
    Ödünç alma işlemleri - Flask Transaction modeli Django'ya uyarlandı
    """
    CONDITION_CHOICES = [
        ('good', 'İyi'),
        ('fair', 'Orta'),
        ('poor', 'Kötü'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('returned', 'İade Edildi'),
        ('overdue', 'Gecikmiş'),
        ('lost', 'Kayıp'),
        ('damaged', 'Hasarlı'),
    ]
    
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Kitap'
    )
    
    member = models.ForeignKey(
        'accounts.Member',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Üye'
    )
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Kullanıcı'
    )
    
    borrow_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ödünç Alma Tarihi'
    )
    
    due_date = models.DateTimeField(
        verbose_name='İade Tarihi'
    )
    
    return_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Gerçek İade Tarihi'
    )
    
    renew_count = models.IntegerField(
        default=0,
        verbose_name='Yenileme Sayısı'
    )
    
    condition_on_borrow = models.CharField(
        max_length=50,
        choices=CONDITION_CHOICES,
        default='good',
        verbose_name='Ödünç Alırkenki Durum'
    )
    
    condition_on_return = models.CharField(
        max_length=50,
        choices=CONDITION_CHOICES,
        blank=True,
        verbose_name='İade Ederkenki Durum'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Durum'
    )
    
    fine_amount = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Ceza Tutarı'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notlar'
    )
    
    librarian = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_transactions',
        verbose_name='İşlemi Yapan Kütüphaneci'
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
        verbose_name = 'İşlem'
        verbose_name_plural = 'İşlemler'
        db_table = 'transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.book.title} - {self.member.ad_soyad}"
    
    def is_overdue(self):
        """İşlemin gecikmiş olup olmadığını kontrol eder"""
        if self.status == 'active' and not self.return_date:
            return timezone.now() > self.due_date
        return False
    
    def days_overdue(self):
        """Kaç gün geciktiğini hesaplar"""
        if self.is_overdue():
            return (timezone.now() - self.due_date).days
        return 0
    
    def can_renew(self):
        """Yenilenebilir durumda olup olmadığını kontrol eder"""
        from django.conf import settings
        
        if self.status != 'active':
            return False, "İşlem aktif durumda değil"
        
        max_renew = getattr(settings, 'LIBRARY_SETTINGS', {}).get('MAX_RENEW_COUNT', 2)
        if self.renew_count >= max_renew:
            return False, f"Maksimum yenileme sayısına ulaşıldı ({max_renew})"
        
        if self.is_overdue():
            return False, "Gecikmiş kitap yenilenemez"
        
        # Rezervasyon kontrolü - başka biri kitabı rezerve ettiyse yenileyemez
        if self.book.reservations.filter(status='active').exists():
            return False, "Kitap rezerve edilmiş, yenilenemez"
        
        return True, "Yenilenebilir"
    
    def renew(self, renewed_by=None):
        """İşlemi yeniler"""
        can_renew, reason = self.can_renew()
        if not can_renew:
            return False, reason
        
        from django.conf import settings
        borrow_days = getattr(settings, 'LIBRARY_SETTINGS', {}).get('MAX_BORROW_DAYS', 14)
        
        self.due_date = timezone.now() + timedelta(days=borrow_days)
        self.renew_count += 1
        if renewed_by:
            self.librarian = renewed_by
        self.save()
        
        return True, f"Kitap {borrow_days} gün süreyle yenilendi"
    
    def return_book(self, returned_by=None, condition='good', notes=''):
        """Kitabı iade eder"""
        if self.status != 'active':
            return False, "İşlem zaten tamamlanmış"
        
        self.return_date = timezone.now()
        self.condition_on_return = condition
        self.status = 'returned'
        
        if notes:
            self.notes += f"\n[İADE] {notes}"
        
        if returned_by:
            self.librarian = returned_by
        
        # Kitabın mevcut adedini artır
        self.book.return_book()
        
        # Gecikme cezası hesapla
        if self.is_overdue():
            self.calculate_fine()
        
        # Üye istatistiklerini güncelle
        self.member.current_borrowed = max(0, self.member.current_borrowed - 1)
        self.member.save()
        
        self.save()
        return True, "Kitap başarıyla iade edildi"
    
    def calculate_fine(self):
        """Gecikme cezasını hesaplar"""
        if not self.is_overdue():
            return 0.0
        
        from django.conf import settings
        fine_per_day = getattr(settings, 'LIBRARY_SETTINGS', {}).get('FINE_PER_DAY', 1.0)
        days_late = self.days_overdue()
        
        self.fine_amount = days_late * fine_per_day
        self.save()
        
        # Fine modelinde ceza kaydı oluştur
        Fine.objects.create(
            user=self.user,
            member=self.member,
            transaction=self,
            amount=self.fine_amount,
            reason='late_return'
        )
        
        return self.fine_amount
    
    def save(self, *args, **kwargs):
        # İlk kayıt sırasında son teslim tarihi ayarla
        if not self.due_date:
            from django.conf import settings
            borrow_days = getattr(settings, 'LIBRARY_SETTINGS', {}).get('MAX_BORROW_DAYS', 14)
            self.due_date = timezone.now() + timedelta(days=borrow_days)
        
        # Durum güncelleme
        if not self.return_date and self.is_overdue():
            self.status = 'overdue'
        
        super().save(*args, **kwargs)


class Fine(models.Model):
    """
    Ceza modeli - Flask Fine modeli Django'ya uyarlandı
    """
    REASON_CHOICES = [
        ('late_return', 'Geç İade'),
        ('damaged', 'Hasarlı İade'),
        ('lost', 'Kayıp Kitap'),
        ('other', 'Diğer'),
    ]
    
    STATUS_CHOICES = [
        ('unpaid', 'Ödenmedi'),
        ('paid', 'Ödendi'),
        ('waived', 'Affedildi'),
    ]
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='fines',
        verbose_name='Kullanıcı'
    )
    
    member = models.ForeignKey(
        'accounts.Member',
        on_delete=models.CASCADE,
        related_name='fines',
        verbose_name='Üye'
    )
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='fines',
        null=True,
        blank=True,
        verbose_name='İşlem'
    )
    
    amount = models.FloatField(
        validators=[MinValueValidator(0.0)],
        verbose_name='Tutar'
    )
    
    reason = models.CharField(
        max_length=100,
        choices=REASON_CHOICES,
        default='late_return',
        verbose_name='Sebep'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unpaid',
        verbose_name='Durum'
    )
    
    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    paid_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ödenme Tarihi'
    )
    
    waived_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Affedilme Tarihi'
    )
    
    paid_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_fines',
        verbose_name='Tahsil Eden'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notlar'
    )
    
    class Meta:
        verbose_name = 'Ceza'
        verbose_name_plural = 'Cezalar'
        db_table = 'fines'
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.member.ad_soyad} - {self.amount} TL ({self.get_reason_display()})"
    
    def pay(self, paid_by=None, notes=''):
        """Cezayı ödenmiş olarak işaretler"""
        if self.status != 'unpaid':
            return False, "Ceza zaten ödenmiş veya affedilmiş"
        
        self.status = 'paid'
        self.paid_date = timezone.now()
        if paid_by:
            self.paid_by = paid_by
        if notes:
            self.notes += f"\n[ÖDEME] {notes}"
        
        self.save()
        return True, "Ceza ödenmiş olarak işaretlendi"
    
    def waive(self, waived_by=None, notes=''):
        """Cezayı affeder"""
        if self.status != 'unpaid':
            return False, "Ceza zaten ödenmiş veya affedilmiş"
        
        self.status = 'waived'
        self.waived_date = timezone.now()
        if waived_by:
            self.paid_by = waived_by  # Aynı alan kullanılır
        if notes:
            self.notes += f"\n[AFFETME] {notes}"
        
        self.save()
        return True, "Ceza affedildi"
    
    def is_paid(self):
        return self.status in ['paid', 'waived']


class TransactionHistory(models.Model):
    """
    İşlem geçmişi - tüm işlem değişikliklerini takip eder
    """
    ACTION_CHOICES = [
        ('borrow', 'Ödünç Verildi'),
        ('return', 'İade Edildi'),
        ('renew', 'Yenilendi'),
        ('overdue', 'Gecikti'),
        ('fine_applied', 'Ceza Uygulandı'),
        ('fine_paid', 'Ceza Ödendi'),
        ('fine_waived', 'Ceza Affedildi'),
    ]
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='İşlem'
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='İşlem'
    )
    
    performed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Yapan'
    )
    
    details = models.TextField(
        blank=True,
        verbose_name='Detaylar'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Zaman'
    )
    
    class Meta:
        verbose_name = 'İşlem Geçmişi'
        verbose_name_plural = 'İşlem Geçmişleri'
        db_table = 'transaction_history'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.transaction} - {self.get_action_display()}"
