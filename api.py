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

from config import app, get_setting
from models import db, User, Book, Member, Transaction, Category, BookCategory, Notification, SearchHistory, Review, Reservation, Fine, ActivityLog, Settings, EmailTemplate, OnlineBorrowRequest, QRCode
from utils import (log_activity, fetch_book_info_from_api, calculate_fine, 
                   send_email, add_notification, generate_qr_code, save_qr_code)
from routes import role_required

# Books API
@app.route('/api/books')
def api_get_books():
    """API endpoint to get all books"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = Book.query
    
    if search:
        query = query.filter(
            db.or_(
                Book.isbn.contains(search),
                Book.title.contains(search),
                Book.authors.contains(search)
            )
        )
    
    books = query.paginate(page=page, per_page=per_page, error_out=False)
    
    books_data = []
    for book in books.items:
        borrowed_count = Transaction.query.filter_by(isbn=book.isbn, return_date=None).count()
        available = book.quantity - borrowed_count
        
        # Get categories
        categories = db.session.query(Category.name).join(BookCategory)\
            .filter(BookCategory.book_isbn == book.isbn).all()
        category_names = [cat[0] for cat in categories]
        
        books_data.append({
            'isbn': book.isbn,
            'title': book.title,
            'authors': book.authors,
            'publish_date': book.publish_date,
            'number_of_pages': book.number_of_pages,
            'publishers': book.publishers,
            'languages': book.languages,
            'quantity': book.quantity,
            'borrowed': borrowed_count,
            'available': available,
            'shelf': book.shelf,
            'cupboard': book.cupboard,
            'categories': ', '.join(category_names),
            'image_path': book.image_path
        })
    
    return jsonify({
        'books': books_data,
        'total': books.total,
        'pages': books.pages,
        'current_page': page
    })

@app.route('/api/books/fetch', methods=['POST'])
def api_fetch_books():
    """Fetch book information from Open Library API"""
    isbns = request.json.get('isbns', [])
    results = []
    
    for isbn in isbns:
        book_info = fetch_book_info_from_api(isbn)
        if book_info:
            results.append(book_info)
        else:
            results.append({
                'isbn': isbn,
                'title': 'Bilgi Bulunamadı',
                'authors': 'Bilgi Bulunamadı',
                'error': True
            })
    
    return jsonify({'books': results})

@app.route('/api/books/add', methods=['POST'])
def api_add_book():
    """Add a new book to the database"""
    data = request.json
    
    try:
        book = Book(
            isbn=data['isbn'],
            title=data['title'],
            authors=data['authors'],
            publish_date=data.get('publish_date', ''),
            number_of_pages=data.get('number_of_pages', 0),
            publishers=data.get('publishers', ''),
            languages=data.get('languages', ''),
            quantity=data.get('quantity', 1),
            shelf=data.get('shelf', ''),
            cupboard=data.get('cupboard', ''),
            image_path=data.get('image_url', '')
        )
        db.session.add(book)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Kitap başarıyla eklendi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/books/<isbn>', methods=['PUT'])
def api_update_book(isbn):
    """Update book information"""
    book = Book.query.get_or_404(isbn)
    data = request.json
    
    book.title = data.get('title', book.title)
    book.authors = data.get('authors', book.authors)
    book.publish_date = data.get('publish_date', book.publish_date)
    book.number_of_pages = data.get('number_of_pages', book.number_of_pages)
    book.publishers = data.get('publishers', book.publishers)
    book.languages = data.get('languages', book.languages)
    book.quantity = data.get('quantity', book.quantity)
    book.shelf = data.get('shelf', book.shelf)
    book.cupboard = data.get('cupboard', book.cupboard)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Kitap güncellendi'})

@app.route('/api/books/<isbn>', methods=['GET'])
def api_get_book(isbn):
    """Get single book information"""
    book = Book.query.get_or_404(isbn)
    
    return jsonify({
        'isbn': book.isbn,
        'title': book.title,
        'authors': book.authors,
        'publish_date': book.publish_date,
        'number_of_pages': book.number_of_pages,
        'publishers': book.publishers,
        'languages': book.languages,
        'quantity': book.quantity,
        'shelf': book.shelf,
        'cupboard': book.cupboard,
        'image_path': book.image_path
    })

@app.route('/api/books/<isbn>', methods=['DELETE'])
def api_delete_book(isbn):
    """Delete a book"""
    book = Book.query.get_or_404(isbn)
    
    # Check if book is borrowed
    if Transaction.query.filter_by(isbn=isbn, return_date=None).first():
        return jsonify({'success': False, 'message': 'Ödünç verilmiş kitap silinemez'}), 400
    
    # Delete related records
    BookCategory.query.filter_by(book_isbn=isbn).delete()
    Transaction.query.filter_by(isbn=isbn).delete()
    Notification.query.filter_by(related_isbn=isbn).delete()
    
    db.session.delete(book)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Kitap silindi'})

@app.route('/api/books/<isbn>/review', methods=['POST'])
@login_required
def add_review(isbn):
    """Add or update book review"""
    book = Book.query.get_or_404(isbn)
    
    rating = request.json.get('rating')
    comment = request.json.get('comment', '')
    
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Geçersiz puan'}), 400
    
    # Check if user already reviewed
    review = Review.query.filter_by(isbn=isbn, user_id=current_user.id).first()
    
    if review:
        # Update existing review
        review.rating = rating
        review.comment = comment
        review.updated_at = datetime.utcnow()
    else:
        # Create new review
        review = Review(
            isbn=isbn,
            user_id=current_user.id,
            rating=rating,
            comment=comment
        )
        db.session.add(review)
        book.review_count += 1
    
    # Update book average rating
    all_reviews = Review.query.filter_by(isbn=isbn).all()
    total_rating = sum(r.rating for r in all_reviews)
    book.average_rating = total_rating / len(all_reviews) if all_reviews else 0
    
    db.session.commit()
    
    log_activity('add_review', f'Reviewed book: {book.title} ({rating} stars)')
    
    return jsonify({'success': True, 'message': 'Değerlendirmeniz kaydedildi'})

@app.route('/api/books/<isbn>/reserve', methods=['POST'])
@login_required
def reserve_book(isbn):
    """Reserve a book"""
    book = Book.query.get_or_404(isbn)
    
    # Check if book is available
    borrowed_count = Transaction.query.filter_by(isbn=isbn, return_date=None).count()
    if book.quantity > borrowed_count:
        return jsonify({'success': False, 'message': 'Kitap zaten mevcut, direkt ödünç alabilirsiniz'}), 400
    
    # Check if user already has an active reservation
    existing = Reservation.query.filter_by(
        isbn=isbn, user_id=current_user.id, status='active'
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'Bu kitap için zaten rezervasyonunuz var'}), 400
    
    # Get member
    member = Member.query.filter_by(user_id=current_user.id).first()
    if not member:
        return jsonify({'success': False, 'message': 'Üye kaydınız bulunamadı'}), 404
    
    # Calculate queue position
    last_reservation = Reservation.query.filter_by(isbn=isbn, status='active')\
        .order_by(Reservation.queue_position.desc()).first()
    queue_position = (last_reservation.queue_position + 1) if last_reservation else 1
    
    # Create reservation
    reservation = Reservation(
        isbn=isbn,
        user_id=current_user.id,
        member_id=member.id,
        queue_position=queue_position,
        expiry_date=datetime.utcnow() + timedelta(days=int(get_setting('reservation_expiry_days', '3')))
    )
    db.session.add(reservation)
    db.session.commit()
    
    # Send notification email
    send_email(current_user.email, 'reservation_confirmation', {
        'member_name': current_user.username,
        'book_title': book.title,
        'queue_position': queue_position
    })
    
    log_activity('reserve_book', f'Reserved book: {book.title}')
    
    return jsonify({
        'success': True,
        'message': f'Rezervasyonunuz alındı. Sıranız: {queue_position}'
    })

@app.route('/api/books/<isbn>/availability')
def api_book_availability(isbn):
    """Check book availability"""
    book = Book.query.get_or_404(isbn)
    borrowed_count = Transaction.query.filter_by(isbn=isbn, return_date=None).count()
    available_count = book.quantity - borrowed_count
    
    return jsonify({
        'available': available_count > 0,
        'title': book.title,
        'total_count': book.quantity,
        'available_count': available_count,
        'borrowed_count': borrowed_count
    })

@app.route('/api/books/<isbn>/categories', methods=['GET', 'POST'])
def api_book_categories(isbn):
    """Get or update book categories"""
    if request.method == 'GET':
        categories = db.session.query(Category).join(BookCategory)\
            .filter(BookCategory.book_isbn == isbn).all()
        
        categories_data = []
        for cat in categories:
            categories_data.append({
                'id': cat.id,
                'name': cat.name
            })
        
        return jsonify({'categories': categories_data})
    
    else:  # POST
        # Delete existing categories
        BookCategory.query.filter_by(book_isbn=isbn).delete()
        
        # Add new categories
        category_ids = request.json.get('category_ids', [])
        for cat_id in category_ids:
            book_cat = BookCategory(book_isbn=isbn, category_id=cat_id)
            db.session.add(book_cat)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Kategoriler güncellendi'})

@app.route('/api/books/<isbn>/details')
def api_get_book_details(isbn):
    """Kitap detaylarını döndür"""
    try:
        book = Book.query.get(isbn)
        if not book:
            return jsonify({'success': False, 'message': 'Kitap bulunamadı'})
        
        # Get category name
        category = db.session.query(Category).join(BookCategory, Category.id == BookCategory.category_id)\
            .filter(BookCategory.book_isbn == isbn).first()
        category_name = category.name if category else 'Genel'
        
        return jsonify({
            'success': True,
            'book': {
                'isbn': book.isbn,
                'title': book.title,
                'authors': book.authors,
                'image_path': book.image_path,
                'quantity': book.quantity,
                'borrowed_count': book.total_borrow_count,
                'category_name': category_name,
                'description': book.description,
                'publishers': book.publishers,
                'publish_date': book.publish_date
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Members API
@app.route('/api/members')
def api_get_members():
    """API endpoint to get all members"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = Member.query
    
    if search:
        query = query.filter(
            db.or_(
                Member.ad_soyad.contains(search),
                Member.numara.contains(search),
                Member.uye_turu.contains(search)
            )
        )
    
    members = query.paginate(page=page, per_page=per_page, error_out=False)
    
    members_data = []
    for member in members.items:
        members_data.append({
            'id': member.id,
            'ad_soyad': member.ad_soyad,
            'sinif': member.sinif,
            'numara': member.numara,
            'email': member.email,
            'uye_turu': member.uye_turu
        })
    
    return jsonify({
        'members': members_data,
        'total': members.total,
        'pages': members.pages,
        'current_page': page
    })

@app.route('/api/members', methods=['POST'])
def api_add_member():
    """Add a new member"""
    data = request.json
    
    try:
        member = Member(
            ad_soyad=data['ad_soyad'],
            sinif=data['sinif'],
            numara=data['numara'],
            email=data.get('email', ''),
            uye_turu=data.get('uye_turu', 'Öğrenci')
        )
        db.session.add(member)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Üye başarıyla eklendi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/members/<int:id>', methods=['PUT'])
def api_update_member(id):
    """Update member information"""
    member = Member.query.get_or_404(id)
    data = request.json
    
    member.ad_soyad = data.get('ad_soyad', member.ad_soyad)
    member.sinif = data.get('sinif', member.sinif)
    member.numara = data.get('numara', member.numara)
    member.email = data.get('email', member.email)
    member.uye_turu = data.get('uye_turu', member.uye_turu)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Üye güncellendi'})

@app.route('/api/members/<int:id>', methods=['DELETE'])
def api_delete_member(id):
    """Delete a member"""
    member = Member.query.get_or_404(id)
    
    # Check if member has unreturned books
    if Transaction.query.filter_by(member_id=id, return_date=None).first():
        return jsonify({'success': False, 'message': 'İade edilmemiş kitabı olan üye silinemez'}), 400
    
    db.session.delete(member)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Üye silindi'})

@app.route('/api/members/by-school-no/<school_no>')
def api_member_by_school_no(school_no):
    """Get member by school number"""
    member = Member.query.filter_by(numara=school_no).first_or_404()
    current_borrowed = Transaction.query.filter_by(member_id=member.id, return_date=None).count()
    
    return jsonify({
        'id': member.id,
        'ad_soyad': member.ad_soyad,
        'sinif': member.sinif,
        'numara': member.numara,
        'email': member.email,
        'uye_turu': member.uye_turu,
        'current_borrowed': current_borrowed,
        'reliability_score': member.reliability_score
    })

@app.route('/api/members/<int:id>')
def api_get_member(id):
    """Get member details"""
    member = Member.query.get_or_404(id)
    
    return jsonify({
        'id': member.id,
        'ad_soyad': member.ad_soyad,
        'sinif': member.sinif,
        'numara': member.numara,
        'email': member.email,
        'uye_turu': member.uye_turu,
        'phone': member.phone,
        'address': member.address,
        'join_date': member.join_date.isoformat() if member.join_date else None,
        'total_borrowed': member.total_borrowed,
        'current_borrowed': member.current_borrowed,
        'reliability_score': member.reliability_score
    })

@app.route('/api/members/<int:id>/borrows')
def api_member_borrows(id):
    """Get member's active borrows"""
    borrows = db.session.query(Transaction, Book)\
        .join(Book, Transaction.isbn == Book.isbn)\
        .filter(Transaction.member_id == id, Transaction.return_date == None)\
        .all()
    
    borrows_data = []
    for trans, book in borrows:
        borrows_data.append({
            'id': trans.id,
            'isbn': trans.isbn,
            'book_title': book.title,
            'borrow_date': trans.borrow_date,
            'due_date': trans.due_date
        })
    
    return jsonify({'borrows': borrows_data})

@app.route('/api/members/<int:member_id>/details')
def api_member_details(member_id):
    """Üye detaylarını getir - online ve QR kod işlemleri için"""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'success': False, 'message': 'Üye bulunamadı'}), 404
    
    # Aktif ödünç alınan kitaplar
    active_transactions = db.session.query(Transaction, Book)\
        .join(Book, Transaction.isbn == Book.isbn)\
        .filter(Transaction.member_id == member_id, Transaction.return_date == None)\
        .all()
    
    active_books = []
    for transaction, book in active_transactions:
        due_date = datetime.strptime(transaction.due_date, '%Y-%m-%d')
        days_remaining = (due_date.date() - datetime.now().date()).days
        is_overdue = days_remaining < 0
        
        active_books.append({
            'transaction_id': transaction.id,
            'isbn': book.isbn,
            'title': book.title,
            'authors': book.authors,
            'borrow_date': transaction.borrow_date,
            'due_date': transaction.due_date,
            'days_remaining': days_remaining,
            'is_overdue': is_overdue,
            'fine_amount': abs(days_remaining) * float(get_setting('daily_fine_amount', '1.0')) if is_overdue else 0
        })
    
    # Son işlemler
    recent_transactions = db.session.query(Transaction, Book)\
        .join(Book, Transaction.isbn == Book.isbn)\
        .filter(Transaction.member_id == member_id)\
        .order_by(Transaction.borrow_date.desc())\
        .limit(10).all()
    
    recent_activity = []
    for transaction, book in recent_transactions:
        recent_activity.append({
            'book_title': book.title,
            'borrow_date': transaction.borrow_date,
            'return_date': transaction.return_date,
            'status': 'Aktif' if not transaction.return_date else 'İade edildi'
        })
    
    # Ceza durumu
    has_penalty = member.penalty_until and datetime.now() < member.penalty_until
    
    return jsonify({
        'success': True,
        'member': {
            'id': member.id,
            'ad_soyad': member.ad_soyad,
            'sinif': member.sinif,
            'numara': member.numara,
            'email': member.email,
            'phone': member.phone,
            'uye_turu': member.uye_turu,
            'address': member.address,
            'join_date': member.join_date.strftime('%d.%m.%Y') if member.join_date else None,
            'total_borrowed': member.total_borrowed,
            'current_borrowed': member.current_borrowed,
            'reliability_score': member.reliability_score,
            'has_penalty': has_penalty,
            'penalty_until': member.penalty_until.strftime('%d.%m.%Y') if member.penalty_until else None
        },
        'active_books': active_books,
        'recent_activity': recent_activity
    })

# Transactions API
@app.route('/api/transactions')
def api_get_transactions():
    """API endpoint to get all transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', 'all')  # all, active, returned
    
    query = db.session.query(Transaction, Book, Member)\
        .join(Book, Transaction.isbn == Book.isbn)\
        .join(Member, Transaction.member_id == Member.id)
    
    if status == 'active':
        query = query.filter(Transaction.return_date == None)
    elif status == 'returned':
        query = query.filter(Transaction.return_date != None)
    
    transactions = query.order_by(Transaction.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    max_renew = int(get_setting('max_renew_count', '2'))
    transactions_data = []
    for trans, book, member in transactions.items:
        can_renew = (trans.return_date is None and trans.renew_count < max_renew)
        transactions_data.append({
            'id': trans.id,
            'isbn': trans.isbn,
            'book_title': book.title,
            'member_id': trans.member_id,
            'member_name': member.ad_soyad,
            'borrow_date': trans.borrow_date,
            'due_date': trans.due_date,
            'return_date': trans.return_date,
            'is_overdue': trans.return_date is None and trans.due_date < datetime.now().strftime("%Y-%m-%d"),
            'can_renew': can_renew
        })
    
    return jsonify({
        'transactions': transactions_data,
        'total': transactions.total,
        'pages': transactions.pages,
        'current_page': page
    })

@app.route('/api/transactions/borrow', methods=['POST'])
def api_borrow_book():
    """Borrow a book"""
    data = request.json
    isbn = data.get('isbn')
    school_no = data.get('school_no')
    due_date = data.get('due_date')
    
    # Find member by school number
    member = Member.query.filter_by(numara=school_no).first()
    if not member:
        return jsonify({'success': False, 'message': 'Üye bulunamadı'}), 404
    
    # Ceza kontrolü
    now = datetime.now()
    if member.penalty_until:
        try:
            penalty_dt = member.penalty_until
            if isinstance(penalty_dt, str):
                penalty_dt = datetime.fromisoformat(penalty_dt)
        except:
            penalty_dt = now
        if penalty_dt and now < penalty_dt:
            return jsonify({'success': False, 'message': f"Bu üye {penalty_dt.strftime('%d.%m.%Y')} tarihine kadar ödünç alamaz (cezalı)."}), 403
    
    # Check book availability
    book = Book.query.get(isbn)
    if not book:
        return jsonify({'success': False, 'message': 'Kitap bulunamadı'}), 404
    
    borrowed_count = Transaction.query.filter_by(isbn=isbn, return_date=None).count()
    if book.quantity <= borrowed_count:
        return jsonify({'success': False, 'message': 'Kitap mevcut değil'}), 400
    
    # Create transaction
    transaction = Transaction(
        isbn=isbn,
        member_id=member.id,
        borrow_date=datetime.now().strftime("%Y-%m-%d"),
        due_date=due_date
    )
    
    # Update book statistics
    book.last_borrowed_date = datetime.now().strftime("%Y-%m-%d")
    book.total_borrow_count += 1
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Kitap ödünç verildi'})

@app.route('/api/transactions/return', methods=['POST'])
def api_return_book():
    """Return a book"""
    data = request.json
    isbn = data.get('isbn')
    school_no = data.get('school_no')
    
    # Find member
    member = Member.query.filter_by(numara=school_no).first()
    if not member:
        return jsonify({'success': False, 'message': 'Üye bulunamadı'}), 404
    
    # Find active transaction
    transaction = Transaction.query.filter_by(
        isbn=isbn,
        member_id=member.id,
        return_date=None
    ).first()
    
    if not transaction:
        return jsonify({'success': False, 'message': 'Aktif ödünç işlemi bulunamadı'}), 404
    
    # Update transaction
    transaction.return_date = datetime.now().strftime("%Y-%m-%d")
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Kitap iade alındı'})

@app.route('/api/transactions/overdue')
def api_get_overdue():
    """Get overdue transactions"""
    overdue = db.session.query(Transaction, Book, Member)\
        .join(Book, Transaction.isbn == Book.isbn)\
        .join(Member, Transaction.member_id == Member.id)\
        .filter(Transaction.return_date == None)\
        .filter(Transaction.due_date < datetime.now().strftime("%Y-%m-%d"))\
        .order_by(Transaction.due_date).all()
    
    overdue_data = []
    for trans, book, member in overdue:
        overdue_data.append({
            'id': trans.id,
            'isbn': trans.isbn,
            'book_title': book.title,
            'member_name': member.ad_soyad,
            'due_date': trans.due_date,
            'days_overdue': (datetime.now() - datetime.strptime(trans.due_date, "%Y-%m-%d")).days
        })
    
    return jsonify({'overdue': overdue_data})

@app.route('/api/transactions/<int:id>/renew', methods=['POST'])
@login_required
def api_renew_transaction(id):
    """Renew a book loan"""
    transaction = Transaction.query.get_or_404(id)
    
    # Check permissions: either own transaction or admin/librarian
    has_permission = False
    
    # Check if user is admin or librarian
    if current_user.role in ['admin', 'librarian']:
        has_permission = True
    else:
        # Check if user owns this transaction
        member = Member.query.filter_by(user_id=current_user.id).first()
        if member and transaction.member_id == member.id:
            has_permission = True
    
    if not has_permission:
        return jsonify({'success': False, 'message': 'Bu işlem için yetkiniz yok'}), 403
    
    # Check if already returned
    if transaction.return_date:
        return jsonify({'success': False, 'message': 'Bu kitap zaten iade edilmiş'}), 400
    
    # Check renew limit
    max_renew = int(get_setting('max_renew_count', '2'))
    if transaction.renew_count >= max_renew:
        return jsonify({'success': False, 'message': 'Maksimum yenileme sayısına ulaştınız'}), 400
    
    # Extend due date by original loan period
    loan_days = int(get_setting('max_borrow_days', '14'))
    current_due = datetime.strptime(transaction.due_date, '%Y-%m-%d')
    new_due = current_due + timedelta(days=loan_days)
    
    transaction.due_date = new_due.strftime('%Y-%m-%d')
    transaction.renew_count += 1
    
    db.session.commit()
    
    log_activity('renew_book', f'Renewed loan for transaction {id}')
    
    return jsonify({
        'success': True,
        'message': f'Süre {loan_days} gün uzatıldı. Yeni teslim tarihi: {transaction.due_date}'
    })

@app.route('/api/transactions/<int:id>/quick-return', methods=['POST'])
@login_required
def api_quick_return(id):
    """Quick return a book"""
    transaction = Transaction.query.get_or_404(id)
    if transaction.return_date:
        return jsonify({'success': False, 'message': 'Kitap zaten iade edilmiş'}), 400
    
    transaction.return_date = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate fine if overdue
    fine_amount = calculate_fine(transaction.due_date)
    if fine_amount > 0:
        transaction.fine_amount = fine_amount
        # Ceza uygula: 1 ay kitap alamama
        member = Member.query.get(transaction.member_id)
        if member:
            now = datetime.now()
            penalty_until = now + timedelta(days=30)
            if not member.penalty_until or (member.penalty_until and now > member.penalty_until):
                member.penalty_until = penalty_until
            else:
                # Ceza üstüne ekle
                member.penalty_until += timedelta(days=30)
        
        # Create fine record
        fine = Fine(
            user_id=current_user.id,
            member_id=transaction.member_id,
            transaction_id=transaction.id,
            amount=fine_amount,
            reason='late_return'
        )
        db.session.add(fine)
    
    db.session.commit()
    log_activity('quick_return', f'Quick returned book - Transaction ID: {id}')
    
    return jsonify({'success': True, 'message': 'Kitap iade alındı'})

@app.route('/api/transactions/stats')
def api_transaction_stats():
    """Get transaction statistics"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    active = Transaction.query.filter_by(return_date=None).count()
    today_due = Transaction.query.filter(
        Transaction.return_date == None,
        Transaction.due_date == today
    ).count()
    overdue = Transaction.query.filter(
        Transaction.return_date == None,
        Transaction.due_date < today
    ).count()
    today_transactions = Transaction.query.filter(
        db.or_(
            Transaction.borrow_date == today,
            Transaction.return_date == today
        )
    ).count()
    
    return jsonify({
        'active': active,
        'today_due': today_due,
        'overdue': overdue,
        'today_transactions': today_transactions
    })

@app.route('/api/transactions/check')
def api_check_transaction():
    """Check transaction by ISBN and school number"""
    isbn = request.args.get('isbn')
    school_no = request.args.get('school_no')
    
    member = Member.query.filter_by(numara=school_no).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    transaction = Transaction.query.filter_by(
        isbn=isbn,
        member_id=member.id,
        return_date=None
    ).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    due_date = datetime.strptime(transaction.due_date, '%Y-%m-%d')
    today = datetime.now()
    days_overdue = max(0, (today - due_date).days)
    
    return jsonify({
        'transaction': {
            'id': transaction.id,
            'borrow_date': transaction.borrow_date,
            'due_date': transaction.due_date,
            'days_overdue': days_overdue
        }
    })

# Categories API
@app.route('/api/categories')
def api_get_categories():
    """Get all categories"""
    categories = Category.query.all()
    categories_data = []
    
    for cat in categories:
        categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'description': cat.description
        })
    
    return jsonify({'categories': categories_data})

# Other API endpoints continue here...
# Export/Import APIs
@app.route('/api/export/books', methods=['GET'])
def api_export_books():
    """Export books to Excel"""
    books = Book.query.all()
    
    data = []
    for book in books:
        data.append({
            'ISBN': book.isbn,
            'Başlık': book.title,
            'Yazar': book.authors,
            'Yayın Yılı': book.publish_date,
            'Sayfa Sayısı': book.number_of_pages,
            'Yayınevi': book.publishers,
            'Diller': book.languages,
            'Adet': book.quantity,
            'Raf': book.shelf,
            'Dolap': book.cupboard
        })
    
    df = pd.DataFrame(data)
    
    # Create temporary file
    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(temp.name, index=False)
    temp.close()
    
    return send_file(temp.name, as_attachment=True, download_name='kitaplar.xlsx')

@app.route('/api/import/books', methods=['POST'])
def api_import_books():
    """Import books from Excel"""
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
                book = Book.query.get(row.get('ISBN'))
                if not book:
                    book = Book(isbn=row.get('ISBN'))
                
                book.title = row.get('Başlık', '')
                book.authors = row.get('Yazar', '')
                book.publish_date = str(row.get('Yayın Yılı', ''))
                book.number_of_pages = int(row.get('Sayfa Sayısı', 0)) if pd.notna(row.get('Sayfa Sayısı')) else 0
                book.publishers = row.get('Yayınevi', '')
                book.languages = row.get('Diller', '')
                book.quantity = int(row.get('Adet', 1)) if pd.notna(row.get('Adet')) else 1
                book.shelf = row.get('Raf', '')
                book.cupboard = row.get('Dolap', '')
                
                db.session.add(book)
            
            db.session.commit()
            os.remove(filepath)
            
            return jsonify({'success': True, 'message': f'{len(df)} kitap başarıyla yüklendi'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    
    return jsonify({'success': False, 'message': 'Geçersiz dosya formatı'}), 400

# Profile and User APIs
@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.json
    
    # Update user info
    if 'email' in data:
        # Check if email already exists
        existing = User.query.filter(
            User.email == data['email'],
            User.id != current_user.id
        ).first()
        if existing:
            return jsonify({'success': False, 'message': 'Bu e-posta adresi zaten kullanılıyor'}), 400
        current_user.email = data['email']
    
    if 'theme' in data:
        current_user.theme = data['theme']
    
    if 'language' in data:
        current_user.language = data['language']
    
    # Update member info if exists
    member = Member.query.filter_by(user_id=current_user.id).first()
    if member:
        if 'phone' in data:
            member.phone = data['phone']
        if 'address' in data:
            member.address = data['address']
    
    db.session.commit()
    
    log_activity('update_profile', 'Profile updated')
    
    return jsonify({'success': True, 'message': 'Profiliniz güncellendi'})

@app.route('/api/user/theme', methods=['POST'])
@login_required
def api_update_theme():
    """Update user theme preference"""
    theme = request.form.get('theme', 'light')
    if theme not in ['light', 'dark']:
        theme = 'light'
    
    current_user.theme = theme
    db.session.commit()
    
    return jsonify({'success': True})

# Advanced Search API
@app.route('/api/search/advanced', methods=['POST'])
def api_advanced_search():
    """Advanced book search"""
    criteria = request.json
    
    query = Book.query
    
    if criteria.get('title'):
        query = query.filter(Book.title.contains(criteria['title']))
    if criteria.get('author'):
        query = query.filter(Book.authors.contains(criteria['author']))
    if criteria.get('publisher'):
        query = query.filter(Book.publishers.contains(criteria['publisher']))
    if criteria.get('year_from'):
        query = query.filter(Book.publish_date >= str(criteria['year_from']))
    if criteria.get('year_to'):
        query = query.filter(Book.publish_date <= str(criteria['year_to']))
    
    if criteria.get('category'):
        query = query.join(BookCategory).join(Category)\
            .filter(Category.name == criteria['category'])
    
    books = query.all()
    
    # Save search to history
    search_term = json.dumps(criteria, ensure_ascii=False)
    search_history = SearchHistory(
        search_term=search_term,
        search_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        result_count=len(books)
    )
    db.session.add(search_history)
    db.session.commit()
    
    books_data = []
    for book in books:
        borrowed_count = Transaction.query.filter_by(isbn=book.isbn, return_date=None).count()
        available = book.quantity - borrowed_count
        
        books_data.append({
            'isbn': book.isbn,
            'title': book.title,
            'authors': book.authors,
            'publish_date': book.publish_date,
            'publishers': book.publishers,
            'quantity': book.quantity,
            'available': available
        })
    
    return jsonify({'books': books_data})
