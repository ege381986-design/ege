"""
AI Engine Module - Akıllı Kütüphane Özellikleri
Kitap önerisi, kategorizasyon, chatbot ve tahminsel analitik
"""

import os
import json
import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import pickle

class BookRecommendationEngine:
    """Kitap öneri sistemi"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words=['the', 'and', 'bir', 'bu'])
        self.similarity_matrix = None
        self.book_indices = {}
        self.trained = False
        
    def train(self, books_data):
        """Modeli eğit"""
        try:
            print("🤖 Kitap öneri sistemi eğitiliyor...")
            
            features = []
            indices = {}
            
            for i, book in enumerate(books_data):
                feature_text = f"{book.title} {book.authors}"
                features.append(feature_text)
                indices[book.isbn] = i
            
            self.book_indices = indices
            
            # TF-IDF matrisini oluştur
            tfidf_matrix = self.vectorizer.fit_transform(features)
            self.similarity_matrix = cosine_similarity(tfidf_matrix)
            
            self.trained = True
            print(f"✅ Öneri sistemi {len(books_data)} kitap ile eğitildi")
            
        except Exception as e:
            print(f"❌ Öneri sistemi eğitimi başarısız: {e}")
    
    def recommend_books(self, isbn, n_recommendations=5):
        """Kitap önerilerini al"""
        if not self.trained or isbn not in self.book_indices:
            return []
        
        try:
            book_idx = self.book_indices[isbn]
            sim_scores = list(enumerate(self.similarity_matrix[book_idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            
            # Kendisi hariç en benzer kitapları al
            similar_books = sim_scores[1:n_recommendations+1]
            return [(idx, score) for idx, score in similar_books]
            
        except Exception as e:
            print(f"❌ Öneri oluşturma hatası: {e}")
            return []

class BookCategorizer:
    """Otomatik kitap kategorizasyonu"""
    
    def __init__(self):
        self.categories = ['Roman', 'Bilim', 'Tarih', 'Edebiyat', 'Felsefe', 'Sanat', 'Teknoloji', 'Çocuk']
        self.category_keywords = {
            'Roman': ['roman', 'hikaye', 'öykü'],
            'Bilim': ['bilim', 'fizik', 'kimya', 'biyoloji'],
            'Tarih': ['tarih', 'geçmiş', 'antik'],
            'Edebiyat': ['edebiyat', 'şiir', 'poetry'],
            'Teknoloji': ['teknoloji', 'bilgisayar', 'internet'],
            'Çocuk': ['çocuk', 'massal', 'fairy']
        }
    
    def categorize_book(self, title, description=""):
        """Kitabı kategorize et"""
        text = f"{title} {description}".lower()
        
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[category] = score
        
        if scores:
            best_category = max(scores, key=scores.get)
            confidence = scores[best_category] / len(self.category_keywords[best_category])
            return best_category, min(confidence, 1.0)
        
        return 'Genel', 0.5

class DemandPredictor:
    """Kitap talep tahmini"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.trained = False
    
    def prepare_features(self, book, transactions):
        """Özellik çıkarımı"""
        features = []
        
        # Kitap özellikleri
        features.append(book.total_borrow_count or 0)
        features.append(book.average_rating or 0)
        features.append(book.quantity or 1)
        
        # Son 30 günlük ödünç alma sayısı
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        recent_borrows = len([t for t in transactions 
                            if t.isbn == book.isbn and t.borrow_date >= thirty_days_ago])
        features.append(recent_borrows)
        
        # Mevcut ödünç alma sayısı
        current_borrows = len([t for t in transactions 
                             if t.isbn == book.isbn and not t.return_date])
        features.append(current_borrows)
        
        # Mevsimsel özellik (ay)
        features.append(datetime.now().month)
        
        return features
    
    def train(self, books_data, transactions_data):
        """Talep tahmin modelini eğit"""
        try:
            print("📊 Talep tahmin modeli eğitiliyor...")
            
            X, y = [], []
            
            for book in books_data:
                features = self.prepare_features(book, transactions_data)
                
                # Hedef: gelecek 30 günlük tahmini talep
                # Basit yaklaşım: geçmiş ortalaması
                target = max(1, book.total_borrow_count // 12)  # Aylık ortalama
                
                X.append(features)
                y.append(target)
            
            if len(X) > 10:  # Minimum veri kontrolü
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                self.model.fit(X_train, y_train)
                score = self.model.score(X_test, y_test)
                
                self.trained = True
                print(f"✅ Talep tahmin modeli eğitildi (R² score: {score:.3f})")
            
        except Exception as e:
            print(f"❌ Talep tahmin modeli eğitimi başarısız: {e}")
    
    def predict_demand(self, book, transactions, days_ahead=30):
        """Talep tahmini yap"""
        if not self.trained:
            return 1  # Varsayılan tahmin
        
        try:
            features = self.prepare_features(book, transactions)
            prediction = self.model.predict([features])[0]
            return max(1, int(prediction))
            
        except Exception as e:
            print(f"❌ Talep tahmini hatası: {e}")
            return 1

class LibraryChatbot:
    """Kütüphane chatbot sistemi"""
    
    def __init__(self):
        self.responses = {
            'greeting': 'Merhaba! Size nasıl yardımcı olabilirim?',
            'book_search': 'Kitap aramak için arama çubuğunu kullanabilirsiniz.',
            'borrow_info': 'Kitap ödünç almak için önce üye olmanız gerekiyor.',
            'opening_hours': 'Kütüphanemiz Pazartesi-Cuma 08:00-17:00 arası açıktır.',
            'default': 'Üzgünüm, bu konuda size yardımcı olamıyorum.'
        }
    
    def process_message(self, message):
        """Mesajı işle ve yanıt döndür"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['merhaba', 'selam', 'hello']):
            return self.responses['greeting']
        elif any(word in message_lower for word in ['kitap', 'ara', 'search']):
            return self.responses['book_search']
        elif any(word in message_lower for word in ['ödünç', 'borrow']):
            return self.responses['borrow_info']
        elif any(word in message_lower for word in ['saat', 'açık', 'hours']):
            return self.responses['opening_hours']
        else:
            return self.responses['default']

class SmartSearch:
    """Akıllı arama sistemi"""
    
    def __init__(self):
        self.search_history = []
        self.popular_searches = []
    
    def enhance_search_query(self, query):
        """Arama sorgusunu iyileştir"""
        # Türkçe karakterleri normalize et
        replacements = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'C', 'Ğ': 'G', 'I': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
        }
        
        normalized_query = query
        for tr_char, en_char in replacements.items():
            normalized_query = normalized_query.replace(tr_char, en_char)
        
        # Yaygın yazım hatalarını düzelt
        corrections = {
            'kitap': ['kitab', 'ktap', 'kitapp'],
            'yazar': ['yazr', 'yazer'],
            'roman': ['romn', 'rman']
        }
        
        for correct, mistakes in corrections.items():
            for mistake in mistakes:
                if mistake in query.lower():
                    query = query.lower().replace(mistake, correct)
        
        return query, normalized_query
    
    def get_search_suggestions(self, partial_query, books_data):
        """Arama önerileri getir"""
        suggestions = []
        
        if len(partial_query) < 2:
            return suggestions
        
        partial_lower = partial_query.lower()
        
        # Kitap başlıklarından öneriler
        for book in books_data[:100]:  # İlk 100 kitap
            if partial_lower in book.title.lower():
                suggestions.append({
                    'text': book.title,
                    'type': 'title',
                    'isbn': book.isbn
                })
            
            if partial_lower in book.authors.lower():
                suggestions.append({
                    'text': book.authors,
                    'type': 'author',
                    'isbn': book.isbn
                })
        
        # Benzersiz önerileri döndür
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion['text'] not in seen:
                seen.add(suggestion['text'])
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:10]

# Global AI engine instance
ai_engine = {
    'recommendation': BookRecommendationEngine(),
    'categorizer': BookCategorizer(),
    'demand_predictor': DemandPredictor(),
    'chatbot': LibraryChatbot(),
    'smart_search': SmartSearch()
}

def initialize_ai_engine(books_data=None, transactions_data=None):
    """AI engine'i başlat"""
    print("🤖 AI Engine başlatılıyor...")
    
    try:
        # Öneri sistemini yükle veya eğit
        ai_engine['recommendation'].train(books_data)
        
        # Talep tahmin modelini eğit
        if books_data and transactions_data:
            ai_engine['demand_predictor'].train(books_data, transactions_data)
        
        print("✅ AI Engine başarıyla başlatıldı!")
        
    except Exception as e:
        print(f"❌ AI Engine başlatma hatası: {e}")

def get_ai_engine():
    """AI engine instance'ını al"""
    return ai_engine

print("🤖 AI Engine modülü yüklendi!") 