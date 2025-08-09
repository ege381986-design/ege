"""
API Performance Enhancements
Performans artırma ve güvenlik iyileştirmeleri
"""

from functools import wraps
from flask import request, jsonify, g
import time
import hashlib
import json
from collections import defaultdict, deque
import threading

# Rate limiting storage
rate_limit_storage = defaultdict(lambda: deque())
rate_limit_lock = threading.Lock()

# Cache storage
cache_storage = {}
cache_lock = threading.Lock()

def rate_limit(max_requests=100, window=3600):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr
            current_time = time.time()
            
            with rate_limit_lock:
                # Clean old requests
                while (rate_limit_storage[client_ip] and 
                       rate_limit_storage[client_ip][0] < current_time - window):
                    rate_limit_storage[client_ip].popleft()
                
                # Check rate limit
                if len(rate_limit_storage[client_ip]) >= max_requests:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Maximum {max_requests} requests per hour',
                        'retry_after': window
                    }), 429
                
                # Add current request
                rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def cache_response(timeout=300):
    """Response caching decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create cache key
            cache_key = hashlib.md5(
                f"{request.endpoint}{request.args}{request.get_json()}".encode()
            ).hexdigest()
            
            current_time = time.time()
            
            with cache_lock:
                # Check cache
                if cache_key in cache_storage:
                    cached_data, cached_time = cache_storage[cache_key]
                    if current_time - cached_time < timeout:
                        return cached_data
                
                # Execute function and cache result
                result = f(*args, **kwargs)
                cache_storage[cache_key] = (result, current_time)
                
                # Clean old cache entries
                keys_to_delete = []
                for key, (_, cache_time) in cache_storage.items():
                    if current_time - cache_time > timeout:
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    del cache_storage[key]
                
                return result
        return decorated_function
    return decorator

def api_monitor(f):
    """API monitoring decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            status = 'success'
            return result
        except Exception as e:
            status = 'error'
            raise
        finally:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # ms
            
            # Log API call
            print(f"API: {request.endpoint} | "
                  f"Method: {request.method} | "
                  f"Status: {status} | "
                  f"Response Time: {response_time:.2f}ms | "
                  f"IP: {request.remote_addr}")
    
    return decorated_function

def compress_response(f):
    """Response compression decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = f(*args, **kwargs)
        
        # Add compression headers
        if hasattr(result, 'headers'):
            result.headers['Content-Encoding'] = 'gzip'
            result.headers['Vary'] = 'Accept-Encoding'
        
        return result
    return decorated_function

# Database query optimization
class QueryOptimizer:
    @staticmethod
    def optimize_book_queries():
        """Optimize book-related queries"""
        from models import db
        
        # Create indexes if not exist
        try:
            db.engine.execute("CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn)")
            db.engine.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")
            db.engine.execute("CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)")
            db.engine.execute("CREATE INDEX IF NOT EXISTS idx_transactions_book_isbn ON transactions(book_isbn)")
            db.engine.execute("CREATE INDEX IF NOT EXISTS idx_transactions_member_id ON transactions(member_id)")
            db.engine.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)")
            print("✅ Database indexes created/verified")
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")
    
    @staticmethod
    def get_popular_books_optimized(limit=10):
        """Optimized popular books query"""
        from models import db, Book, Transaction
        
        query = """
        SELECT b.*, COUNT(t.id) as borrow_count
        FROM books b
        LEFT JOIN transactions t ON b.isbn = t.book_isbn
        WHERE t.status IN ('borrowed', 'returned')
        GROUP BY b.isbn
        ORDER BY borrow_count DESC
        LIMIT ?
        """
        
        result = db.engine.execute(query, (limit,))
        return result.fetchall()

# Security enhancements
def validate_input(schema):
    """Input validation decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            
            # Basic validation
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Schema validation
            for field, rules in schema.items():
                if field in data:
                    value = data[field]
                    
                    # Type validation
                    if 'type' in rules and not isinstance(value, rules['type']):
                        return jsonify({'error': f'Invalid type for {field}'}), 400
                    
                    # Length validation
                    if 'max_length' in rules and len(str(value)) > rules['max_length']:
                        return jsonify({'error': f'{field} too long'}), 400
                    
                    # Required validation
                    if rules.get('required', False) and not value:
                        return jsonify({'error': f'{field} is required'}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage examples:
"""
# Rate limiting example
@rate_limit(max_requests=50, window=3600)  # 50 requests per hour
@api_monitor
def get_books():
    pass

# Caching example
@cache_response(timeout=600)  # Cache for 10 minutes
@api_monitor
def get_popular_books():
    pass

# Input validation example
@validate_input({
    'isbn': {'type': str, 'required': True, 'max_length': 13},
    'title': {'type': str, 'required': True, 'max_length': 200}
})
def add_book():
    pass
""" 