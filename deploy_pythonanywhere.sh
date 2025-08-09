#!/bin/bash

# Kütüphane Yönetim Sistemi - PythonAnywhere Deployment Script
# Bu script dosyaları PythonAnywhere için hazırlar

echo "🚀 Kütüphane Yönetim Sistemi - PythonAnywhere Deployment Hazırlığı"
echo "=================================================================="

# Deployment klasörü oluştur
DEPLOY_DIR="deployment_pythonanywhere"
echo "📁 $DEPLOY_DIR klasörü oluşturuluyor..."

if [ -d "$DEPLOY_DIR" ]; then
    rm -rf "$DEPLOY_DIR"
fi
mkdir -p "$DEPLOY_DIR"

# Temel dosyaları kopyala
echo "📋 Temel dosyalar kopyalanıyor..."
cp app_pythonanywhere.py "$DEPLOY_DIR/app.py"
cp wsgi.py "$DEPLOY_DIR/"
cp config_pythonanywhere.py "$DEPLOY_DIR/config.py"
cp models.py "$DEPLOY_DIR/"
cp routes.py "$DEPLOY_DIR/"
cp api.py "$DEPLOY_DIR/"
cp utils.py "$DEPLOY_DIR/"
cp requirements_pythonanywhere.txt "$DEPLOY_DIR/requirements.txt"
cp DEPLOYMENT_GUIDE.md "$DEPLOY_DIR/"

# Template ve static klasörlerini kopyala
echo "🎨 Templates ve static dosyalar kopyalanıyor..."
cp -r templates "$DEPLOY_DIR/"
cp -r static "$DEPLOY_DIR/"

# Gerekli klasörleri oluştur
echo "📂 Gerekli klasörler oluşturuluyor..."
mkdir -p "$DEPLOY_DIR/uploads"
mkdir -p "$DEPLOY_DIR/reports" 
mkdir -p "$DEPLOY_DIR/backups"
mkdir -p "$DEPLOY_DIR/instance"

# .env template oluştur
echo "⚙️ Environment dosyası oluşturuluyor..."
cat > "$DEPLOY_DIR/.env.template" << 'EOF'
# Gmail yapılandırması
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password

# Güvenlik
SECRET_KEY=your-secret-key-here-change-this

# Kütüphane bilgileri
LIBRARY_NAME=Cumhuriyet Anadolu Lisesi Kütüphanesi
LIBRARY_EMAIL=kutuphane@cal.edu.tr
LIBRARY_PHONE=0312 XXX XX XX
EOF

# Deployment talimatları oluştur
echo "📖 Deployment talimatları oluşturuluyor..."
cat > "$DEPLOY_DIR/INSTALL.md" << 'EOF'
# PythonAnywhere Kurulum Adımları

## 1. Dosyaları Yükleyin
Bu klasördeki tüm dosya ve klasörleri PythonAnywhere'deki `/home/kullaniciadi/mysite/` dizinine yükleyin.

## 2. Sanal Ortam Kurun
```bash
cd ~
python3.10 -m venv mysite-venv
source mysite-venv/bin/activate
pip install -r mysite/requirements.txt
```

## 3. WSGI Dosyasını Düzenleyin
`/var/www/kullaniciadi_pythonanywhere_com_wsgi.py` dosyasında kullanıcı adınızı güncelleyin.

## 4. Environment Variables
`.env.template` dosyasını `.bashrc` dosyanıza ekleyin (gerçek değerlerle).

## 5. Veritabanı Oluşturun
```bash
cd ~/mysite
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('OK')"
```

## 6. Web App'i Reload Edin
PythonAnywhere web app konfigürasyonunda "Reload" butonuna tıklayın.

Detaylı talimatlar için DEPLOYMENT_GUIDE.md dosyasını okuyun.
EOF

# Zip dosyası oluştur
echo "📦 Zip arşivi oluşturuluyor..."
zip -r "${DEPLOY_DIR}.zip" "$DEPLOY_DIR/"

# Özet bilgiler
echo ""
echo "✅ Deployment hazırlığı tamamlandı!"
echo ""
echo "📁 Oluşturulan dosyalar:"
echo "   - $DEPLOY_DIR/ klasörü"
echo "   - ${DEPLOY_DIR}.zip arşivi"
echo ""
echo "📋 Sonraki adımlar:"
echo "   1. ${DEPLOY_DIR}.zip dosyasını indirin"
echo "   2. PythonAnywhere'e yükleyin"
echo "   3. DEPLOYMENT_GUIDE.md dosyasındaki adımları takip edin"
echo ""
echo "🎯 Deployment URL'niz: kullaniciadi.pythonanywhere.com"
echo ""

# Dosya sayısı ve boyutu göster
file_count=$(find "$DEPLOY_DIR" -type f | wc -l)
total_size=$(du -sh "$DEPLOY_DIR" | cut -f1)
echo "📊 İstatistikler:"
echo "   - Toplam dosya: $file_count"
echo "   - Toplam boyut: $total_size"
echo ""
echo "🚀 Deployment'a hazır!"
