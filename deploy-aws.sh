#!/bin/bash
echo "🚀 AWS Deployment başlıyor..."

# Build and upload to S3
echo "📦 Static files S3'e yükleniyor..."
aws s3 sync static/ s3://library-static-files/static/ --delete

# Database migration
echo "🗄️ Database migration..."
python manage.py db upgrade

# Application restart
echo "🔄 Application restart..."
sudo systemctl restart library
sudo systemctl restart nginx

# Health check
echo "🏥 Health check..."
curl -f http://localhost/health || exit 1

echo "✅ Deployment tamamlandı!" 