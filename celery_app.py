"""
Celery Background Tasks Module
Arka plan görevleri: e-posta, raporlama, yedekleme
"""

import os
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta

def make_celery(app):
    """Celery instance oluştur"""
    celery = Celery(
        app.import_name,
        backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    )
    
    class ContextTask(celery.Task):
        """Flask app context ile task"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Celery configuration
celery_config = {
    'beat_schedule': {
        # Her gün 09:00'da geciken kitap bildirimleri gönder
        'send-overdue-notifications': {
            'task': 'celery_app.send_overdue_notifications',
            'schedule': crontab(hour=9, minute=0),
        },
        # Her gün 02:00'da veritabanı yedeği al
        'backup-database': {
            'task': 'celery_app.backup_database',
            'schedule': crontab(hour=2, minute=0),
        },
        # Ayın ilk günü 00:00'da aylık raporları oluştur
        'generate-monthly-reports': {
            'task': 'celery_app.generate_monthly_reports',
            'schedule': crontab(day_of_month=1, hour=0, minute=0),
        },
        # Her hafta Pazartesi 08:00'da popüler kitapları güncelle
        'update-popular-books': {
            'task': 'celery_app.update_popular_books',
            'schedule': crontab(day_of_week=1, hour=8, minute=0),
        },
        # Her 6 saatte bir AI modellerini güncelle
        'retrain-ai-models': {
            'task': 'celery_app.retrain_ai_models',
            'schedule': crontab(minute=0, hour='*/6'),
        }
    },
    'timezone': 'Europe/Istanbul',
}

# Global celery instance (will be initialized in app startup)
celery = None

def init_celery(app):
    """Celery'yi Flask app ile başlat"""
    global celery
    celery = make_celery(app)
    celery.conf.update(celery_config)
    return celery

# Background Tasks

def send_overdue_notifications():
    """Geciken kitaplar için e-posta bildirimi gönder"""
    try:
        from models import db, Transaction, Member, Book
        from utils import send_email
        
        print("📧 Geciken kitap bildirimleri gönderiliyor...")
        
        # Geciken işlemleri bul
        today = datetime.now().strftime('%Y-%m-%d')
        overdue_transactions = Transaction.query.filter(
            Transaction.return_date == None,
            Transaction.due_date < today
        ).all()
        
        sent_count = 0
        
        for transaction in overdue_transactions:
            try:
                member = Member.query.get(transaction.member_id)
                book = Book.query.get(transaction.isbn)
                
                if member and member.email and book:
                    # Gecikme gün sayısını hesapla
                    due_date = datetime.strptime(transaction.due_date, '%Y-%m-%d')
                    days_overdue = (datetime.now().date() - due_date.date()).days
                    
                    # E-posta gönder
                    email_data = {
                        'member_name': member.ad_soyad,
                        'book_title': book.title,
                        'due_date': transaction.due_date,
                        'days_overdue': days_overdue,
                        'fine_amount': days_overdue * 1.0  # Günlük 1₺ ceza
                    }
                    
                    success = send_email(
                        member.email,
                        'overdue_reminder',
                        email_data
                    )
                    
                    if success:
                        sent_count += 1
                        
            except Exception as e:
                print(f"❌ E-posta gönderme hatası (Transaction {transaction.id}): {e}")
        
        print(f"✅ {sent_count} geciken kitap bildirimi gönderildi")
        return sent_count
        
    except Exception as e:
        print(f"❌ Geciken kitap bildirimi görevi başarısız: {e}")
        return 0

def backup_database():
    """Veritabanı yedeği al"""
    try:
        import shutil
        import sqlite3
        from datetime import datetime
        
        print("💾 Veritabanı yedeği alınıyor...")
        
        # Yedek klasörü oluştur
        backup_dir = 'backups/auto'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Tarih damgası ile yedek dosya adı
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"library_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # SQLite veritabanını kopyala
        db_path = 'instance/library.db'  # SQLite dosya yolu
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            
            # Eski yedekleri temizle (30 günden eski olanları)
            cleanup_old_backups(backup_dir, days=30)
            
            print(f"✅ Veritabanı yedeği alındı: {backup_filename}")
            return backup_filename
        else:
            print("❌ Veritabanı dosyası bulunamadı")
            return None
            
    except Exception as e:
        print(f"❌ Veritabanı yedekleme hatası: {e}")
        return None

def cleanup_old_backups(backup_dir, days=30):
    """Eski yedekleri temizle"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for filename in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, filename)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_time < cutoff_date:
                    os.remove(file_path)
                    print(f"🗑️ Eski yedek silindi: {filename}")
                    
    except Exception as e:
        print(f"❌ Eski yedek temizleme hatası: {e}")

def generate_monthly_reports():
    """Aylık raporları oluştur"""
    try:
        from models import db, Transaction, Book, Member
        from utils import generate_pdf_report
        import pandas as pd
        
        print("📊 Aylık raporlar oluşturuluyor...")
        
        # Geçen ay verilerini al
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        month_start = last_month.replace(day=1).strftime('%Y-%m-%d')
        month_end = last_month.strftime('%Y-%m-%d')
        
        # Aylık işlem raporu
        monthly_transactions = Transaction.query.filter(
            Transaction.borrow_date.between(month_start, month_end)
        ).all()
        
        # Rapor verileri
        report_data = {
            'period': f"{last_month.strftime('%B %Y')}",
            'total_borrows': len(monthly_transactions),
            'active_members': len(set(t.member_id for t in monthly_transactions)),
            'popular_books': [],
            'member_stats': []
        }
        
        # En popüler kitapları bul
        book_counts = {}
        for transaction in monthly_transactions:
            book_counts[transaction.isbn] = book_counts.get(transaction.isbn, 0) + 1
        
        popular_isbns = sorted(book_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for isbn, count in popular_isbns:
            book = Book.query.get(isbn)
            if book:
                report_data['popular_books'].append({
                    'title': book.title,
                    'authors': book.authors,
                    'borrow_count': count
                })
        
        # PDF raporu oluştur
        report_filename = f"monthly_report_{last_month.strftime('%Y_%m')}.pdf"
        report_path = os.path.join('reports', report_filename)
        
        os.makedirs('reports', exist_ok=True)
        
        # Basit PDF raporu (gerçek implementasyon için reportlab kullanılabilir)
        with open(report_path.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
            f.write(f"AYLIK RAPOR - {report_data['period']}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Toplam Ödünç Alma: {report_data['total_borrows']}\n")
            f.write(f"Aktif Üye Sayısı: {report_data['active_members']}\n\n")
            f.write("EN POPÜLER KİTAPLAR:\n")
            f.write("-" * 30 + "\n")
            for book in report_data['popular_books']:
                f.write(f"{book['title']} - {book['authors']} ({book['borrow_count']} kez)\n")
        
        print(f"✅ Aylık rapor oluşturuldu: {report_filename}")
        return report_filename
        
    except Exception as e:
        print(f"❌ Aylık rapor oluşturma hatası: {e}")
        return None

def update_popular_books():
    """Popüler kitapları güncelle"""
    try:
        from models import db, Book, Transaction
        
        print("📈 Popüler kitaplar güncelleniyor...")
        
        # Son 30 günlük verilerle popülerlik skorlarını güncelle
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Her kitap için son 30 günlük ödünç alma sayısını hesapla
        books = Book.query.all()
        updated_count = 0
        
        for book in books:
            recent_borrows = Transaction.query.filter(
                Transaction.isbn == book.isbn,
                Transaction.borrow_date >= thirty_days_ago
            ).count()
            
            # Popülerlik skorunu güncelle (ağırlıklı ortalama)
            old_score = book.total_borrow_count or 0
            new_score = old_score * 0.8 + recent_borrows * 0.2
            
            if abs(new_score - old_score) > 0.1:  # Anlamlı değişiklik varsa güncelle
                book.total_borrow_count = int(new_score)
                updated_count += 1
        
        db.session.commit()
        
        print(f"✅ {updated_count} kitabın popülerlik skoru güncellendi")
        return updated_count
        
    except Exception as e:
        print(f"❌ Popüler kitap güncelleme hatası: {e}")
        return 0

def retrain_ai_models():
    """AI modellerini yeniden eğit"""
    try:
        from models import db, Book, Transaction
        from ai_engine import get_ai_engine
        
        print("🤖 AI modelleri yeniden eğitiliyor...")
        
        # Güncel veriyi al
        books_data = Book.query.all()
        transactions_data = Transaction.query.all()
        
        if len(books_data) < 10:  # Minimum veri kontrolü
            print("⚠️ Yeterli veri yok, AI eğitimi atlandı")
            return False
        
        # AI engine'i al ve modelleri eğit
        ai_engine = get_ai_engine()
        
        # Öneri sistemini yeniden eğit
        ai_engine['recommendation'].train(books_data)
        
        print("✅ AI modelleri başarıyla yeniden eğitildi")
        return True
        
    except Exception as e:
        print(f"❌ AI model eğitimi hatası: {e}")
        return False

def send_due_date_reminders():
    """Teslim tarihi yaklaşan kitaplar için hatırlatma gönder"""
    try:
        from models import db, Transaction, Member, Book
        from utils import send_email
        
        print("⏰ Teslim tarihi hatırlatmaları gönderiliyor...")
        
        # Yarın teslim edilecek kitapları bul
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        due_tomorrow = Transaction.query.filter(
            Transaction.due_date == tomorrow,
            Transaction.return_date == None
        ).all()
        
        sent_count = 0
        
        for transaction in due_tomorrow:
            try:
                member = Member.query.get(transaction.member_id)
                book = Book.query.get(transaction.isbn)
                
                if member and member.email and book:
                    email_data = {
                        'member_name': member.ad_soyad,
                        'book_title': book.title,
                        'due_date': transaction.due_date
                    }
                    
                    success = send_email(
                        member.email,
                        'due_date_reminder',
                        email_data
                    )
                    
                    if success:
                        sent_count += 1
                        
            except Exception as e:
                print(f"❌ Hatırlatma e-postası gönderme hatası: {e}")
        
        print(f"✅ {sent_count} teslim tarihi hatırlatması gönderildi")
        return sent_count
        
    except Exception as e:
        print(f"❌ Teslim tarihi hatırlatması görevi başarısız: {e}")
        return 0

# Task registration (these will be registered when celery starts)
def register_tasks(celery_app):
    """Celery task'larını kaydet"""
    
    @celery_app.task(name='celery_app.send_overdue_notifications')
    def task_send_overdue_notifications():
        return send_overdue_notifications()
    
    @celery_app.task(name='celery_app.backup_database')
    def task_backup_database():
        return backup_database()
    
    @celery_app.task(name='celery_app.generate_monthly_reports')
    def task_generate_monthly_reports():
        return generate_monthly_reports()
    
    @celery_app.task(name='celery_app.update_popular_books')
    def task_update_popular_books():
        return update_popular_books()
    
    @celery_app.task(name='celery_app.retrain_ai_models')
    def task_retrain_ai_models():
        return retrain_ai_models()
    
    @celery_app.task(name='celery_app.send_due_date_reminders')
    def task_send_due_date_reminders():
        return send_due_date_reminders()
    
    print("✅ Celery task'ları kaydedildi")

print("⚙️ Celery background tasks modülü yüklendi!") 