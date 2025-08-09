#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI dosyası - PythonAnywhere için
Bu dosya PythonAnywhere web uygulaması konfigürasyonunda kullanılacak
"""

import os
import sys

# Uygulama dizinini Python path'ine ekle
path = '/home/yourusername/mysite'  # Bu yolu PythonAnywhere'deki gerçek yolunuzla değiştirin
if path not in sys.path:
    sys.path.append(path)

# Flask uygulamasını import et
from app import app as application

if __name__ == "__main__":
    application.run()
