from flask import request
from flask_login import current_user
from flask_mail import Message
from datetime import datetime, timedelta
import requests
import qrcode
import io
import base64
import os
import tempfile
import pandas as pd
import shutil
import subprocess
import sys
import secrets
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from config import app, mail, get_setting
from models import db, User, Book, Member, Transaction, Category, BookCategory, Notification, SearchHistory, Review, Reservation, Fine, ActivityLog, Settings, EmailTemplate, OnlineBorrowRequest, QRCode

def log_activity(action, details=None):
    """Log user activity"""
    try:
        log = ActivityLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass

def generate_qr_code(data):
    """Generate QR code and return base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def save_qr_code(isbn):
    """Save QR code for a book"""
    data = f"BOOK:{isbn}"
    qr_image = generate_qr_code(data)
    
    # Save to file
    qr_path = f"static/qrcodes/{isbn}.png"
    with open(qr_path, "wb") as f:
        f.write(base64.b64decode(qr_image))
    
    return qr_path

def calculate_fine(due_date, return_date=None):
    """Calculate fine amount for overdue books"""
    if return_date is None:
        return_date = datetime.now()
    else:
        return_date = datetime.strptime(return_date, "%Y-%m-%d")
    
    due_date = datetime.strptime(due_date, "%Y-%m-%d")
    
    if return_date <= due_date:
        return 0.0
    
    days_overdue = (return_date - due_date).days
    fine_per_day = float(get_setting('fine_per_day', '1.0'))
    
    return days_overdue * fine_per_day

def send_email(to_email, template_name, context):
    """Send email using template"""
    if get_setting('email_notifications', 'true') != 'true':
        return False
    
    template = EmailTemplate.query.filter_by(name=template_name, is_active=True).first()
    if not template:
        return False
    
    try:
        # Replace variables in template
        subject = template.subject
        body = template.body
        
        for key, value in context.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))
        
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

def fetch_book_info_from_api(isbn):
    """Önce Google Books, sonra Open Library API'den kitap bilgisi ve kapak resmi çek"""
    # Önce Google Books API'den dene
    google_info = fetch_from_google_books(isbn)
    if google_info:
        # Eğer kapak resmi yoksa Open Library'den sadece kapak çek
        if not google_info.get('image_url'):
            openlib_info = fetch_from_openlibrary_for_cover(isbn)
            if openlib_info and openlib_info.get('image_url'):
                google_info['image_url'] = openlib_info['image_url']
        return google_info
    # Google Books bulamazsa Open Library'den tüm bilgiyi çek
    return fetch_from_openlibrary(isbn)

def fetch_from_google_books(isbn):
    """Fetch book info from Google Books API"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        response = requests.get(url)
        data = response.json()
        
        if data.get("totalItems", 0) > 0:
            item = data["items"][0]["volumeInfo"]
            return {
                "isbn": isbn,
                "title": item.get("title", "N/A"),
                "authors": ", ".join(item.get("authors", [])) or "N/A",
                "publish_date": item.get("publishedDate", "N/A"),
                "number_of_pages": item.get("pageCount", 0),
                "publishers": item.get("publisher", "N/A"),
                "languages": item.get("language", "N/A"),
                "description": item.get("description", ""),
                "image_url": item.get("imageLinks", {}).get("thumbnail")
            }
    except:
        pass
    return None

def fetch_from_openlibrary_for_cover(isbn):
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        key = f"ISBN:{isbn}"
        if key in data and "cover" in data[key]:
            book = data[key]
            image_url = book["cover"].get("large") or book["cover"].get("medium") or None
            return {"image_url": image_url}
    except Exception as e:
        print(f"OpenLibrary Cover Error: {e}")
    return None

def fetch_from_openlibrary(isbn):
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        key = f"ISBN:{isbn}"
        if key in data:
            book = data[key]
            book_info = {
                "isbn": isbn,
                "title": book.get("title", "N/A"),
                "authors": ", ".join([author['name'] for author in book.get("authors", [])]) or "N/A",
                "publish_date": book.get("publish_date", "N/A"),
                "number_of_pages": book.get("number_of_pages", 0),
                "publishers": ", ".join([publisher['name'] for publisher in book.get("publishers", [])]) or "N/A",
                "languages": ", ".join([lang['key'].split('/')[-1] for lang in book.get("languages", [])]) if book.get("languages") else "N/A",
                "description": book.get("description", {}).get("value", "") if isinstance(book.get("description"), dict) else book.get("description", ""),
                "image_url": None
            }
            if "cover" in book:
                image_url = book["cover"].get("large") or book["cover"].get("medium") or None
                book_info["image_url"] = image_url
            return book_info
    except Exception as e:
        print(f"OpenLibrary Error: {e}")
    return None

def add_notification(type, message, related_isbn=None):
    """Add a new notification"""
    notification = Notification(
        type=type,
        message=message,
        created_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        related_isbn=related_isbn
    )
    db.session.add(notification)
    db.session.commit()

def check_overdue_books():
    """Check for overdue books and create notifications"""
    # Books due soon
    upcoming = db.session.query(Transaction, Book, Member).join(Book, Transaction.isbn == Book.isbn)\
        .join(Member, Transaction.member_id == Member.id)\
        .filter(Transaction.return_date == None)\
        .filter(Transaction.due_date <= (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"))\
        .filter(Transaction.due_date >= datetime.now().strftime("%Y-%m-%d")).all()
    
    for trans, book, member in upcoming:
        message = f"'{book.title}' kitabı {member.ad_soyad} tarafından {trans.due_date} tarihine kadar iade edilmelidir."
        add_notification("return_reminder", message, book.isbn)
    
    # Overdue books
    overdue = db.session.query(Transaction, Book, Member).join(Book, Transaction.isbn == Book.isbn)\
        .join(Member, Transaction.member_id == Member.id)\
        .filter(Transaction.return_date == None)\
        .filter(Transaction.due_date < datetime.now().strftime("%Y-%m-%d")).all()
    
    for trans, book, member in overdue:
        message = f"'{book.title}' kitabı {member.ad_soyad} tarafından {trans.due_date} tarihinden beri gecikmiştir."
        add_notification("overdue", message, book.isbn)

def process_borrow_transaction(book, member, method, notes):
    """Ödünç alma işlemini işle"""
    # Ceza kontrolü
    if member.penalty_until and datetime.now() < member.penalty_until:
        return jsonify({'success': False, 'message': 'Üyenin ceza süresi devam ediyor'}), 403
    
    # Kullanılabilirlik kontrolü
    borrowed_count = Transaction.query.filter_by(isbn=book.isbn, return_date=None).count()
    if book.quantity <= borrowed_count:
        return jsonify({'success': False, 'message': 'Kitap şu anda mevcut değil'}), 400
    
    # Kullanıcının bu kitabı zaten ödünç alıp almadığını kontrol et
    existing_borrow = Transaction.query.filter_by(
        isbn=book.isbn, 
        member_id=member.id, 
        return_date=None
    ).first()
    
    if existing_borrow:
        return jsonify({'success': False, 'message': 'Bu üye kitabı zaten ödünç almış'}), 400
    
    # Aktif ödünç alma sayısı kontrolü
    active_borrows = Transaction.query.filter_by(member_id=member.id, return_date=None).count()
    max_books = int(get_setting('max_books_per_member', '5'))
    if active_borrows >= max_books:
        return jsonify({'success': False, 'message': f'Üye maksimum {max_books} kitap ödünç alabilir'}), 400
    
    # Ödünç alma işlemi
    due_date = (datetime.now() + timedelta(days=int(get_setting('max_borrow_days', '14')))).strftime('%Y-%m-%d')
    
    transaction = Transaction(
        isbn=book.isbn,
        member_id=member.id,
        borrow_date=datetime.now().strftime('%Y-%m-%d'),
        due_date=due_date,
        notes=f'{method.upper()} ile ödünç alındı - {notes}'
    )
    
    # Kitap istatistiklerini güncelle
    book.last_borrowed_date = datetime.now().strftime('%Y-%m-%d')
    book.total_borrow_count += 1
    
    # Üye istatistiklerini güncelle
    member.total_borrowed += 1
    member.current_borrowed += 1
    
    db.session.add(transaction)
    db.session.commit()
    
    # Bildirim oluştur
    add_notification('borrow', f'"{book.title}" kitabı ödünç alındı', book.isbn)
    
    # E-posta bildirimi gönder
    if member.email:
        send_email(member.email, 'book_borrowed', {
            'member_name': member.ad_soyad,
            'book_title': book.title,
            'due_date': due_date,
            'borrow_date': transaction.borrow_date
        })
    
    log_activity('borrow_transaction', f'{method.upper()} ile ödünç alma: {book.title} - {member.ad_soyad}')
    
    return jsonify({
        'success': True,
        'message': 'Kitap başarıyla ödünç alındı',
        'transaction': {
            'id': transaction.id,
            'book_title': book.title,
            'member_name': member.ad_soyad,
            'due_date': due_date,
            'borrow_date': transaction.borrow_date,
            'method': method
        }
    })

def process_return_transaction(book, member, method, notes):
    """İade işlemini işle"""
    # Aktif ödünç alma işlemini bul
    transaction = Transaction.query.filter_by(
        isbn=book.isbn, 
        member_id=member.id, 
        return_date=None
    ).first()
    
    if not transaction:
        return jsonify({'success': False, 'message': 'Bu kitap için aktif ödünç alma işlemi bulunamadı'}), 404
    
    # İade işlemi
    transaction.return_date = datetime.now().strftime('%Y-%m-%d')
    transaction.notes = f'{transaction.notes} - {method.upper()} ile iade edildi - {notes}'
    
    # Gecikme kontrolü
    due_date = datetime.strptime(transaction.due_date, '%Y-%m-%d')
    fine_amount = 0
    days_overdue = 0
    
    if datetime.now().date() > due_date.date():
        days_overdue = (datetime.now().date() - due_date.date()).days
        fine_amount = days_overdue * float(get_setting('daily_fine_amount', '1.0'))
        
        # Ceza oluştur
        fine = Fine(
            user_id=current_user.id,
            member_id=transaction.member_id,
            transaction_id=transaction.id,
            amount=fine_amount,
            reason='late_return'
        )
        db.session.add(fine)
        
        # Üye güvenilirlik puanını düşür
        member.reliability_score = max(0, member.reliability_score - (days_overdue * 2))
    
    # Üye istatistiklerini güncelle
    member.current_borrowed = max(0, member.current_borrowed - 1)
    
    db.session.commit()
    
    # Bildirim oluştur
    add_notification('return', f'"{book.title}" kitabı iade edildi', book.isbn)
    
    # E-posta bildirimi gönder
    if member.email:
        send_email(member.email, 'book_returned', {
            'member_name': member.ad_soyad,
            'book_title': book.title,
            'return_date': transaction.return_date,
            'fine_amount': fine_amount,
            'days_overdue': days_overdue
        })
    
    log_activity('return_transaction', f'{method.upper()} ile iade: {book.title} - {member.ad_soyad}')
    
    return jsonify({
        'success': True,
        'message': 'Kitap başarıyla iade edildi',
        'return_date': transaction.return_date,
        'fine_amount': fine_amount,
        'days_overdue': days_overdue,
        'method': method
    })

# Backup and Restore Functions
def create_backup():
    """Create database backup"""
    try:
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy database file
        shutil.copy2('instance/books_info.db', backup_path)
        
        log_activity('create_backup', f'Created backup: {backup_filename}')
        
        return backup_filename
    except Exception as e:
        print(f"Backup error: {e}")
        return None

def restore_backup(filename):
    """Restore database from backup"""
    try:
        backup_dir = 'backups'
        backup_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_path) or not filename.endswith('.db'):
            return False
        
        # Tüm bağlantıları kapat
        db.session.close_all()
        db.engine.dispose()
        
        # Mevcut veritabanını yedekle
        shutil.copy2('instance/books_info.db', 'instance/books_info_before_restore.db')
        
        # Yedeği geri yükle
        shutil.copy2(backup_path, 'instance/books_info.db')
        
        log_activity('restore_backup', f'Restored from backup: {filename}')
        
        # Windows Explorer'da dosyayı aç
        abs_db_path = os.path.abspath('instance/books_info.db')
        subprocess.Popen(f'explorer /select,"{abs_db_path}"')
        
        # Otomatik yeniden başlatma (Windows için)
        os.execl(sys.executable, sys.executable, *sys.argv)
        
        return True
    except Exception as e:
        print(f"Restore error: {e}")
        return False

# QR Code Functions
def generate_user_qr():
    """Generate QR code for user"""
    qr_token = secrets.token_urlsafe(32)
    expiry_time = datetime.utcnow() + timedelta(minutes=30)  # 30 dakika geçerli
    
    # QR kod bilgilerini veritabanına kaydet
    qr_code = QRCode(
        user_id=current_user.id,
        token=qr_token,
        expiry_time=expiry_time,
        status='active'
    )
    
    db.session.add(qr_code)
    db.session.commit()
    
    # QR kod URL'si oluştur
    qr_url = f"{request.host_url}qr/verify/{qr_token}"
    
    return {
        'qr_token': qr_token,
        'qr_url': qr_url,
        'expiry_time': expiry_time.strftime('%H:%M:%S'),
        'expires_in': 30  # dakika
    }

def verify_qr_code(token):
    """Verify QR code token"""
    qr_code = QRCode.query.filter_by(token=token).first()
    
    if not qr_code:
        return {'success': False, 'message': 'QR kod bulunamadı'}
    
    if qr_code.status != 'active':
        return {'success': False, 'message': 'QR kod kullanılmış veya süresi dolmuş'}
    
    if datetime.utcnow() > qr_code.expiry_time:
        qr_code.status = 'expired'
        db.session.commit()
        return {'success': False, 'message': 'QR kod süresi dolmuş'}
    
    # Kullanıcı bilgilerini getir
    user = User.query.get(qr_code.user_id)
    member = Member.query.filter_by(user_id=qr_code.user_id).first()
    
    return {
        'success': True,
        'user_info': {
            'username': user.username,
            'email': user.email,
            'member_name': member.ad_soyad if member else 'Üye bilgisi bulunamadı',
            'member_id': member.id if member else None
        },
        'expires_in': int((qr_code.expiry_time - datetime.utcnow()).total_seconds())
    }

def use_qr_code(token):
    """Use QR code (mark as used)"""
    qr_code = QRCode.query.filter_by(token=token).first()
    
    if not qr_code or qr_code.status != 'active':
        return False
    
    qr_code.status = 'used'
    qr_code.used_at = datetime.utcnow()
    db.session.commit()
    
    return True

# PDF Generation Functions
def generate_books_qr_pdf(books):
    """Generate QR codes for books in PDF format"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x, y = 20*mm, height-60*mm
    qr_size = 40*mm
    per_row = 4
    count = 0
    
    for book in books:
        qr_img = qrcode.make(book.isbn)
        c.drawInlineImage(qr_img, x, y, qr_size, qr_size)
        c.setFont('Helvetica', 8)
        c.drawString(x, y-8, f"{book.title[:30]}")
        c.drawString(x, y-16, f"ISBN: {book.isbn}")
        
        x += (qr_size + 10*mm)
        count += 1
        
        if count % per_row == 0:
            x = 20*mm
            y -= (qr_size + 20*mm)
            if y < 60*mm:
                c.showPage()
                x, y = 20*mm, height-60*mm
    
    c.save()
    buffer.seek(0)
    return buffer

def generate_members_qr_pdf(members):
    """Generate QR codes for members in PDF format"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x, y = 20*mm, height-60*mm
    qr_size = 40*mm
    per_row = 4
    count = 0
    
    for member in members:
        qr_img = qrcode.make(str(member.id))
        c.drawInlineImage(qr_img, x, y, qr_size, qr_size)
        c.setFont('Helvetica', 8)
        c.drawString(x, y-8, f"{member.ad_soyad[:30]}")
        c.drawString(x, y-16, f"No: {member.numara}")
        
        x += (qr_size + 10*mm)
        count += 1
        
        if count % per_row == 0:
            x = 20*mm
            y -= (qr_size + 20*mm)
            if y < 60*mm:
                c.showPage()
                x, y = 20*mm, height-60*mm
    
    c.save()
    buffer.seek(0)
    return buffer

def export_to_excel(data, sheet_name='Data'):
    """Export data to Excel format"""
    df = pd.DataFrame(data)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(temp.name, sheet_name=sheet_name, index=False)
    temp.close()
    return temp.name

# Online Borrow Request Functions
def process_online_borrow_request(request_data):
    """Process online borrow request"""
    isbn = request_data.get('isbn')
    pickup_date = request_data.get('pickup_date')
    pickup_time = request_data.get('pickup_time')
    notes = request_data.get('notes', '')
    
    # Kitap kontrolü
    book = Book.query.get(isbn)
    if not book:
        return {'success': False, 'message': 'Kitap bulunamadı'}
    
    # Kullanılabilirlik kontrolü
    borrowed_count = Transaction.query.filter_by(isbn=isbn, return_date=None).count()
    if book.quantity <= borrowed_count:
        return {'success': False, 'message': 'Kitap şu anda mevcut değil'}
    
    # Üye kontrolü
    member = Member.query.filter_by(user_id=current_user.id).first()
    if not member:
        return {'success': False, 'message': 'Üye kaydınız bulunamadı'}
    
    # Ceza kontrolü
    if member.penalty_until and datetime.now() < member.penalty_until:
        return {'success': False, 'message': 'Ceza süreniz devam ediyor'}
    
    # Aktif ödünç alma sayısı kontrolü
    active_borrows = Transaction.query.filter_by(member_id=member.id, return_date=None).count()
    max_books = int(get_setting('max_books_per_member', '5'))
    if active_borrows >= max_books:
        return {'success': False, 'message': f'Maksimum {max_books} kitap ödünç alabilirsiniz'}
    
    # Online ödünç alma talebi oluştur
    online_request = OnlineBorrowRequest(
        isbn=isbn,
        user_id=current_user.id,
        member_id=member.id,
        pickup_date=pickup_date,
        pickup_time=pickup_time,
        notes=notes,
        status='pending'
    )
    
    db.session.add(online_request)
    db.session.commit()
    
    # E-posta bildirimi gönder
    send_email(current_user.email, 'online_borrow_request', {
        'member_name': current_user.username,
        'book_title': book.title,
        'pickup_date': pickup_date,
        'pickup_time': pickup_time,
        'request_id': online_request.id
    })
    
    # Admin'lere bildirim gönder
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        send_email(admin.email, 'admin_online_borrow_notification', {
            'member_name': current_user.username,
            'book_title': book.title,
            'pickup_date': pickup_date,
            'pickup_time': pickup_time,
            'request_id': online_request.id
        })
    
    log_activity('online_borrow_request', f'Online ödünç alma talebi: {book.title}')
    
    return {
        'success': True, 
        'message': 'Ödünç alma talebiniz alındı. Onaylandığında e-posta ile bilgilendirileceksiniz.',
        'request_id': online_request.id
    }

def approve_online_borrow_request(request_id):
    """Approve online borrow request"""
    online_request = OnlineBorrowRequest.query.get(request_id)
    
    if not online_request or online_request.status != 'pending':
        return {'success': False, 'message': 'Talep bulunamadı veya zaten işlenmiş'}
    
    # Kitap ve üye kontrolü
    book = Book.query.get(online_request.isbn)
    member = Member.query.get(online_request.member_id)
    
    if not book or not member:
        return {'success': False, 'message': 'Kitap veya üye bulunamadı'}
    
    # Ödünç alma işlemini gerçekleştir
    result = process_borrow_transaction(book, member, 'online', f'Online rezervasyon - ID: {online_request.id}')
    
    if result.status_code == 200:
        # Talebi onayla
        online_request.status = 'approved'
        online_request.approved_at = datetime.utcnow()
        online_request.approved_by = current_user.username
        db.session.commit()
        
        # Kullanıcıya onay e-postası gönder
        user = User.query.get(online_request.user_id)
        send_email(user.email, 'online_borrow_approved', {
            'member_name': user.username,
            'book_title': book.title,
            'pickup_date': online_request.pickup_date,
            'pickup_time': online_request.pickup_time,
            'due_date': (datetime.now() + timedelta(days=int(get_setting('max_borrow_days', '14')))).strftime('%Y-%m-%d'),
            'request_id': online_request.id
        })
        
        log_activity('approve_online_borrow', f'Online ödünç alma onaylandı: {book.title}')
        
        return {'success': True, 'message': 'Ödünç alma talebi onaylandı'}
    
    return result

def reject_online_borrow_request(request_id, reason):
    """Reject online borrow request"""
    online_request = OnlineBorrowRequest.query.get(request_id)
    
    if not online_request or online_request.status != 'pending':
        return {'success': False, 'message': 'Talep bulunamadı veya zaten işlenmiş'}
    
    # Talebi reddet
    online_request.status = 'rejected'
    online_request.rejection_reason = reason
    online_request.approved_at = datetime.utcnow()
    online_request.approved_by = current_user.username
    
    db.session.commit()
    
    # Kullanıcıya red e-postası gönder
    user = User.query.get(online_request.user_id)
    book = Book.query.get(online_request.isbn)
    send_email(user.email, 'online_borrow_rejected', {
        'member_name': user.username,
        'book_title': book.title,
        'reason': reason,
        'request_id': online_request.id
    })
    
    log_activity('reject_online_borrow', f'Online ödünç alma reddedildi: {book.title}')
    
    return {'success': True, 'message': 'Ödünç alma talebi reddedildi ve kullanıcı bilgilendirildi'}

# Statistics and Reporting Functions
def get_inventory_summary():
    """Get inventory summary statistics"""
    total_books = db.session.query(db.func.sum(Book.quantity)).scalar() or 0
    distinct_books = Book.query.count()
    borrowed_books = Transaction.query.filter_by(return_date=None).count()
    available_books = total_books - borrowed_books
    
    # Kategori dağılımı
    category_data = db.session.query(
        Category.name, db.func.count(BookCategory.book_isbn)
    ).join(BookCategory).group_by(Category.name).all()
    
    category_labels = [c[0] for c in category_data]
    category_counts = [c[1] for c in category_data]
    
    # Popüler kitaplar
    popular_books = db.session.query(
        Book.title, db.func.count(Transaction.id).label('borrow_count')
    ).join(Transaction).group_by(Book.isbn).order_by(db.text('borrow_count DESC')).limit(10).all()
    
    # Aktif üyeler
    active_members = db.session.query(
        Member.ad_soyad.label('name'), db.func.count(Transaction.id).label('borrow_count')
    ).join(Transaction).group_by(Member.id).order_by(db.text('borrow_count DESC')).limit(10).all()
    
    return {
        'summary': {
            'total_books': total_books,
            'distinct_books': distinct_books,
            'borrowed_books': borrowed_books,
            'available_books': available_books
        },
        'category_labels': category_labels,
        'category_counts': category_counts,
        'popular_books': [{'title': b.title, 'borrow_count': b.borrow_count} for b in popular_books],
        'active_members': [{'name': m.name, 'borrow_count': m.borrow_count} for m in active_members]
    }

def get_member_statistics():
    """Get member statistics"""
    total_members = Member.query.count()
    active_members = Member.query.filter(Member.current_borrowed > 0).count()
    penalized_members = Member.query.filter(Member.penalty_until != None, Member.penalty_until > datetime.now()).count()
    
    # En çok ödünç alan üyeler
    most_active = db.session.query(
        Member.ad_soyad.label('name'), db.func.count(Transaction.id).label('borrow_count')
    ).join(Transaction).group_by(Member.id).order_by(db.text('borrow_count DESC')).limit(10).all()
    
    # Cezalı üyeler
    penalized = Member.query.filter(Member.penalty_until != None, Member.penalty_until > datetime.now()).all()
    
    # En çok gecikme yapan üyeler
    most_overdue = db.session.query(
        Member.ad_soyad.label('name'), db.func.count(Transaction.id).label('overdue_count')
    ).join(Transaction).filter(
        Transaction.return_date == None,
        Transaction.due_date < datetime.now().strftime('%Y-%m-%d')
    ).group_by(Member.id).order_by(db.text('overdue_count DESC')).limit(10).all()
    
    return {
        'summary': {
            'total_members': total_members,
            'active_members': active_members,
            'penalized_members': penalized_members
        },
        'most_active': [{'name': m.name, 'borrow_count': m.borrow_count} for m in most_active],
        'penalized': [{'name': m.ad_soyad, 'penalty_until': str(m.penalty_until)} for m in penalized],
        'most_overdue': [{'name': m.name, 'overdue_count': m.overdue_count} for m in most_overdue]
    }

# Search and Book Functions
def quick_search_books(query, limit=10):
    """Quick book search for online and QR operations"""
    if not query:
        return {'success': False, 'message': 'Arama terimi gerekli'}
    
    # Kitap arama
    books = Book.query.filter(
        db.or_(
            Book.title.contains(query),
            Book.authors.contains(query),
            Book.isbn.contains(query),
            Book.barcode.contains(query)
        )
    ).limit(limit).all()
    
    books_data = []
    for book in books:
        # Mevcut durumu kontrol et
        borrowed_count = Transaction.query.filter_by(isbn=book.isbn, return_date=None).count()
        available = book.quantity > borrowed_count
        
        books_data.append({
            'isbn': book.isbn,
            'title': book.title,
            'authors': book.authors,
            'quantity': book.quantity,
            'available': available,
            'borrowed_count': borrowed_count,
            'shelf': book.shelf,
            'cupboard': book.cupboard,
            'image_path': book.image_path,
            'total_borrow_count': book.total_borrow_count,
            'average_rating': book.average_rating
        })
    
    return {
        'success': True,
        'books': books_data,
        'total': len(books_data)
    }

def quick_search_members(query, limit=10):
    """Quick member search for online and QR operations"""
    if not query:
        return {'success': False, 'message': 'Arama terimi gerekli'}
    
    # Üye arama
    members = Member.query.filter(
        db.or_(
            Member.ad_soyad.contains(query),
            Member.numara.contains(query),
            Member.email.contains(query),
            Member.phone.contains(query)
        )
    ).limit(limit).all()
    
    members_data = []
    for member in members:
        # Aktif ödünç alma sayısını hesapla
        active_borrows = Transaction.query.filter_by(member_id=member.id, return_date=None).count()
        
        # Ceza durumunu kontrol et
        has_penalty = member.penalty_until and datetime.now() < member.penalty_until
        
        members_data.append({
            'id': member.id,
            'ad_soyad': member.ad_soyad,
            'sinif': member.sinif,
            'numara': member.numara,
            'email': member.email,
            'phone': member.phone,
            'uye_turu': member.uye_turu,
            'active_borrows': active_borrows,
            'total_borrowed': member.total_borrowed,
            'reliability_score': member.reliability_score,
            'has_penalty': has_penalty,
            'penalty_until': member.penalty_until.strftime('%d.%m.%Y') if member.penalty_until else None,
            'join_date': member.join_date.strftime('%d.%m.%Y') if member.join_date else None
        })
    
    return {
        'success': True,
        'members': members_data,
        'total': len(members_data)
    }
