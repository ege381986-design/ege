"""
PythonAnywhere için Yapılandırma Dosyası
Bu dosya PythonAnywhere ortamı için optimize edilmiştir
"""

from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Flask uygulaması oluştur
app = Flask(__name__)

# PythonAnywhere için yapılandırma
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'pythonanywhere-secret-key-change-this'

# SQLite veritabanı - PythonAnywhere'de çalışır
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "kutuphane.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload klasörü
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Mail configuration - Gmail SMTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

# Gerekli klasörleri oluştur
required_folders = [
    app.config['UPLOAD_FOLDER'],
    os.path.join(basedir, 'static', 'qrcodes'),
    os.path.join(basedir, 'reports'),
    os.path.join(basedir, 'backups'),
    os.path.join(basedir, 'instance')
]

for folder in required_folders:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

# Extensions'ları başlat
db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import all models after db is initialized
from models import *

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def get_setting(key, default=None):
    """Get setting value from database"""
    try:
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default
    except:
        return default

# Template context processor
@app.context_processor
def inject_globals():
    """Inject global functions and variables into templates"""
    return {
        'get_setting': get_setting,
        'now': datetime.now,
        'strptime': datetime.strptime
    }

# Jinja2 filters
@app.template_filter('activity_icon')
def activity_icon_filter(action):
    mapping = {
        'login': 'box-arrow-in-right',
        'logout': 'box-arrow-right',
        'register': 'person-plus',
        'add_book': 'book-plus',
        'borrow': 'arrow-down-circle',
        'return': 'arrow-up-circle',
        'reserve': 'bookmark-plus',
        'fine': 'exclamation-circle',
        'update': 'pencil-square',
        'delete': 'trash',
    }
    return mapping.get(action, 'info-circle')

@app.template_filter('timeago')
def timeago_filter(dt):
    if not dt:
        return ''
    now = datetime.utcnow()
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')
            except:
                return dt
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'şimdi'
    elif seconds < 3600:
        return f'{int(seconds//60)} dakika önce'
    elif seconds < 86400:
        return f'{int(seconds//3600)} saat önce'
    elif seconds < 2592000:
        return f'{int(seconds//86400)} gün önce'
    elif seconds < 31104000:
        return f'{int(seconds//2592000)} ay önce'
    else:
        return f'{int(seconds//31104000)} yıl önce'

# Initialize database with default data
def init_database():
    """Initialize database with default data"""
    with app.app_context():
        db.create_all()
        
        # Add default categories if not exist
        default_categories = [
            ("Türk Edebiyatı", "Türk edebiyatı eserleri"),
            ("Yabancı Edebiyat", "Yabancı edebiyat eserleri"),
            ("Şiir", "Şiir kitapları"),
            ("Hikaye", "Hikaye kitapları"),
            ("Roman", "Roman türündeki kitaplar"),
            ("Bilim", "Bilimsel kitaplar"),
            ("Tarih", "Tarih kitapları"),
            ("Biyografi", "Biyografi kitapları"),
            ("Çocuk", "Çocuk kitapları"),
            ("Eğitim", "Eğitim kitapları")
        ]
        
        for cat_name, cat_desc in default_categories:
            if not Category.query.filter_by(name=cat_name).first():
                category = Category(name=cat_name, description=cat_desc)
                db.session.add(category)
        
        # Add default settings
        default_settings = [
            ('fine_per_day', '1.0', 'Günlük gecikme cezası (TL)'),
            ('max_borrow_days', '14', 'Maksimum ödünç alma süresi (gün)'),
            ('max_renew_count', '2', 'Maksimum yenileme sayısı'),
            ('reservation_expiry_days', '3', 'Rezervasyon geçerlilik süresi (gün)'),
            ('max_books_per_member', '5', 'Üye başına maksimum kitap sayısı'),
            ('library_name', 'Cumhuriyet Anadolu Lisesi Kütüphanesi', 'Kütüphane adı'),
            ('library_email', 'kutuphane@cal.edu.tr', 'Kütüphane e-posta adresi'),
            ('library_phone', '0312 XXX XX XX', 'Kütüphane telefonu'),
            ('sms_notifications', 'false', 'SMS bildirimleri aktif mi?'),
            ('email_notifications', 'true', 'E-posta bildirimleri aktif mi?')
        ]
        
        for key, value, desc in default_settings:
            if not Settings.query.filter_by(key=key).first():
                setting = Settings(key=key, value=value, description=desc)
                db.session.add(setting)
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@cal.edu.tr',
                role='admin'
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
        
        try:
            db.session.commit()
            print("✅ Database initialized successfully")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database initialization error: {e}")

# Initialize database on startup
try:
    init_database()
except Exception as e:
    print(f"❌ Initialization error: {e}")
