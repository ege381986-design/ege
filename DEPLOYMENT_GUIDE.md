# Kütüphane Yönetim Sistemi - PythonAnywhere Deployment Rehberi

Bu dokümantasyon, Cumhuriyet Anadolu Lisesi Kütüphane Yönetim Sistemi'ni PythonAnywhere'de nasıl deploy edeceğinizi açıklar.

## Gereksinimler

- PythonAnywhere hesabı (ücretsiz hesap yeterli)
- Gmail hesabı (e-posta bildirimleri için)

## Adım 1: Dosyaları PythonAnywhere'e Yükleyin

1. PythonAnywhere'de "Files" sekmesine gidin
2. Ana dizininizde `mysite` klasörü oluşturun
3. Aşağıdaki dosyaları `mysite` klasörüne yükleyin:
   - `app_pythonanywhere.py` (ana uygulama)
   - `wsgi.py` (WSGI konfigürasyonu)
   - `config_pythonanywhere.py` (yapılandırma)
   - `models.py` (veritabanı modelleri)
   - `routes.py` (web sayfaları)
   - `api.py` (API endpoint'leri)
   - `utils.py` (yardımcı fonksiyonlar)
   - `requirements_pythonanywhere.txt` (gerekli paketler)
   - `static/` klasörü (CSS, JS, resimler)
   - `templates/` klasörü (HTML şablonları)

## Adım 2: Sanal Ortam Kurulumu

PythonAnywhere Console'da:

```bash
# Ana dizininize gidin
cd ~

# Sanal ortam oluşturun
python3.10 -m venv mysite-venv

# Sanal ortamı aktive edin
source mysite-venv/bin/activate

# Gerekli paketleri yükleyin
pip install -r mysite/requirements_pythonanywhere.txt
```

## Adım 3: Web Uygulaması Konfigürasyonu

1. PythonAnywhere Dashboard'da "Web" sekmesine gidin
2. "Add a new web app" butonuna tıklayın
3. "Manual configuration" seçin
4. Python 3.10 seçin
5. Aşağıdaki ayarları yapın:

### WSGI Configuration File

`/var/www/yourusername_pythonanywhere_com_wsgi.py` dosyasını düzenleyin:

```python
import os
import sys

# Kullanıcı adınızı buraya yazın
username = 'yourusername'
path = f'/home/{username}/mysite'
if path not in sys.path:
    sys.path.append(path)

# Sanal ortamı aktive et
activate_this = f'/home/{username}/mysite-venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

from app_pythonanywhere import app as application
```

### Static Files

Web app konfigürasyonunda:
- URL: `/static/`
- Directory: `/home/yourusername/mysite/static/`

### Source Code

- Source code: `/home/yourusername/mysite/`

## Adım 4: Çevre Değişkenleri

PythonAnywhere Dashboard'da "Files" sekmesinde `.bashrc` dosyasını düzenleyin:

```bash
# Gmail yapılandırması (E-posta bildirimleri için)
export MAIL_USERNAME='your-email@gmail.com'
export MAIL_PASSWORD='your-app-password'
export SECRET_KEY='your-secret-key-here'
```

**Önemli:** Gmail App Password kullanın, normal şifre değil!

## Adım 5: Veritabanı Kurulumu

Console'da:

```bash
cd ~/mysite
source ../mysite-venv/bin/activate
python3
```

Python shell'de:

```python
from app_pythonanywhere import app, db
with app.app_context():
    db.create_all()
    print("Database created!")
exit()
```

## Adım 6: Test ve Çalıştırma

1. Web app konfigürasyonunda "Reload" butonuna tıklayın
2. Your web app URL'ini ziyaret edin: `yourusername.pythonanywhere.com`
3. Admin paneline giriş yapın:
   - Kullanıcı adı: `admin`
   - Şifre: `admin123` (değiştirmeyi unutmayın!)

## Dosya Yapısı

```
/home/yourusername/
├── mysite/
│   ├── app_pythonanywhere.py     # Ana uygulama
│   ├── wsgi.py                   # WSGI konfigürasyonu
│   ├── config_pythonanywhere.py  # Yapılandırma
│   ├── models.py                 # Veritabanı modelleri
│   ├── routes.py                 # Web sayfaları
│   ├── api.py                    # API endpoint'leri
│   ├── utils.py                  # Yardımcı fonksiyonlar
│   ├── kutuphane.db             # SQLite veritabanı
│   ├── static/                   # CSS, JS, resimler
│   ├── templates/                # HTML şablonları
│   ├── uploads/                  # Yüklenen dosyalar
│   ├── reports/                  # Raporlar
│   └── backups/                  # Yedekler
└── mysite-venv/                  # Sanal ortam
```

## Önemli Notlar

### Güvenlik
- `SECRET_KEY`'i mutlaka değiştirin
- Admin şifresini değiştirin
- Gmail App Password kullanın

### Limitler (Ücretsiz Hesap)
- CPU saniye limiti vardır
- Disk alanı limiti: 512MB
- Günlük web istekleri limiti

### Veritabanı
- SQLite kullanılıyor (ücretsiz hesaplar için uygun)
- Büyük projeler için MySQL upgrade gerekebilir

### Log Dosyaları
Hatalar için:
- Error log: Web app konfigürasyon sayfasında
- Server log: Web app konfigürasyon sayfasında

## Sorun Giderme

### ImportError hatası
```bash
# Konsol'da paket yükleyin
pip install eksik-paket-adi
```

### Veritabanı hatası
```bash
# Veritabanı dosya izinlerini kontrol edin
ls -la ~/mysite/kutuphane.db
chmod 664 ~/mysite/kutuphane.db
```

### Static dosyalar yüklenmiyor
- Static files konfigürasyonunu kontrol edin
- URL ve Directory yollarının doğru olduğundan emin olun

## Güncelleme

Kod güncellemesi yapmak için:
1. Yeni dosyaları yükleyin
2. Web app'te "Reload" butonuna tıklayın

## Destek

- PythonAnywhere Help: help@pythonanywhere.com
- Forum: https://www.pythonanywhere.com/forums/

## Başarılı Deploy Kontrol Listesi

- [ ] Dosyalar yüklendi
- [ ] Sanal ortam oluşturuldu
- [ ] Paketler yüklendi
- [ ] WSGI dosyası düzenlendi
- [ ] Çevre değişkenleri ayarlandı
- [ ] Veritabanı oluşturuldu
- [ ] Web app reload edildi
- [ ] Site çalışıyor
- [ ] Admin girişi yapılabiliyor
- [ ] E-posta ayarları test edildi

Tüm adımlar tamamlandığında kütüphane yönetim sisteminiz PythonAnywhere'de çalışır durumda olacaktır!
