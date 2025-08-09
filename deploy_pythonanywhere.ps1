# Kütüphane Yönetim Sistemi - PythonAnywhere Deployment Script (Windows)
# PowerShell ile çalıştırın: .\deploy_pythonanywhere.ps1

Write-Host "🚀 Kütüphane Yönetim Sistemi - PythonAnywhere Deployment Hazırlığı" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green

# Deployment klasörü oluştur
$DEPLOY_DIR = "deployment_pythonanywhere"
Write-Host "📁 $DEPLOY_DIR klasörü oluşturuluyor..." -ForegroundColor Yellow

if (Test-Path $DEPLOY_DIR) {
    Remove-Item -Recurse -Force $DEPLOY_DIR
}
New-Item -ItemType Directory -Path $DEPLOY_DIR | Out-Null

# Temel dosyaları kopyala
Write-Host "📋 Temel dosyalar kopyalanıyor..." -ForegroundColor Yellow

$filesToCopy = @(
    @{Source = "app_pythonanywhere.py"; Destination = "$DEPLOY_DIR\app.py"},
    @{Source = "wsgi.py"; Destination = "$DEPLOY_DIR\wsgi.py"},
    @{Source = "config_pythonanywhere.py"; Destination = "$DEPLOY_DIR\config.py"},
    @{Source = "models.py"; Destination = "$DEPLOY_DIR\models.py"},
    @{Source = "routes.py"; Destination = "$DEPLOY_DIR\routes.py"},
    @{Source = "api.py"; Destination = "$DEPLOY_DIR\api.py"},
    @{Source = "utils.py"; Destination = "$DEPLOY_DIR\utils.py"},
    @{Source = "requirements_pythonanywhere.txt"; Destination = "$DEPLOY_DIR\requirements.txt"},
    @{Source = "DEPLOYMENT_GUIDE.md"; Destination = "$DEPLOY_DIR\DEPLOYMENT_GUIDE.md"}
)

foreach ($file in $filesToCopy) {
    if (Test-Path $file.Source) {
        Copy-Item $file.Source $file.Destination
        Write-Host "   ✅ $($file.Source) kopyalandı" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️ $($file.Source) bulunamadı!" -ForegroundColor Red
    }
}

# Template ve static klasörlerini kopyala
Write-Host "🎨 Templates ve static dosyalar kopyalanıyor..." -ForegroundColor Yellow

if (Test-Path "templates") {
    Copy-Item -Recurse "templates" $DEPLOY_DIR
    Write-Host "   ✅ templates klasörü kopyalandı" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ templates klasörü bulunamadı!" -ForegroundColor Red
}

if (Test-Path "static") {
    Copy-Item -Recurse "static" $DEPLOY_DIR
    Write-Host "   ✅ static klasörü kopyalandı" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ static klasörü bulunamadı!" -ForegroundColor Red
}

# Gerekli klasörleri oluştur
Write-Host "📂 Gerekli klasörler oluşturuluyor..." -ForegroundColor Yellow

$directories = @("uploads", "reports", "backups", "instance")
foreach ($dir in $directories) {
    $fullPath = Join-Path $DEPLOY_DIR $dir
    New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    Write-Host "   ✅ $dir klasörü oluşturuldu" -ForegroundColor Green
}

# .env template oluştur
Write-Host "⚙️ Environment dosyası oluşturuluyor..." -ForegroundColor Yellow

$envTemplate = @"
# Gmail yapılandırması
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password

# Güvenlik
SECRET_KEY=your-secret-key-here-change-this

# Kütüphane bilgileri
LIBRARY_NAME=Cumhuriyet Anadolu Lisesi Kütüphanesi
LIBRARY_EMAIL=kutuphane@cal.edu.tr
LIBRARY_PHONE=0312 XXX XX XX
"@

$envTemplate | Out-File -FilePath "$DEPLOY_DIR\.env.template" -Encoding UTF8

# Deployment talimatları oluştur
Write-Host "📖 Deployment talimatları oluşturuluyor..." -ForegroundColor Yellow

$installMd = @"
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
"@

$installMd | Out-File -FilePath "$DEPLOY_DIR\INSTALL.md" -Encoding UTF8

# ZIP dosyası oluştur (eğer 7-Zip varsa)
Write-Host "📦 Zip arşivi oluşturuluyor..." -ForegroundColor Yellow

try {
    if (Get-Command "7z" -ErrorAction SilentlyContinue) {
        & 7z a -tzip "$DEPLOY_DIR.zip" "$DEPLOY_DIR\*"
        Write-Host "   ✅ ZIP arşivi oluşturuldu (7-Zip)" -ForegroundColor Green
    } else {
        # PowerShell ile zip oluştur
        Compress-Archive -Path "$DEPLOY_DIR\*" -DestinationPath "$DEPLOY_DIR.zip" -Force
        Write-Host "   ✅ ZIP arşivi oluşturuldu (PowerShell)" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️ ZIP oluşturulamadı: $($_.Exception.Message)" -ForegroundColor Red
}

# Özet bilgiler
Write-Host ""
Write-Host "✅ Deployment hazırlığı tamamlandı!" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Oluşturulan dosyalar:" -ForegroundColor Cyan
Write-Host "   - $DEPLOY_DIR\ klasörü"
if (Test-Path "$DEPLOY_DIR.zip") {
    Write-Host "   - $DEPLOY_DIR.zip arşivi"
}
Write-Host ""
Write-Host "📋 Sonraki adımlar:" -ForegroundColor Cyan
Write-Host "   1. $DEPLOY_DIR.zip dosyasını PythonAnywhere'e yükleyin"
Write-Host "   2. DEPLOYMENT_GUIDE.md dosyasındaki adımları takip edin"
Write-Host ""
Write-Host "🎯 Deployment URL'niz: kullaniciadi.pythonanywhere.com" -ForegroundColor Magenta
Write-Host ""

# Dosya sayısı ve boyutu göster
$fileCount = (Get-ChildItem -Recurse $DEPLOY_DIR -File).Count
$totalSize = [math]::Round((Get-ChildItem -Recurse $DEPLOY_DIR | Measure-Object -Property Length -Sum).Sum / 1MB, 2)

Write-Host "📊 İstatistikler:" -ForegroundColor Cyan
Write-Host "   - Toplam dosya: $fileCount"
Write-Host "   - Toplam boyut: $totalSize MB"
Write-Host ""
Write-Host "🚀 Deployment'a hazır!" -ForegroundColor Green

# Klasörü dosya gezgininde aç
Write-Host "📂 Deployment klasörünü açmak istiyor musunuz? (Y/N): " -NoNewline -ForegroundColor Yellow
$response = Read-Host
if ($response -eq 'Y' -or $response -eq 'y') {
    Start-Process explorer.exe -ArgumentList (Resolve-Path $DEPLOY_DIR).Path
}
