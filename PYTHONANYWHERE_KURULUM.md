# PythonAnywhere Kurulumu - Doğru Adımlar

⚠️ **ÖNEMLİ**: Ana klasördeki requirements.txt değil, deployment_pythonanywhere klasöründeki dosyaları kullanın!

## Doğru Adımlar:

1. **Sadece deployment_pythonanywhere klasörünü kullanın:**
   ```bash
   cd ~/mysite
   # deployment_pythonanywhere klasöründeki requirements.txt'yi kullanın
   pip install -r deployment_pythonanywhere/requirements.txt
   ```

2. **Veya dosyaları kopyalayın:**
   ```bash
   cd ~/mysite
   cp deployment_pythonanywhere/requirements.txt requirements.txt
   cp deployment_pythonanywhere/app.py app.py
   cp deployment_pythonanywhere/config.py config.py
   # ... diğer dosyaları da kopyalayın
   ```

## Optimize Edilmiş Requirements.txt İçeriği:
Ana requirements.txt (888MB torch içerir) ❌
deployment_pythonanywhere/requirements.txt (ML kütüphaneleri yok) ✅

## Eğer Hala Hata Alıyorsanız:
```bash
# Önce cache'i temizleyin
pip cache purge

# Sadece temel Flask kütüphanelerini yükleyin
pip install Flask==2.3.3
pip install Flask-SQLAlchemy==3.0.5
pip install Flask-Login==0.6.2
pip install requests==2.31.0
pip install qrcode==7.4.2
pip install reportlab==4.0.4
pip install pandas==2.0.3
pip install matplotlib==3.7.2

# Sonra eksik olanları tek tek ekleyin
```

## Toplam boyut: ~100MB (torch yok!)
