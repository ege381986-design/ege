# 🚀 PythonAnywhere Deployment - Hızlı Başlangıç

Bu dosyalar Cumhuriyet Anadolu Lisesi Kütüphane Yönetim Sistemi'ni PythonAnywhere'de deploy etmek için hazırlanmıştır.

## 📦 Hazırlanmış Dosyalar

### Ana Dosyalar
- `app_pythonanywhere.py` → PythonAnywhere için optimize edilmiş ana uygulama
- `config_pythonanywhere.py` → PythonAnywhere için yapılandırma
- `wsgi.py` → WSGI konfigürasyonu
- `requirements_pythonanywhere.txt` → Sadece gerekli paketler

### Deployment Araçları
- `deploy_pythonanywhere.ps1` → Windows PowerShell scripti
- `deploy_pythonanywhere.sh` → Linux/Mac bash scripti
- `DEPLOYMENT_GUIDE.md` → Detaylı deployment rehberi

## 🎯 Hızlı Deployment

### 1. Dosyaları Hazırla
Windows'da:
```powershell
.\deploy_pythonanywhere.ps1
```

Linux/Mac'te:
```bash
chmod +x deploy_pythonanywhere.sh
./deploy_pythonanywhere.sh
```

### 2. PythonAnywhere'e Yükle
1. `deployment_pythonanywhere.zip` dosyasını indirin
2. PythonAnywhere Files sekmesine gidin
3. ZIP'i `mysite/` klasörüne yükleyin ve açın

### 3. Sanal Ortam Kur
```bash
cd ~
python3.10 -m venv mysite-venv
source mysite-venv/bin/activate
pip install -r mysite/requirements.txt
```

### 4. WSGI Ayarla
`/var/www/kullaniciadi_pythonanywhere_com_wsgi.py`:
```python
import os
import sys

username = 'KULLANICI_ADINIZ'  # ← Buraya kullanıcı adınızı yazın
path = f'/home/{username}/mysite'
if path not in sys.path:
    sys.path.append(path)

activate_this = f'/home/{username}/mysite-venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

from app import app as application
```

### 5. Environment Variables
`.bashrc` dosyanıza ekleyin:
```bash
export MAIL_USERNAME='email@gmail.com'
export MAIL_PASSWORD='gmail-app-password'  
export SECRET_KEY='gizli-anahtar-buraya'
```

### 6. Veritabanı Oluştur
```bash
cd ~/mysite
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 7. Web App'i Başlat
1. Web sekmesinde "Reload" butonuna tıklayın
2. `kullaniciadi.pythonanywhere.com` adresini ziyaret edin

## 🔑 İlk Giriş

- **Kullanıcı:** admin
- **Şifre:** admin123
- **⚠️ Önemli:** Şifreyi hemen değiştirin!

## 📱 Özellikler

✅ Üye yönetimi
✅ Kitap kataloglama  
✅ Ödünç alma/iade sistemi
✅ QR kod oluşturma
✅ E-posta bildirimleri
✅ Raporlama
✅ Rezervasyon sistemi
✅ Gecikme takibi

## 🛠️ PythonAnywhere Konfigürasyonu

### Web App Settings
- **Source code:** `/home/kullaniciadi/mysite`
- **Working directory:** `/home/kullaniciadi/mysite`
- **Python version:** 3.10

### Static Files
- **URL:** `/static/`
- **Directory:** `/home/kullaniciadi/mysite/static/`

## ❓ Sorun Giderme

### ImportError
```bash
pip install eksik-paket-adi
```

### Veritabanı Hatası
```bash
chmod 664 ~/mysite/*.db
```

### Static Dosyalar
Static files ayarlarını kontrol edin.

### Error Logs
Web app sayfasında "Error log" ve "Server log" bağlantılarını kontrol edin.

## 📞 Destek

- **Detaylı Rehber:** `DEPLOYMENT_GUIDE.md`
- **PythonAnywhere Help:** help@pythonanywhere.com
- **Forum:** pythonanywhere.com/forums/

## 🎉 Başarılı Deploy Sonrası

1. Admin şifresini değiştirin
2. E-posta ayarlarını test edin  
3. Birkaç test verisi girin
4. Tüm özellikleri test edin

**🎯 Deployment URL'niz:** `https://kullaniciadi.pythonanywhere.com`

---

**📝 Not:** Bu dosyalar PythonAnywhere ücretsiz hesabı için optimize edilmiştir. Büyük çaplı kullanım için paid plan gerekebilir.
