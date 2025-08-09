from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from datetime import datetime
import os

# Flask uygulaması oluştur
app = Flask(__name__)

# Uygulama konfigürasyonu
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books_info.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

# Create necessary folders
for folder in ['uploads', 'static/qrcodes', 'reports', 'backups']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Initialize extensions  
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import db from models and initialize
from models import db
db.init_app(app)

# Import all models after db is initialized
from models import *

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def get_setting(key, default=None):
    """Get setting value from database"""
    setting = Settings.query.filter_by(key=key).first()
    return setting.value if setting else default

# Add get_setting to template context
@app.context_processor
def inject_globals():
    """Inject global functions and variables into templates"""
    return {
        'get_setting': get_setting,
        'now': datetime.now,
        'strptime': datetime.strptime
    }

# Initialize database and default data
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
            ("Eğitim", "Eğitim kitapları"),
            ("Felsefe", "Felsefe kitapları"),
            ("Sanat", "Sanat kitapları"),
            ("Psikoloji", "Psikoloji kitapları"),
            ("Sosyoloji", "Sosyoloji kitapları"),
            ("Matematik", "Matematik kitapları"),
            ("Fizik", "Fizik kitapları"),
            ("Kimya", "Kimya kitapları"),
            ("Biyoloji", "Biyoloji kitapları"),
            ("Coğrafya", "Coğrafya kitapları"),
            ("Din", "Din kitapları")
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
        
        # Add default email templates
        email_templates = [
            {
                'name': 'welcome',
                'subject': 'Kütüphaneye Hoş Geldiniz',
                'body': '''Sayın {{member_name}},

Cumhuriyet Anadolu Lisesi Kütüphanesine hoş geldiniz!

Üyelik bilgileriniz:
- Üye No: {{member_id}}
- Kayıt Tarihi: {{join_date}}

Kütüphanemizden en iyi şekilde yararlanmanızı dileriz.

Saygılarımızla,
Kütüphane Yönetimi''',
                'variables': '["member_name", "member_id", "join_date"]'
            },
            {
                'name': 'borrow_confirmation',
                'subject': 'Kitap Ödünç Alma Onayı',
                'body': '''Sayın {{member_name}},

Aşağıdaki kitabı ödünç aldınız:

Kitap: {{book_title}}
ISBN: {{isbn}}
Ödünç Tarihi: {{borrow_date}}
Son Teslim Tarihi: {{due_date}}

Lütfen kitabı zamanında iade etmeyi unutmayın.

İyi okumalar,
Kütüphane Yönetimi''',
                'variables': '["member_name", "book_title", "isbn", "borrow_date", "due_date"]'
            },
            {
                'name': 'return_reminder',
                'subject': 'Kitap İade Hatırlatması',
                'body': '''Sayın {{member_name}},

"{{book_title}}" isimli kitabın iade tarihi yaklaşıyor.

Son Teslim Tarihi: {{due_date}}
Kalan Gün: {{days_remaining}}

Lütfen kitabı zamanında iade ediniz.

Saygılarımızla,
Kütüphane Yönetimi''',
                'variables': '["member_name", "book_title", "due_date", "days_remaining"]'
            },
            {
                'name': 'overdue_notice',
                'subject': 'Gecikmiş Kitap Bildirimi',
                'body': '''Sayın {{member_name}},

"{{book_title}}" isimli kitabın iade süresi dolmuştur.

Son Teslim Tarihi: {{due_date}}
Gecikme Süresi: {{days_overdue}} gün
Gecikme Cezası: {{fine_amount}} TL

Lütfen en kısa sürede kitabı iade ediniz.

Saygılarımızla,
Kütüphane Yönetimi''',
                'variables': '["member_name", "book_title", "due_date", "days_overdue", "fine_amount"]'
            },
            {
                'name': 'online_borrow_request',
                'subject': 'Online Ödünç Alma Talebiniz Alındı',
                'body': '''Sayın {{member_name}},

"{{book_title}}" isimli kitap için online ödünç alma talebiniz alınmıştır.

Talep ID: {{request_id}}
Alış Tarihi: {{pickup_date}}
Alış Saati: {{pickup_time}}

Talebiniz incelendikten sonra e-posta ile bilgilendirileceksiniz.

Saygılarımızla,
Kütüphane Yönetimi''',
                'variables': '["member_name", "book_title", "request_id", "pickup_date", "pickup_time"]'
            },
            {
                'name': 'admin_online_borrow_notification',
                'subject': 'Yeni Online Ödünç Alma Talebi',
                'body': '''Yeni bir online ödünç alma talebi bulunmaktadır.

Üye: {{member_name}}
Kitap: {{book_title}}
Alış Tarihi: {{pickup_date}}
Alış Saati: {{pickup_time}}
Talep ID: {{request_id}}

Lütfen admin panelinden talebi inceleyiniz.

Kütüphane Yönetim Sistemi''',
                'variables': '["member_name", "book_title", "pickup_date", "pickup_time", "request_id"]'
            },
            {
                'name': 'online_borrow_approved',
                'subject': 'Online Ödünç Alma Talebiniz Onaylandı',
                'body': '''Sayın {{member_name}},

"{{book_title}}" isimli kitap için online ödünç alma talebiniz onaylanmıştır.

Talep ID: {{request_id}}
Alış Tarihi: {{pickup_date}}
Alış Saati: {{pickup_time}}
Son Teslim Tarihi: {{due_date}}

Belirtilen tarih ve saatte kütüphaneye gelerek kitabınızı alabilirsiniz.
Kimlik belgenizi yanınızda getirmeyi unutmayın.

Saygılarımızla,
Kütüphane Yönetimi''',
                'variables': '["member_name", "book_title", "request_id", "pickup_date", "pickup_time", "due_date"]'
            },
            {
                'name': 'online_borrow_rejected',
                'subject': 'Online Ödünç Alma Talebiniz Reddedildi',
                'body': '''Sayın {{member_name}},

"{{book_title}}" isimli kitap için online ödünç alma talebiniz reddedilmiştir.

Talep ID: {{request_id}}
Red Nedeni: {{reason}}

Başka bir kitap için talep oluşturabilir veya kütüphanemizi ziyaret edebilirsiniz.

Saygılarımızla,
Kütüphane Yönetimi''',
                'variables': '["member_name", "book_title", "request_id", "reason"]'
            }
        ]
        
        for template in email_templates:
            if not EmailTemplate.query.filter_by(name=template['name']).first():
                email_template = EmailTemplate(**template)
                db.session.add(email_template)
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@cal.edu.tr',
                role='admin'
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
        
        db.session.commit()

# Initialize scheduled tasks when app starts
def init_app():
    """Initialize app and run scheduled tasks"""
    from utils import check_overdue_books
    with app.app_context():
        check_overdue_books()

# Jinja2 filter: activity_icon
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

# Jinja2 filter: timeago
@app.template_filter('timeago')
def timeago_filter(dt):
    from datetime import datetime
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

def open_browser():
    pass

# Initialize database on import
init_database()
