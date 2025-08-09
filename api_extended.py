from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import pandas as pd
import tempfile
import os
import json
import secrets
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import qrcode
import shutil
import subprocess
import sys

from config import app, get_setting
from models import db, User, Book, Member, Transaction, Category, BookCategory, Notification, SearchHistory, Review, Reservation, Fine, ActivityLog, Settings, EmailTemplate, OnlineBorrowRequest, QRCode
from utils import (log_activity, send_email, add_notification, generate_qr_code, 
                   save_qr_code, process_borrow_transaction, process_return_transaction,
                   generate_books_qr_pdf, generate_members_qr_pdf, export_to_excel,
                   process_online_borrow_request, approve_online_borrow_request,
                   reject_online_borrow_request, get_inventory_summary, get_member_statistics,
                   quick_search_books, quick_search_members, generate_user_qr, verify_qr_code, use_qr_code)
from routes import role_required

# Notifications API
@app.route('/api/notifications')
def api_get_notifications():
    """Get all notifications"""
    unread_only = request.args.get('unread_only', 'false') == 'true'
    
    query = Notification.query
    if unread_only:
        query = query.filter_by(is_read=0)
    
    notifications = query.order_by(Notification.created_date.desc()).all()
    
    notifications_data = []
    for notif in notifications:
        notifications_data.append({
            'id': notif.id,
            'type': notif.type,
            'message': notif.message,
            'created_date': notif.created_date,
            'is_read': notif.is_read,
            'related_isbn': notif.related_isbn
        })
    
    return jsonify({'notifications': notifications_data})

@app.route('/api/notifications/<int:id>/read', methods=['POST'])
def api_mark_notification_read(id):
    """Mark notification as read"""
    notification = Notification.query.get_or_404(id)
    notification.is_read = 1
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    """Mark all notifications as read"""
    Notification.query.filter_by(is_read=0).update({'is_read': 1})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/<int:id>', methods=['DELETE'])
@login_required
def api_delete_notification(id):
    """Delete a notification"""
    notification = Notification.query.get_or_404(id)
    db.session.delete(notification)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/clear-all', methods=['DELETE'])
@login_required
def api_clear_all_notifications():
    """Clear all notifications"""
    Notification.query.delete()
    db.session.commit()
    return jsonify({'success': True})

# Reservations API
@app.route('/api/reservations/<int:id>/cancel', methods=['POST'])
@login_required  
def api_cancel_reservation(id):
    """Cancel a reservation"""
    reservation = Reservation.query.get_or_404(id)
    
    # Check if user owns this reservation
    if reservation.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Bu rezervasyon size ait değil'}), 403
    
    # Check if already cancelled
    if reservation.status != 'active':
        return jsonify({'success': False, 'message': 'Bu rezervasyon zaten aktif değil'}), 400
    
    # Cancel reservation
    reservation.status = 'cancelled'
    
    # Update queue positions for other reservations
    other_reservations = Reservation.query.filter(
        Reservation.isbn == reservation.isbn,
        Reservation.status == 'active',
        Reservation.queue_position > reservation.queue_position
    ).all()
    
    for res in other_reservations:
        res.queue_position -= 1
    
    db.session.commit()
    
    log_activity('cancel_reservation', f'Cancelled reservation {id}')
    
    return jsonify({'success': True, 'message': 'Rezervasyon iptal edildi'})

# Fines API
@app.route('/api/fines/<int:id>/pay', methods=['POST'])
@login_required
def api_pay_fine(id):
    """Pay a fine"""
    fine = Fine.query.get_or_404(id)
    
    if fine.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Bu ceza size ait değil'}), 403
    
    if fine.status == 'paid':
        return jsonify({'success': False, 'message': 'Bu ceza zaten ödenmiş'}), 400
    
    fine.status = 'paid'
    fine.paid_date = datetime.utcnow()
    db.session.commit()
    
    log_activity('pay_fine', f'Paid fine {id}')
    
    return jsonify({'success': True, 'message': 'Ceza ödendi'})

# Settings API
@app.route('/api/settings', methods=['POST'])
@login_required
@role_required('admin')
def api_update_settings():
    """Update system settings"""
    for key, value in request.json.items():
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Settings(key=key, value=value)
            db.session.add(setting)
    
    db.session.commit()
    log_activity('update_settings', 'System settings updated')
    
    return jsonify({'success': True, 'message': 'Ayarlar güncellendi'})

# Users Management API
@app.route('/api/users/<int:id>/toggle-active', methods=['POST'])
@login_required
@role_required('admin')
def api_toggle_user_active(id):
    """Toggle user active status"""
    user = User.query.get_or_404(id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Kendi hesabınızı devre dışı bırakamazsınız'}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    log_activity('toggle_user', f'Toggled user {user.username} active status to {user.is_active}')
    
    return jsonify({'success': True, 'is_active': user.is_active})

@app.route('/api/users', methods=['POST'])
@login_required
@role_required('admin')
def api_create_user():
    """Create new user"""
    data = request.json
    
    # Validate data
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Bu kullanıcı adı zaten kullanılıyor'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'message': 'Bu e-posta adresi zaten kayıtlı'}), 400
    
    try:
        user = User(
            username=data['username'],
            email=data['email'],
            role=data.get('role', 'user')
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        
        log_activity('create_user', f'Created user: {user.username}')
        
        return jsonify({'success': True, 'message': 'Kullanıcı oluşturuldu'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:id>', methods=['PUT'])
@login_required
@role_required('admin')
def api_update_user(id):
    """Update user information"""
    user = User.query.get_or_404(id)
    data = request.json
    
    # Update email if changed
    if 'email' in data and data['email'] != user.email:
        if User.query.filter(User.email == data['email'], User.id != id).first():
            return jsonify({'success': False, 'message': 'Bu e-posta adresi zaten kullanılıyor'}), 400
        user.email = data['email']
    
    # Update role
    if 'role' in data:
        user.role = data['role']
    
    # Update password if provided
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    
    db.session.commit()
    log_activity('update_user', f'Updated user: {user.username}')
    
    return jsonify({'success': True, 'message': 'Kullanıcı güncellendi'})

@app.route('/api/users/<int:id>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_delete_user(id):
    """Delete user"""
    user = User.query.get_or_404(id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Kendi hesabınızı silemezsiniz'}), 400
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_activity('delete_user', f'Deleted user: {username}')
    
    return jsonify({'success': True, 'message': 'Kullanıcı silindi'})

@app.route('/api/users/<int:id>/activity')
@login_required
@role_required('admin')
def api_user_activity(id):
    """Get user activity logs"""
    activities = ActivityLog.query.filter_by(user_id=id)\
        .order_by(ActivityLog.timestamp.desc()).limit(50).all()
    
    activities_data = []
    for activity in activities:
        activities_data.append({
            'timestamp': activity.timestamp.isoformat(),
            'action': activity.action,
            'details': activity.details,
            'ip_address': activity.ip_address
        })
    
    return jsonify({'activities': activities_data})

# Email Templates API
@app.route('/api/email-templates/<int:id>', methods=['PUT'])
@login_required
@role_required('admin')
def api_update_email_template(id):
    """Update email template"""
    template = EmailTemplate.query.get_or_404(id)
    data = request.json
    
    template.subject = data.get('subject', template.subject)
    template.body = data.get('body', template.body)
    template.is_active = data.get('is_active', template.is_active)
    
    db.session.commit()
    log_activity('update_email_template', f'Updated template: {template.name}')
    
    return jsonify({'success': True, 'message': 'E-posta şablonu güncellendi'})

# Backup and Restore API
@app.route('/api/backup/create', methods=['POST'])
@login_required
@role_required('admin')
def api_create_backup():
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
        
        return jsonify({
            'success': True,
            'message': 'Yedekleme başarıyla oluşturuldu',
            'filename': backup_filename
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/backup/download/<filename>')
@login_required
@role_required('admin')
def api_download_backup(filename):
    """Download backup file"""
    backup_dir = 'backups'
    filepath = os.path.join(backup_dir, filename)
    
    if os.path.exists(filepath) and filename.endswith('.db'):
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'Backup file not found'}), 404

@app.route('/api/backup/restore/<filename>', methods=['POST'])
@login_required
@role_required('admin')
def api_restore_backup(filename):
    """Restore database from backup"""
    try:
        backup_dir = 'backups'
        backup_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_path) or not filename.endswith('.db'):
            return jsonify({'success': False, 'message': 'Yedek dosyası bulunamadı'}), 404
        
        # Veritabanı bağlantılarını kapat
        try:
            db.session.close()
            db.engine.dispose()
        except:
            pass
        
        # Mevcut veritabanını yedekle
        try:
            shutil.copy2('instance/books_info.db', f'instance/books_info_before_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        except:
            pass
        
        # Yedeği geri yükle
        shutil.copy2(backup_path, 'instance/books_info.db')
        
        log_activity('restore_backup', f'Restored from backup: {filename}')
        
        return jsonify({
            'success': True,
            'message': 'Veritabanı başarıyla geri yüklendi. Sayfayı yenileyin.'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Geri yükleme hatası: {str(e)}'}), 500

@app.route('/api/backup/delete/<filename>', methods=['POST', 'DELETE'])
@login_required
@role_required('admin')
def api_delete_backup(filename):
    """Delete backup file"""
    try:
        backup_dir = 'backups'
        filepath = os.path.join(backup_dir, filename)
        
        if os.path.exists(filepath) and filename.endswith('.db'):
            os.remove(filepath)
            log_activity('delete_backup', f'Deleted backup: {filename}')
            return jsonify({'success': True, 'message': 'Yedek silindi'})
        else:
            return jsonify({'success': False, 'message': 'Yedek dosyası bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Export/Import Additional APIs
@app.route('/api/export/members', methods=['GET'])
def api_export_members():
    """Export members to Excel"""
    members = Member.query.all()
    
    data = []
    for member in members:
        data.append({
            'ID': member.id,
            'Ad-Soyad': member.ad_soyad,
            'Sınıf': member.sinif,
            'Numara': member.numara,
            'E-posta': member.email,
            'Üye Türü': member.uye_turu
        })
    
    df = pd.DataFrame(data)
    
    # Create temporary file
    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(temp.name, index=False)
    temp.close()
    
    return send_file(temp.name, as_attachment=True, download_name='uyeler.xlsx')

@app.route('/api/import/members', methods=['POST'])
def api_import_members():
    """Import members from Excel"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Dosya bulunamadı'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Dosya seçilmedi'}), 400
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            df = pd.read_excel(filepath)
            
            for _, row in df.iterrows():
                member = Member(
                    ad_soyad=row.get('ad_soyad', ''),
                    sinif=row.get('sinif', ''),
                    numara=row.get('numara', ''),
                    email=row.get('email', ''),
                    uye_turu=row.get('uye_turu', 'Öğrenci')
                )
                db.session.add(member)
            
            db.session.commit()
            os.remove(filepath)
            
            return jsonify({'success': True, 'message': f'{len(df)} üye başarıyla yüklendi'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    
    return jsonify({'success': False, 'message': 'Geçersiz dosya formatı'}), 400

@app.route('/api/export/transactions', methods=['GET'])
def api_export_transactions():
    """Export transactions to Excel"""
    transactions = db.session.query(Transaction, Book, Member)\
        .join(Book, Transaction.isbn == Book.isbn)\
        .join(Member, Transaction.member_id == Member.id)\
        .order_by(Transaction.id.desc()).all()
    
    data = []
    for trans, book, member in transactions:
        data.append({
            'ID': trans.id,
            'ISBN': trans.isbn,
            'Kitap Adı': book.title,
            'Üye ID': trans.member_id,
            'Üye Adı': member.ad_soyad,
            'Veriliş Tarihi': trans.borrow_date,
            'Son Tarih': trans.due_date,
            'İade Tarihi': trans.return_date or '-'
        })
    
    df = pd.DataFrame(data)
    
    # Create temporary file
    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(temp.name, index=False)
    temp.close()
    
    return send_file(temp.name, as_attachment=True, download_name='islemler.xlsx')

# Bulk QR and PDF generation APIs
@app.route('/api/members/qr-bulk')
@login_required
@role_required('admin')
def api_members_qr_bulk():
    members = Member.query.all()
    buffer = generate_members_qr_pdf(members)
    return send_file(buffer, as_attachment=True, download_name='uyeler_qr.pdf', mimetype='application/pdf')

@app.route('/api/books/qr-bulk', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_books_qr_bulk():
    if request.method == 'POST':
        isbns = request.form.get('isbns')
        if isbns:
            isbns = json.loads(isbns)
            books = Book.query.filter(Book.isbn.in_(isbns)).all()
        else:
            books = Book.query.all()
    else:
        books = Book.query.all()
    
    buffer = generate_books_qr_pdf(books)
    return send_file(buffer, as_attachment=True, download_name='kitaplar_qr.pdf', mimetype='application/pdf')

@app.route('/api/books/pdf-bulk', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_books_pdf_bulk():
    if request.method == 'POST':
        isbns = request.form.get('isbns')
        if isbns:
            isbns = json.loads(isbns)
            books = Book.query.filter(Book.isbn.in_(isbns)).all()
        else:
            books = Book.query.all()
    else:
        books = Book.query.all()
    
    data = []
    for book in books:
        borrowed = Transaction.query.filter_by(isbn=book.isbn, return_date=None).count()
        data.append({
            'ISBN': book.isbn,
            'Kitap Adı': book.title,
            'Yazar': book.authors,
            'Yayınevi': book.publishers,
            'Mevcut/Toplam': f"{book.quantity - borrowed}/{book.quantity}"
        })
    
    temp_file = export_to_excel(data, 'Kitaplar')
    return send_file(temp_file, as_attachment=True, download_name='kitaplar_liste.xlsx', 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/members/pdf-bulk', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_members_pdf_bulk():
    if request.method == 'POST':
        ids = request.form.get('ids')
        if ids:
            ids = json.loads(ids)
            members = Member.query.filter(Member.id.in_(ids)).all()
        else:
            members = Member.query.all()
    else:
        members = Member.query.all()
    
    data = []
    for m in members:
        data.append({
            'Ad Soyad': m.ad_soyad,
            'Numara': m.numara,
            'Sınıf': m.sinif,
            'E-posta': m.email,
            'Üye Türü': m.uye_turu
        })
    
    temp_file = export_to_excel(data, 'Üyeler')
    return send_file(temp_file, as_attachment=True, download_name='uyeler_liste.xlsx', 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Inventory APIs
@app.route('/api/inventory/summary')
@login_required
@role_required('admin')
def api_inventory_summary():
    summary = get_inventory_summary()
    return jsonify(summary)

@app.route('/api/inventory/pdf')
@login_required
@role_required('admin')
def api_inventory_pdf():
    summary = get_inventory_summary()
    
    # Excel dosyasına yaz
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_path = temp_file.name
    temp_file.close()
    
    with pd.ExcelWriter(temp_path) as writer:
        pd.DataFrame([
            ['Toplam Kitap', summary['summary']['total_books']],
            ['Farklı Kitap', summary['summary']['distinct_books']],
            ['Ödünçte', summary['summary']['borrowed_books']],
            ['Mevcut', summary['summary']['available_books']]
        ], columns=['Özellik', 'Değer']).to_excel(writer, sheet_name='Özet', index=False)
        
        pd.DataFrame(list(zip(summary['category_labels'], summary['category_counts'])), 
                    columns=['Kategori', 'Adet']).to_excel(writer, sheet_name='Kategoriler', index=False)
        
        pd.DataFrame([(b['title'], b['borrow_count']) for b in summary['popular_books']], 
                    columns=['Kitap', 'Adet']).to_excel(writer, sheet_name='Popüler Kitaplar', index=False)
        
        pd.DataFrame([(m['name'], m['borrow_count']) for m in summary['active_members']], 
                    columns=['Üye', 'Adet']).to_excel(writer, sheet_name='Aktif Üyeler', index=False)
    
    return send_file(temp_path, as_attachment=True, download_name='envanter_ozet.xlsx', 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/inventory/member-stats')
@login_required
@role_required('admin')
def api_inventory_member_stats():
    stats = get_member_statistics()
    return jsonify(stats)

@app.route('/api/inventory/members-pdf')
@login_required
@role_required('admin')
def api_inventory_members_pdf():
    stats = get_member_statistics()
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_path = temp_file.name
    temp_file.close()
    
    with pd.ExcelWriter(temp_path) as writer:
        pd.DataFrame([
            ['Toplam Üye', stats['summary']['total_members']],
            ['Aktif Üye', stats['summary']['active_members']],
            ['Cezalı Üye', stats['summary']['penalized_members']]
        ], columns=['Özellik', 'Değer']).to_excel(writer, sheet_name='Özet', index=False)
        
        pd.DataFrame([(m['name'], m['borrow_count']) for m in stats['most_active']], 
                    columns=['Üye', 'Adet']).to_excel(writer, sheet_name='En Çok Ödünç Alanlar', index=False)
        
        pd.DataFrame([(m['name'], m['penalty_until']) for m in stats['penalized']], 
                    columns=['Üye', 'Ceza Bitiş']).to_excel(writer, sheet_name='Cezalılar', index=False)
        
        pd.DataFrame([(m['name'], m['overdue_count']) for m in stats['most_overdue']], 
                    columns=['Üye', 'Gecikme Sayısı']).to_excel(writer, sheet_name='En Çok Gecikme Yapanlar', index=False)
    
    return send_file(temp_path, as_attachment=True, download_name='uye_istatistikleri.xlsx', 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Shelf Map API
@app.route('/api/shelf-map')
def api_shelf_map():
    books = Book.query.all()
    data = []
    for book in books:
        data.append({
            'title': book.title,
            'isbn': book.isbn,
            'shelf': book.shelf,
            'cupboard': book.cupboard,
            'image_url': book.image_path
        })
    return jsonify({'books': data})

# Online Borrow APIs
@app.route('/api/online-borrow/request', methods=['POST'])
@login_required
def api_online_borrow_request():
    """Online ödünç alma talebi oluştur"""
    result = process_online_borrow_request(request.json)
    return jsonify(result)

@app.route('/api/online-borrow/requests')
@login_required
def api_get_online_borrow_requests():
    """Kullanıcının online ödünç alma taleplerini getir"""
    if current_user.role in ['admin', 'librarian']:
        # Admin/librarian tüm talepleri görebilir
        requests = db.session.query(OnlineBorrowRequest, Book, Member)\
            .join(Book, OnlineBorrowRequest.isbn == Book.isbn)\
            .join(Member, OnlineBorrowRequest.member_id == Member.id)\
            .order_by(OnlineBorrowRequest.created_at.desc()).all()
    else:
        # Normal kullanıcı sadece kendi taleplerini görebilir
        requests = db.session.query(OnlineBorrowRequest, Book, Member)\
            .join(Book, OnlineBorrowRequest.isbn == Book.isbn)\
            .join(Member, OnlineBorrowRequest.member_id == Member.id)\
            .filter(OnlineBorrowRequest.user_id == current_user.id)\
            .order_by(OnlineBorrowRequest.created_at.desc()).all()
    
    requests_data = []
    for req, book, member in requests:
        requests_data.append({
            'id': req.id,
            'isbn': req.isbn,
            'book_title': book.title,
            'member_name': member.ad_soyad,
            'pickup_date': req.pickup_date,
            'pickup_time': req.pickup_time,
            'status': req.status,
            'notes': req.notes,
            'created_at': req.created_at.strftime('%d.%m.%Y %H:%M'),
            'approved_at': req.approved_at.strftime('%d.%m.%Y %H:%M') if req.approved_at else None,
            'approved_by': req.approved_by
        })
    
    return jsonify({'requests': requests_data})

@app.route('/api/online-borrow/approve/<int:request_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_approve_online_borrow(request_id):
    """Online ödünç alma talebini onayla"""
    result = approve_online_borrow_request(request_id)
    return jsonify(result)

@app.route('/api/online-borrow/reject/<int:request_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_reject_online_borrow(request_id):
    """Online ödünç alma talebini reddet"""
    data = request.json
    reason = data.get('reason', '')
    result = reject_online_borrow_request(request_id, reason)
    return jsonify(result)

@app.route('/api/online-borrow/cancel/<int:request_id>', methods=['POST'])
@login_required
def api_cancel_online_borrow(request_id):
    """Online ödünç alma talebini iptal et"""
    online_request = OnlineBorrowRequest.query.get_or_404(request_id)
    
    # Sadece talep sahibi iptal edebilir
    if online_request.user_id != current_user.id and current_user.role not in ['admin', 'librarian']:
        return jsonify({'success': False, 'message': 'Bu işlem için yetkiniz yok'}), 403
    
    if online_request.status != 'pending':
        return jsonify({'success': False, 'message': 'Bu talep artık iptal edilemez'}), 400
    
    # Talebi iptal et
    online_request.status = 'cancelled'
    online_request.approved_at = datetime.utcnow()
    online_request.approved_by = current_user.username
    
    db.session.commit()
    
    log_activity('cancel_online_borrow', f'Online ödünç alma iptal edildi: ID {request_id}')
    
    return jsonify({
        'success': True, 
        'message': 'Ödünç alma talebi iptal edildi'
    })

# QR Code APIs
@app.route('/api/qr/generate', methods=['POST'])
@login_required
def api_generate_qr():
    """QR kod oluştur"""
    result = generate_user_qr()
    return jsonify({
        'success': True,
        **result
    })

@app.route('/api/qr/status/<token>')
def api_qr_status(token):
    """QR kod durumunu kontrol et"""
    result = verify_qr_code(token)
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/api/qr/verify/<token>', methods=['POST'])
def api_verify_qr(token):
    """QR kodu doğrula ve kullanıcıyı giriş yap"""
    result = verify_qr_code(token)
    
    if not result['success']:
        return jsonify(result), 400
    
    # QR kodu kullanıldı olarak işaretle
    if use_qr_code(token):
        # Kullanıcıyı giriş yap
        user = User.query.get(QRCode.query.filter_by(token=token).first().user_id)
        from flask_login import login_user
        login_user(user)
        
        log_activity('qr_login', f'QR kod ile giriş: {user.username}')
        
        return jsonify({
            'success': True,
            'message': 'QR kod doğrulandı ve giriş yapıldı',
            'user_info': {
                'username': user.username,
                'email': user.email
            }
        })
    else:
        return jsonify({'success': False, 'message': 'QR kod kullanılamadı'}), 400

# Mobile and Self-Check APIs
@app.route('/api/mobile/scan-book/<isbn>')
@login_required
def api_mobile_scan_book(isbn):
    """Mobil cihazda kitap QR kodu tarama"""
    # Kitap kontrolü
    book = Book.query.get(isbn)
    if not book:
        return jsonify({'success': False, 'message': 'Kitap bulunamadı'}), 404
    
    # Üye kontrolü
    member = Member.query.filter_by(user_id=current_user.id).first()
    if not member:
        return jsonify({'success': False, 'message': 'Üye kaydınız bulunamadı'}), 404
    
    # Ceza kontrolü
    if member.penalty_until and datetime.now() < member.penalty_until:
        return jsonify({'success': False, 'message': 'Ceza süreniz devam ediyor'}), 403
    
    # Kullanılabilirlik kontrolü
    borrowed_count = Transaction.query.filter_by(isbn=isbn, return_date=None).count()
    available = book.quantity - borrowed_count
    
    # Kullanıcının bu kitabı ödünç alıp almadığını kontrol et
    user_borrowed = Transaction.query.filter_by(
        isbn=isbn, 
        member_id=member.id, 
        return_date=None
    ).first()
    
    return jsonify({
        'success': True,
        'book_info': {
            'title': book.title,
            'authors': book.authors,
            'isbn': book.isbn,
            'available': available,
            'total': book.quantity,
            'user_borrowed': user_borrowed is not None
        },
        'member_info': {
            'name': member.ad_soyad,
            'active_borrows': Transaction.query.filter_by(member_id=member.id, return_date=None).count(),
            'max_books': int(get_setting('max_books_per_member', '5'))
        }
    })

@app.route('/api/mobile/borrow/<isbn>', methods=['POST'])
@login_required
def api_mobile_borrow(isbn):
    """Mobil cihazda ödünç alma işlemi"""
    data = request.json or {}
    notes = data.get('notes', 'Mobil QR kod ile ödünç alındı')
    
    # Üye kontrolü
    member = Member.query.filter_by(user_id=current_user.id).first()
    if not member:
        return jsonify({'success': False, 'message': 'Üye kaydınız bulunamadı'}), 404
    
    # Gelişmiş işlem API'sini kullan
    return process_borrow_transaction(
        book=Book.query.get(isbn),
        member=member,
        method='qr',
        notes=notes
    )

@app.route('/api/mobile/return/<isbn>', methods=['POST'])
@login_required
def api_mobile_return(isbn):
    """Mobil cihazda iade işlemi"""
    data = request.json or {}
    notes = data.get('notes', 'Mobil QR kod ile iade edildi')
    
    # Üye kontrolü
    member = Member.query.filter_by(user_id=current_user.id).first()
    if not member:
        return jsonify({'success': False, 'message': 'Üye kaydınız bulunamadı'}), 404
    
    # Gelişmiş işlem API'sini kullan
    return process_return_transaction(
        book=Book.query.get(isbn),
        member=member,
        method='qr',
        notes=notes
    )

@app.route('/api/mobile/my-books')
@login_required
def api_mobile_my_books():
    """Mobil cihazda kullanıcının kitaplarını getir"""
    member = Member.query.filter_by(user_id=current_user.id).first()
    if not member:
        return jsonify({'success': False, 'message': 'Üye kaydınız bulunamadı'}), 404
    
    # Aktif ödünç alınan kitaplar
    active_transactions = db.session.query(Transaction, Book)\
        .join(Book, Transaction.isbn == Book.isbn)\
        .filter(Transaction.member_id == member.id, Transaction.return_date == None)\
        .all()
    
    books_data = []
    for transaction, book in active_transactions:
        due_date = datetime.strptime(transaction.due_date, '%Y-%m-%d')
        days_remaining = (due_date.date() - datetime.now().date()).days
        is_overdue = days_remaining < 0
        
        books_data.append({
            'transaction_id': transaction.id,
            'isbn': book.isbn,
            'title': book.title,
            'authors': book.authors,
            'borrow_date': transaction.borrow_date,
            'due_date': transaction.due_date,
            'days_remaining': days_remaining,
            'is_overdue': is_overdue,
            'fine_amount': abs(days_remaining) * float(get_setting('daily_fine_amount', '1.0')) if is_overdue else 0,
            'cover_image': book.image_path if book.image_path else None
        })
    
    return jsonify({
        'success': True,
        'books': books_data,
        'total_books': len(books_data)
    })

# Quick Search APIs
@app.route('/api/books/search/quick')
def api_books_quick_search():
    """Hızlı kitap arama API'si - online ve QR kod işlemleri için"""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    result = quick_search_books(query, limit)
    return jsonify(result)

@app.route('/api/members/search/quick')
def api_members_quick_search():
    """Hızlı üye arama API'si - online ve QR kod işlemleri için"""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    result = quick_search_members(query, limit)
    return jsonify(result)

@app.route('/api/books/search')
def api_books_search():
    """Kitap arama API'si"""
    try:
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '')
        availability = request.args.get('availability', '')
        limit = request.args.get('limit', 20, type=int)
        
        # Base query
        books_query = Book.query
        
        # Arama filtresi
        if query:
            books_query = books_query.filter(
                db.or_(
                    Book.title.contains(query),
                    Book.authors.contains(query),
                    Book.isbn.contains(query)
                )
            )
        
        # Kategori filtresi
        if category:
            books_query = books_query.join(BookCategory).filter(
                BookCategory.category_id == category
            )
        
        # Mevcutluk filtresi
        if availability == 'available':
            books_query = books_query.filter(Book.quantity > Book.total_borrow_count)
        elif availability == 'unavailable':
            books_query = books_query.filter(Book.quantity <= Book.total_borrow_count)
        
        # Limit uygula
        books = books_query.limit(limit).all()
        
        # Sonuçları formatla
        result = []
        for book in books:
            # Get category name
            category_obj = db.session.query(Category).join(BookCategory, Category.id == BookCategory.category_id)\
                .filter(BookCategory.book_isbn == book.isbn).first()
            category_name = category_obj.name if category_obj else 'Genel'
            
            result.append({
                'isbn': book.isbn,
                'title': book.title,
                'authors': book.authors,
                'image_path': book.image_path,
                'quantity': book.quantity,
                'borrowed_count': book.total_borrow_count,
                'category_name': category_name
            })
        
        return jsonify({'books': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Statistics APIs
@app.route('/api/books/stats')
def api_books_stats():
    """Kitap istatistiklerini getir"""
    try:
        total_books = Book.query.count()
        available_books = db.session.query(Book).join(Transaction, Book.isbn == Transaction.isbn)\
            .filter(Transaction.return_date.is_(None)).count()
        available_books = total_books - available_books
        
        return jsonify({
            'success': True,
            'total_books': total_books,
            'available_books': available_books
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stats')
@login_required
def api_stats():
    """İstatistikleri döndür"""
    try:
        # Toplam kitap sayısı
        total_books = Book.query.count()
        
        # Mevcut kitap sayısı
        available_books = db.session.query(Book).filter(
            Book.quantity > Book.total_borrow_count
        ).count()
        
        # Kullanıcının rezervasyon sayısı
        my_requests = OnlineBorrowRequest.query.filter_by(
            user_id=current_user.id
        ).count()
        
        # QR tarama sayısı (localStorage'dan alınacak, şimdilik 0)
        qr_scans = 0
        
        return jsonify({
            'total_books': total_books,
            'available_books': available_books,
            'my_requests': my_requests,
            'qr_scans': qr_scans
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/my-books')
@login_required
def api_my_books():
    """Kullanıcının ödünç aldığı kitapları döndür"""
    try:
        # Kullanıcının üye ID'sini bul
        member = Member.query.filter_by(user_id=current_user.id).first()
        if not member:
            return jsonify({'books': []})
        
        # Aktif ödünç işlemlerini al
        transactions = Transaction.query.filter_by(
            member_id=member.id,
            return_date=None
        ).all()
        
        books = []
        for transaction in transactions:
            book = Book.query.get(transaction.isbn)
            if book:
                books.append({
                    'isbn': book.isbn,
                    'title': book.title,
                    'authors': book.authors,
                    'image_path': book.image_path,
                    'borrow_date': transaction.borrow_date,
                    'due_date': transaction.due_date
                })
        
        return jsonify({'books': books})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/recommendations')
@login_required
def api_books_recommendations():
    """Kitap önerilerini döndür"""
    try:
        # Basit öneri sistemi - en popüler kitapları döndür
        popular_books = Book.query.order_by(Book.total_borrow_count.desc()).limit(6).all()
        
        recommendations = []
        for book in popular_books:
            recommendations.append({
                'isbn': book.isbn,
                'title': book.title,
                'authors': book.authors,
                'image_path': book.image_path,
                'recommendation_reason': 'Popüler kitap'
            })
        
        return jsonify({'recommendations': recommendations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Reports API
@app.route('/api/reports/export')
@login_required
@role_required('admin')
def api_export_report():
    """Export report as PDF"""
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    format_type = request.args.get('format', 'pdf')
    
    # For now, return a simple JSON response
    # In a real application, you would generate a PDF using ReportLab
    return jsonify({
        'message': 'Rapor dışa aktarma özelliği yakında eklenecek',
        'start_date': start_date,
        'end_date': end_date,
        'format': format_type
    })

# Transaction Processing API
@app.route('/api/transactions/process', methods=['POST'])
@login_required
def api_process_transaction():
    """Gelişmiş işlem işleme API'si - online ve QR kod işlemleri için"""
    data = request.json
    action = data.get('action')  # 'borrow' veya 'return'
    isbn = data.get('isbn')
    member_id = data.get('member_id')
    method = data.get('method', 'manual')  # 'online', 'qr', 'manual'
    notes = data.get('notes', '')
    
    if not all([action, isbn, member_id]):
        return jsonify({'success': False, 'message': 'Eksik parametreler'}), 400
    
    # Kitap kontrolü
    book = Book.query.get(isbn)
    if not book:
        return jsonify({'success': False, 'message': 'Kitap bulunamadı'}), 404
    
    # Üye kontrolü
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'success': False, 'message': 'Üye bulunamadı'}), 404
    
    if action == 'borrow':
        return process_borrow_transaction(book, member, method, notes)
    elif action == 'return':
        return process_return_transaction(book, member, method, notes)
    else:
        return jsonify({'success': False, 'message': 'Geçersiz işlem türü'}), 400
