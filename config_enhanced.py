import os
import secrets
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_socketio import SocketIO
from flask_migrate import Migrate
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Load environment variables
load_dotenv()

class Config:
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Railway PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///library.db'
    
    # Railway Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Railway için port
    PORT = int(os.environ.get('PORT', 5000))
    
    # Production ayarları
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        SESSION_COOKIE_SECURE = True
        WTF_CSRF_ENABLED = True
        SQLALCHEMY_ECHO = False
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'csv'}
    
    # Mail Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@cal.edu.tr')
    
    # Redis Configuration
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # Cache Configuration
    CACHE_TYPE = "RedisCache" if os.environ.get('REDIS_HOST') else "SimpleCache"
    CACHE_REDIS_HOST = REDIS_HOST
    CACHE_REDIS_PORT = REDIS_PORT
    CACHE_REDIS_DB = REDIS_DB
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Celery Configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    
    # Push Notifications
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    
    # API Keys
    GOOGLE_BOOKS_API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY')
    OPENLIBRARY_API_KEY = os.environ.get('OPENLIBRARY_API_KEY')
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

# Initialize Flask app and extensions
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Sentry for error tracking
if app.config['SENTRY_DSN']:
    sentry_sdk.init(
        dsn=app.config['SENTRY_DSN'],
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0
    )

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
mail = Mail(app)
csrf = CSRFProtect(app)
cache = Cache(app)
socketio = SocketIO(app, cors_allowed_origins="*")
migrate = Migrate(app, db)

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[app.config['RATELIMIT_DEFAULT']]
)

# Login manager configuration
login_manager.login_view = 'login'
login_manager.login_message = 'Bu sayfaya erişmek için giriş yapmalısınız.'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/qrcodes', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Logging configuration
import logging
from logging.handlers import RotatingFileHandler

if not app.debug and not app.testing:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler('logs/library.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Library Management System startup')

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_setting(key, default=None):
    """Get setting from database or return default"""
    try:
        from models import Settings
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default
    except:
        return default

def set_setting(key, value):
    """Set setting in database"""
    try:
        from models import Settings
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Settings(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return True
    except:
        return False

# Context processors
@app.context_processor
def inject_user():
    from flask_login import current_user
    return dict(current_user=current_user)

@app.context_processor
def inject_settings():
    return dict(
        app_name=get_setting('app_name', 'Kütüphane Yönetim Sistemi'),
        app_version=get_setting('app_version', '2.0'),
        maintenance_mode=get_setting('maintenance_mode', 'false') == 'true'
    )

# Template filters
@app.template_filter('datetime')
def datetime_filter(value, format='%d.%m.%Y %H:%M'):
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('currency')
def currency_filter(value):
    return f"{value:.2f} ₺"

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('errors/429.html', 
                         description=e.description), 429

# Security headers
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    if app.config['SESSION_COOKIE_SECURE']:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

print("✅ Enhanced configuration loaded successfully!")
print(f"🔧 Environment: {os.environ.get('FLASK_ENV', 'development')}")
print(f"🗄️ Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
print(f"🔒 CSRF Protection: Enabled")
print(f"⚡ Cache Type: {app.config['CACHE_TYPE']}")
print(f"🚀 Ready to start!")
