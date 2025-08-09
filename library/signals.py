from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from accounts.models import Member
from transactions.models import Transaction, Fine
from notifications.models import Notification, NotificationPreference
from books.models import Book

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Yeni kullanıcı oluşturulduğunda otomatik olarak profil ve bildirim tercihleri oluştur
    """
    if created:
        # Bildirim tercihlerini oluştur
        NotificationPreference.objects.get_or_create(user=instance)
        
        # Hoş geldin mesajı gönder
        Notification.create_welcome_message(instance)


@receiver(post_save, sender=Transaction)
def handle_transaction_changes(sender, instance, created, **kwargs):
    """
    İşlem değişikliklerini takip et
    """
    if created:
        # Yeni ödünç alma işlemi
        # Kitabın mevcut adedini azalt
        if instance.book.available_quantity > 0:
            instance.book.available_quantity -= 1
            instance.book.save()
        
        # Üye istatistiklerini güncelle
        member = instance.member
        member.current_borrowed += 1
        member.total_borrowed += 1
        member.save()
    
    else:
        # Mevcut işlem güncellendi
        if instance.status == 'overdue' and not instance.fines.exists():
            # Gecikme bildirimi oluştur
            Notification.create_overdue_notification(instance)
        
        elif instance.status == 'returned' and instance.return_date:
            # İade bildirimi (isteğe bağlı)
            pass


@receiver(post_save, sender=Fine)
def handle_fine_created(sender, instance, created, **kwargs):
    """
    Yeni ceza oluşturulduğunda bildirim gönder
    """
    if created:
        Notification.create_fine_notification(instance)


@receiver(pre_save, sender=Transaction)
def check_due_date_approaching(sender, instance, **kwargs):
    """
    İade tarihi yaklaşan işlemler için hatırlatma gönder
    """
    if instance.pk:  # Mevcut bir kayıt güncelleniyorsa
        try:
            old_instance = Transaction.objects.get(pk=instance.pk)
            
            # İade tarihi değişti mi kontrol et
            if old_instance.due_date != instance.due_date:
                # Yeni tarihe göre hatırlatma planlama işlemi burada yapılabilir
                pass
                
        except Transaction.DoesNotExist:
            pass
