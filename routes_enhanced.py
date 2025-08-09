"""
Enhanced Routes - Gelişmiş Web Sayfaları
Yeni özellikler ve API endpoint'leri
"""

from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Book, Member, Transaction, User
from ai_engine import get_ai_engine
from datetime import datetime, timedelta
import json

def register_enhanced_routes(app):
    """Enhanced route'ları kaydet"""
    
    @app.route('/api/ai/recommend/<isbn>')
    @login_required
    def ai_book_recommendations(isbn):
        """AI kitap önerileri"""
        try:
            ai_engine = get_ai_engine()
            books = Book.query.all()
            
            recommendations = ai_engine['recommendation'].recommend_books(isbn, 5)
            
            result = []
            for idx, score in recommendations:
                if idx < len(books):
                    book = books[idx]
                    result.append({
                        'isbn': book.isbn,
                        'title': book.title,
                        'authors': book.authors,
                        'score': float(score),
                        'image_url': f"/static/qrcodes/{book.isbn}.png"
                    })
            
            return jsonify({
                'success': True,
                'recommendations': result
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/ai/categorize', methods=['POST'])
    @login_required
    def ai_categorize_book():
        """AI ile kitap kategorizasyonu"""
        if current_user.role not in ['admin', 'librarian']:
            return jsonify({'success': False, 'error': 'Yetkiniz yok'}), 403
        
        try:
            data = request.get_json()
            title = data.get('title', '')
            description = data.get('description', '')
            
            ai_engine = get_ai_engine()
            category, confidence = ai_engine['categorizer'].categorize_book(title, description)
            
            return jsonify({
                'success': True,
                'category': category,
                'confidence': confidence
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/ai/chatbot', methods=['POST'])
    def ai_chatbot():
        """AI Chatbot"""
        try:
            data = request.get_json()
            message = data.get('message', '')
            
            ai_engine = get_ai_engine()
            response = ai_engine['chatbot'].process_message(message)
            
            return jsonify({
                'success': True,
                'response': response
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'response': 'Üzgünüm, şu anda size yardımcı olamıyorum.'
            })
    
    @app.route('/analytics')
    @login_required
    def analytics():
        """Gelişmiş analitik sayfası"""
        if current_user.role not in ['admin', 'librarian']:
            flash('Bu sayfaya erişim yetkiniz yok.', 'error')
            return redirect(url_for('dashboard'))
        
        # Analitik verileri hazırla
        total_books = Book.query.count()
        total_members = Member.query.count()
        active_transactions = Transaction.query.filter_by(return_date=None).count()
        
        # Son 30 günlük veriler
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        recent_transactions = Transaction.query.filter(
            Transaction.borrow_date >= thirty_days_ago
        ).count()
        
        # Popüler kitaplar
        popular_books = Book.query.order_by(Book.total_borrow_count.desc()).limit(10).all()
        
        # Kategori dağılımı
        categories = {}
        for book in Book.query.all():
            cat = book.category or 'Diğer'
            categories[cat] = categories.get(cat, 0) + 1
        
        return render_template('analytics.html',
                             total_books=total_books,
                             total_members=total_members,
                             active_transactions=active_transactions,
                             recent_transactions=recent_transactions,
                             popular_books=popular_books,
                             categories=categories)
    
    @app.route('/api/system/health')
    def system_health():
        """Sistem sağlık kontrolü"""
        try:
            # Database bağlantısı test et
            db.session.execute('SELECT 1')
            
            # Temel istatistikler
            stats = {
                'database': 'healthy',
                'books_count': Book.query.count(),
                'members_count': Member.query.count(),
                'active_transactions': Transaction.query.filter_by(return_date=None).count(),
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify({
                'status': 'healthy',
                'stats': stats
            })
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/api/books/search/smart', methods=['GET'])
    def smart_book_search():
        """Akıllı kitap arama"""
        try:
            query = request.args.get('q', '').strip()
            if not query:
                return jsonify({'books': [], 'total': 0})
            
            # Basit arama (geliştirilmesi gerekiyor)
            books = Book.query.filter(
                Book.title.contains(query) |
                Book.authors.contains(query) |
                Book.publishers.contains(query)
            ).limit(20).all()
            
            results = []
            for book in books:
                results.append({
                    'isbn': book.isbn,
                    'title': book.title,
                    'authors': book.authors,
                    'publishers': book.publishers,
                    'category': book.category,
                    'quantity': book.quantity,
                    'available': book.quantity - Transaction.query.filter_by(
                        isbn=book.isbn, return_date=None
                    ).count()
                })
            
            return jsonify({
                'books': results,
                'total': len(results),
                'query': query
            })
            
        except Exception as e:
            return jsonify({
                'error': str(e),
                'books': [],
                'total': 0
            }), 500
    
    @app.route('/mobile/scanner')
    def mobile_scanner():
        """Mobil QR scanner sayfası"""
        return render_template('mobile_scanner.html')
    
    @app.route('/api/notifications/send', methods=['POST'])
    @login_required
    def send_notification():
        """Push notification gönder"""
        if current_user.role not in ['admin', 'librarian']:
            return jsonify({'success': False, 'error': 'Yetkiniz yok'}), 403
        
        try:
            data = request.get_json()
            title = data.get('title', '')
            message = data.get('message', '')
            target = data.get('target', 'all')  # all, user_id, role
            
            # Push notification gönderme logic'i burada implement edilecek
            # Şimdilik basit response
            
            return jsonify({
                'success': True,
                'message': 'Bildirim gönderildi'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    print("✅ Enhanced routes kaydedildi!")

print("🚀 Enhanced routes modülü hazır!") 