# Cumhuriyet Anadolu Lisesi Kütüphane Yönetim Sistemi

## Modüler Yapı - v2.0

Bu proje 4000+ satırlık tek bir dosyadan (app.py) 5 mantıklı modüle bölünmüştür. Her modül yaklaşık 800-1000 satır koddan oluşur.

## 📁 Dosya Yapısı

```
├── app.py              # Ana uygulama dosyası (89 satır)
├── config.py           # Konfigürasyon ve başlangıç (350+ satır)  
├── models.py           # Veritabanı modelleri (430+ satır)
├── routes.py           # Web sayfaları ve route'lar (850+ satır)
├── api.py              # Temel API endpoint'leri (900+ satır)
├── api_extended.py     # Ek API endpoint'leri (1100+ satır)
├── utils.py            # Yardımcı fonksiyonlar (1200+ satır)
├── app_old.py          # Eski tek dosya (yedek)
└── README.md           # Bu dosya
```

## 🔧 Modül Açıklamaları

### 1. config.py - Konfigürasyon ve Başlangıç
- Flask uygulaması oluşturma
- Veritabanı ve mail konfigürasyonu
- Klasör oluşturma
- Varsayılan verilerin yüklenmesi
- Template context fonksiyonları

### 2. models.py - Veritabanı Modelleri
- SQLAlchemy modelleri
- User, Book, Member, Transaction vb. tüm tablolar
- İlişkiler (relationships)
- Model metodları

### 3. routes.py - Web Sayfaları ve Route'lar
- Ana web sayfaları (/, /books, /profile vb.)
- Kimlik doğrulama (login, logout, register)
- Admin sayfaları (dashboard, reports, settings)
- Kullanıcı sayfaları (my-books, my-reservations)

### 4. api.py - Temel API Endpoint'leri
- Kitap API'leri (/api/books/*)
- Üye API'leri (/api/members/*)
- İşlem API'leri (/api/transactions/*)
- Kategori API'leri (/api/categories/*)
- Temel CRUD işlemleri

### 5. api_extended.py - Ek API Endpoint'leri
- Bildirim API'leri (/api/notifications/*)
- Rezervasyon API'leri (/api/reservations/*)
- Ceza API'leri (/api/fines/*)
- Ayarlar API'leri (/api/settings/*)
- QR kod API'leri (/api/qr/*)
- Online ödünç alma API'leri
- Yedekleme API'leri
- İstatistik API'leri

### 6. utils.py - Yardımcı Fonksiyonlar
- E-posta gönderme
- QR kod oluşturma
- PDF oluşturma
- Excel export/import
- API entegrasyonları (Google Books, OpenLibrary)
- İşlem fonksiyonları
- Yedekleme fonksiyonları

## 🚀 Çalıştırma

```bash
python app.py
```

## 🔗 Önemli URL'ler

- **Ana Sayfa**: http://localhost:5000
- **Admin Paneli**: http://localhost:5000/dashboard  
- **API Dokümantasyonu**: http://localhost:5000/api/*

## 👤 Varsayılan Giriş Bilgileri

- **Kullanıcı Adı**: admin
- **Şifre**: admin123

## 📊 Özellikler

### Ana Özellikler
- ✅ Kitap yönetimi (ekleme, düzenleme, silme)
- ✅ Üye yönetimi 
- ✅ Ödünç alma/iade işlemleri
- ✅ Rezervasyon sistemi
- ✅ Ceza sistemi
- ✅ QR kod desteği
- ✅ Online ödünç alma
- ✅ E-posta bildirimleri

### API Özellikleri
- ✅ RESTful API'ler
- ✅ JSON responses
- ✅ Error handling
- ✅ Authentication
- ✅ Role-based access

### Raporlama
- ✅ Dashboard istatistikleri
- ✅ Excel export/import
- ✅ PDF raporları
- ✅ QR kod toplu üretimi

## 🛠️ Teknik Detaylar

### Kullanılan Teknolojiler
- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Frontend**: Bootstrap, jQuery, Chart.js
- **Database**: SQLite
- **PDF**: ReportLab
- **QR Codes**: qrcode
- **Excel**: pandas, openpyxl

### Veritabanı Tabloları
- users (kullanıcılar)
- books (kitaplar)
- members (üyeler)
- transactions (işlemler)
- categories (kategoriler)
- reservations (rezervasyonlar)
- fines (cezalar)
- notifications (bildirimler)
- settings (ayarlar)
- activity_logs (aktivite logları)

## 🔄 Modüler Yapının Avantajları

1. **Daha İyi Organizasyon**: Her modül belirli bir sorumluluğa sahip
2. **Kolay Bakım**: Değişiklikler ilgili modülde yapılır
3. **Takım Çalışması**: Farklı modüller paralel geliştirilebilir
4. **Test Edilebilirlik**: Her modül ayrı ayrı test edilebilir
5. **Yeniden Kullanılabilirlik**: Modüller başka projelerde kullanılabilir
6. **Performans**: Sadece gerekli modüller yüklenir

## 📝 Notlar

- Bu yapı Python'un import sistemini kullanır
- Circular import'lar engellenmiştir
- Her modül kendi import'larını yapar
- Database instance models.py'da oluşturulur
- Configuration config.py'da merkezi olarak yönetilir

## 🔧 Geliştirme

Yeni özellik eklerken:

1. **Model değişikliği** → models.py
2. **Web sayfası** → routes.py  
3. **API endpoint** → api.py veya api_extended.py
4. **Yardımcı fonksiyon** → utils.py
5. **Konfigürasyon** → config.py

## 📞 Destek

Herhangi bir sorun için:
- Hata loglarını kontrol edin
- Her modülün kendi import'larını kontrol edin
- Database bağlantısını test edin

---

**Geliştirici**: Claude AI Assistant  
**Versiyon**: 2.0 (Modüler)  
**Tarih**: 2024
