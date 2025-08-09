# PythonAnywhere Kurulum Adımları
**Bu versiyon PythonAnywhere'in 512MB disk kotasına uygun olarak optimize edilmiştir**

## ⚠️ Önemli Not
Bu requirements.txt dosyası ML kütüphanelerini (torch, transformers, scikit-learn) içermez çünkü disk kotası aşımına sebep olurlar. Sadece temel kütüphane yönetimi özellikleri çalışacaktır.

## 1. Dosyaları Yükleyin
Bu klasördeki tüm dosya ve klasörleri PythonAnywhere'deki `/home/kullaniciadi/mysite/` dizinine yükleyin.

## 2. Sanal Ortam Kurun ve Kütüphaneleri Yükleyin
```bash
cd ~
python3.10 -m venv mysite-venv
source mysite-venv/bin/activate
cd mysite
pip install -r requirements.txt
```

**Eğer disk kotası hatası alırsanız:**
```bash
# Önce temel kütüphaneleri yükleyin
pip install Flask==2.3.3 Flask-SQLAlchemy==3.0.5
pip install Flask-Login==0.6.2 Flask-WTF==1.1.1
pip install requests==2.31.0 qrcode==7.4.2
# Sonra diğerlerini tek tek ekleyin
```

## 3. WSGI Dosyasını Düzenleyin
PythonAnywhere dashboardda "Web" sekmesinden:
- `Source code:` `/home/kullaniciadi/mysite`
- `Working directory:` `/home/kullaniciadi/mysite`
- WSGI configuration file'da kullanıcı adınızı güncelleyin

## 4. Environment Variables
Console'dan:
```bash
echo 'export SECRET_KEY="your-secret-key-here"' >> ~/.bashrc
echo 'export MAIL_USERNAME="your-email@gmail.com"' >> ~/.bashrc
echo 'export MAIL_PASSWORD="your-app-password"' >> ~/.bashrc
source ~/.bashrc
```

## 5. Veritabanı Oluşturun
```bash
cd ~/mysite
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('✅ Veritabanı oluşturuldu')"
```

## 6. Web App'i Reload Edin
PythonAnywhere web app konfigürasyonunda "Reload" butonuna tıklayın.

## 7. Test Edin
Web sitenizi ziyaret edin: `https://kullaniciadi.pythonanywhere.com`

## Disk Kotası Sorunu Çözüldü ✅
- ML kütüphaneleri kaldırıldı (torch, transformers, scikit-learn)
- Hafif versiyonlar kullanıldı
- Redis ve Celery devre dışı bırakıldı (SQLite cache kullanılıyor)
- Toplam boyut ~100MB'a düşürüldü

## Çalışan Özellikler
✅ Kitap ekleme/düzenleme/silme
✅ Üye yönetimi  
✅ Ödünç alma/iade işlemleri
✅ QR kod üretimi
✅ PDF rapor oluşturma
✅ E-posta bildirimleri
✅ Web arayüzü ve API'ler
✅ Excel import/export

## Çalışmayan Özellikler (ML gerektiren)
❌ AI tabanlı kitap önerileri
❌ Otomatik kategori tanıma
❌ Gelişmiş analitik özellikler
❌ Background task'lar (Celery)
❌ Redis cache

Detaylı talimatlar için DEPLOYMENT_GUIDE.md dosyasını okuyun.
