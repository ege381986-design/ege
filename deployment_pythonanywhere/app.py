#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PythonAnywhere için Ana Uygulama Dosyası
Basitleştirilmiş ve optimize edilmiş versiyon
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# PythonAnywhere için basit import
from config import app, db, login_manager, mail
print("✅ PythonAnywhere configuration loaded!")

# Import all models (this creates the database tables)
from models import *

# Import all utility functions (sadece temel olanları)
try:
    from utils import *
    print("✅ Utils loaded!")
except ImportError as e:
    print(f"⚠️ Some utils not loaded: {e}")

# Import all routes (web pages)
try:
    from routes import *
    print("✅ Routes loaded!")
except ImportError as e:
    print(f"❌ Routes error: {e}")

# Import basic API endpoints
try:
    from api import *
    print("✅ Basic API loaded!")
except ImportError as e:
    print(f"⚠️ API not loaded: {e}")

# Optional: Advanced features (sadece eğer mevcut ise)
try:
    from api_extended import *
    print("✅ Extended API loaded!")
except ImportError:
    print("ℹ️ Extended API not available (optional)")

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Main application entry point
if __name__ == '__main__':
    with app.app_context():
        try:
            # Ensure database tables exist
            db.create_all()
            print("✅ Database tables created/verified")
        except Exception as e:
            print(f"❌ Database error: {e}")
    
    # Run the application
    app.run(debug=False)
