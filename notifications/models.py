from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """
    Bildirim modeli - Flask Notification modeli Django'ya uyarlandı
    """
    TYPE_CHOICES = [
        ('due_reminder', 'İade Hatırlatması'),
        ('overdue', 'Gecikme Bildirimi'),
        ('reservation_ready', 'Rezervasyon Hazır'),
        ('reservation_expired', 'Rezervasyon Süresi Doldu'),
        ('fine_applied', 'Ceza Uygulandı'),
        ('book_returned', 'Kitap İade Edildi'),
        ('renewal_reminder', 'Yenileme Hatırlatması'),
        ('system_message', 'Sistem Mesajı'),
        ('welcome', 'Hoş Geldin Mesajı'),
        ('book_request_approved', 'Kitap Talebi Onaylandı'),
        ('book_request_rejected', 'Kitap Talebi Reddedildi'),
        ('other', 'Diğer'),
    ]
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        verbose_name='Kullanıcı'
    )
    
    member = models.ForeignKey(
        'accounts.Member',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        verbose_name='Üye'
    )
    
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='other',
        verbose_name='Tip'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='Başlık'
    )
    
    message = models.TextField(
        verbose_name='Mesaj'
    )
    
    is_read = models.BooleanField(
        default=False,
        verbose_name='Okundu'
    )
    
    is_sent = models.BooleanField(
        default=False,
        verbose_name='Gönderildi'
    )
    
    related_book = models.ForeignKey(
        'books.Book',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='İlgili Kitap'
    )
    
    related_transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='İlgili İşlem'
    )
    
    email_sent = models.BooleanField(
        default=False,
        verbose_name='E-posta Gönderildi'
    )
    
    sms_sent = models.BooleanField(
        default=False,
        verbose_name='SMS Gönderildi'
    )
    
    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    read_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Okunma Tarihi'
    )
    
    sent_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Gönderilme Tarihi'
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Geçerlilik Süresi'
    )
    
    class Meta:
        verbose_name = 'Bildirim'
        verbose_name_plural = 'Bildirimler'
        db_table = 'notifications'
        ordering = ['-created_date']
    
    def __str__(self):
        recipient = self.user.username if self.user else self.member.ad_soyad if self.member else 'Genel'
        return f"{recipient} - {self.title}"
    
    def mark_as_read(self):
        """Bildirimi okundu olarak işaretler"""
        if not self.is_read:
            self.is_read = True
            self.read_date = timezone.now()
            self.save()
    
    def mark_as_sent(self):
        """Bildirimi gönderildi olarak işaretler"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_date = timezone.now()
            self.save()
    
    def is_expired(self):
        """Bildirimin süresi dolmuş mu kontrol eder"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @classmethod
    def create_due_reminder(cls, transaction):
        """İade hatırlatması bildirimi oluşturur"""
        return cls.objects.create(
            user=transaction.user,
            member=transaction.member,
            type='due_reminder',
            title='Kitap İade Hatırlatması',
            message=f'"{transaction.book.title}" adlı kitabınızın iade tarihi yaklaştı. İade tarihi: {transaction.due_date.strftime("%d.%m.%Y")}',
            related_book=transaction.book,
            related_transaction=transaction
        )
    
    @classmethod
    def create_overdue_notification(cls, transaction):
        """Gecikme bildirimi oluşturur"""
        days_late = (timezone.now() - transaction.due_date).days
        return cls.objects.create(
            user=transaction.user,
            member=transaction.member,
            type='overdue',
            title='Gecikmiş Kitap Bildirimi',
            message=f'"{transaction.book.title}" adlı kitabınız {days_late} gündür gecikmiş durumda. Lütfen en kısa sürede iade ediniz.',
            related_book=transaction.book,
            related_transaction=transaction
        )
    
    @classmethod
    def create_reservation_ready(cls, reservation):
        """Rezervasyon hazır bildirimi oluşturur"""
        return cls.objects.create(
            user=reservation.user,
            member=reservation.member,
            type='reservation_ready',
            title='Rezerve Kitabınız Hazır',
            message=f'"{reservation.book.title}" adlı kitabınız kütüphanede hazır. Son alma tarihi: {reservation.expiry_date.strftime("%d.%m.%Y")}',
            related_book=reservation.book
        )
    
    @classmethod
    def create_fine_notification(cls, fine):
        """Ceza bildirimi oluşturur"""
        return cls.objects.create(
            user=fine.user,
            member=fine.member,
            type='fine_applied',
            title='Ceza Uygulandı',
            message=f'{fine.amount} TL tutarında ceza uygulandı. Sebep: {fine.get_reason_display()}',
            related_transaction=fine.transaction
        )
    
    @classmethod
    def create_welcome_message(cls, user):
        """Hoş geldin mesajı oluşturur"""
        return cls.objects.create(
            user=user,
            type='welcome',
            title='Kütüphane Sistemine Hoş Geldiniz',
            message=f'Merhaba {user.get_full_name() or user.username}, kütüphane sistemimize hoş geldiniz! Kitapları keşfetmeye başlayabilirsiniz.'
        )


class EmailTemplate(models.Model):
    """
    E-posta şablonu modeli - Flask EmailTemplate modeli Django'ya uyarlandı
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Şablon Adı'
    )
    
    subject = models.CharField(
        max_length=200,
        verbose_name='Konu'
    )
    
    body = models.TextField(
        verbose_name='İçerik'
    )
    
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text='Kullanılabilir değişkenler listesi (JSON)',
        verbose_name='Değişkenler'
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
        verbose_name = 'E-posta Şablonu'
        verbose_name_plural = 'E-posta Şablonları'
        db_table = 'email_templates'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"
    
    def render(self, context=None):
        """Şablonu verilen context ile render eder"""
        if not context:
            context = {}
        
        subject = self.subject
        body = self.body
        
        # Basit değişken değiştirme (daha gelişmiş template engine kullanılabilir)
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        
        return {
            'subject': subject,
            'body': body
        }


class NotificationPreference(models.Model):
    """
    Kullanıcı bildirim tercihleri
    """
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='Kullanıcı'
    )
    
    email_due_reminder = models.BooleanField(
        default=True,
        verbose_name='E-posta İade Hatırlatması'
    )
    
    email_overdue = models.BooleanField(
        default=True,
        verbose_name='E-posta Gecikme Bildirimi'
    )
    
    email_reservation_ready = models.BooleanField(
        default=True,
        verbose_name='E-posta Rezervasyon Hazır'
    )
    
    email_fine_applied = models.BooleanField(
        default=True,
        verbose_name='E-posta Ceza Bildirimi'
    )
    
    sms_due_reminder = models.BooleanField(
        default=False,
        verbose_name='SMS İade Hatırlatması'
    )
    
    sms_overdue = models.BooleanField(
        default=False,
        verbose_name='SMS Gecikme Bildirimi'
    )
    
    sms_reservation_ready = models.BooleanField(
        default=False,
        verbose_name='SMS Rezervasyon Hazır'
    )
    
    web_notifications = models.BooleanField(
        default=True,
        verbose_name='Web Bildirimleri'
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
        verbose_name = 'Bildirim Tercihi'
        verbose_name_plural = 'Bildirim Tercihleri'
        db_table = 'notification_preferences'
    
    def __str__(self):
        return f"{self.user.username} - Bildirim Tercihleri"


class NotificationHistory(models.Model):
    """
    Gönderilen bildirim geçmişi
    """
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('sent', 'Gönderildi'),
        ('failed', 'Başarısız'),
        ('bounced', 'Geri Döndü'),
    ]
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_history',
        verbose_name='Bildirim'
    )
    
    channel = models.CharField(
        max_length=20,
        choices=[
            ('email', 'E-posta'),
            ('sms', 'SMS'),
            ('web', 'Web'),
            ('push', 'Push'),
        ],
        verbose_name='Kanal'
    )
    
    recipient = models.CharField(
        max_length=200,
        verbose_name='Alıcı'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Durum'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Hata Mesajı'
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Gönderilme Zamanı'
    )
    
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Teslim Edilme Zamanı'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi'
    )
    
    class Meta:
        verbose_name = 'Bildirim Geçmişi'
        verbose_name_plural = 'Bildirim Geçmişleri'
        db_table = 'notification_history'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification.title} - {self.channel} - {self.status}"


class SystemSettings(models.Model):
    """
    Sistem ayarları - Flask Settings modeli Django'ya uyarlandı
    """
    key = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Anahtar'
    )
    
    value = models.TextField(
        verbose_name='Değer'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Açıklama'
    )
    
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'Metin'),
            ('integer', 'Sayı'),
            ('float', 'Ondalık'),
            ('boolean', 'Mantıksal'),
            ('json', 'JSON'),
        ],
        default='string',
        verbose_name='Veri Tipi'
    )
    
    is_editable = models.BooleanField(
        default=True,
        verbose_name='Düzenlenebilir'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Güncellenme Tarihi'
    )
    
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Güncelleyen'
    )
    
    class Meta:
        verbose_name = 'Sistem Ayarı'
        verbose_name_plural = 'Sistem Ayarları'
        db_table = 'system_settings'
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}..."
    
    def get_value(self):
        """Değeri doğru tipte döndürür"""
        if self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'boolean':
            return self.value.lower() in ['true', '1', 'yes', 'on']
        elif self.data_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value
    
    def set_value(self, value):
        """Değeri doğru formatta kaydeder"""
        if self.data_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)
