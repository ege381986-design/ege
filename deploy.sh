#!/bin/bash
echo "🚀 Starting deployment..."

# Git pull
git pull origin main

# Virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Database migration
python -c "from app import db, app; app.app_context().push(); db.create_all()"

# Collect static files
python -c "import os; os.system('find static -name \"*.pyc\" -delete')"

# Restart services
sudo systemctl restart library
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
sudo systemctl reload nginx

echo "✅ Deployment completed!" 