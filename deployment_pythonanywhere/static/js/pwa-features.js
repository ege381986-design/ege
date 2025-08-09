/**
 * PWA ve Modern JavaScript Özellikleri
 * Service Worker, Push Notifications, Offline Support
 */

// Service Worker Registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('✅ Service Worker kayıtlı:', registration.scope);
                
                // Push notification desteği kontrol et
                if ('PushManager' in window) {
                    initializePushNotifications(registration);
                }
            })
            .catch(function(error) {
                console.log('❌ Service Worker kaydı başarısız:', error);
            });
    });
}

// Push Notifications
async function initializePushNotifications(registration) {
    try {
        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
            console.log('✅ Bildirim izni verildi');
            
            // VAPID public key (production'da environment variable'dan alınmalı)
            const vapidPublicKey = 'your-vapid-public-key-here';
            
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
            });
            
            // Subscription'ı sunucuya gönder
            await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(subscription)
            });
            
            console.log('✅ Push notification aboneliği oluşturuldu');
        }
    } catch (error) {
        console.error('❌ Push notification hatası:', error);
    }
}

// VAPID key conversion utility
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// PWA Install Prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    // Varsayılan install prompt'unu engelle
    e.preventDefault();
    deferredPrompt = e;
    
    // Install butonu göster
    showInstallButton();
});

function showInstallButton() {
    const installButton = document.getElementById('install-button');
    if (installButton) {
        installButton.style.display = 'block';
        installButton.addEventListener('click', installPWA);
    } else {
        // Dinamik install butonu oluştur
        createInstallButton();
    }
}

function createInstallButton() {
    const installBtn = document.createElement('button');
    installBtn.id = 'install-button';
    installBtn.className = 'btn btn-primary btn-sm position-fixed';
    installBtn.style.cssText = 'bottom: 20px; right: 20px; z-index: 1000;';
    installBtn.innerHTML = '<i class="bi bi-download"></i> Uygulamayı Yükle';
    installBtn.addEventListener('click', installPWA);
    
    document.body.appendChild(installBtn);
}

async function installPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            console.log('✅ PWA yüklendi');
        }
        
        deferredPrompt = null;
        document.getElementById('install-button').style.display = 'none';
    }
}

// Online/Offline Status
window.addEventListener('online', function() {
    showNotification('🌐 İnternet bağlantısı geri geldi', 'success');
    syncOfflineActions();
});

window.addEventListener('offline', function() {
    showNotification('📡 İnternet bağlantısı kesildi. Offline modda çalışıyorsunuz.', 'warning');
});

// Offline Actions Sync
async function syncOfflineActions() {
    try {
        const offlineActions = getOfflineActions();
        
        for (const action of offlineActions) {
            try {
                const response = await fetch(action.url, {
                    method: action.method,
                    headers: action.headers,
                    body: action.body
                });
                
                if (response.ok) {
                    removeOfflineAction(action.id);
                    console.log('✅ Offline aksiyon senkronize edildi:', action.type);
                }
            } catch (error) {
                console.log('❌ Offline aksiyon senkronizasyonu başarısız:', error);
            }
        }
    } catch (error) {
        console.error('❌ Offline senkronizasyon hatası:', error);
    }
}

// Offline Actions Storage
function saveOfflineAction(action) {
    const actions = getOfflineActions();
    action.id = Date.now();
    action.timestamp = new Date().toISOString();
    actions.push(action);
    localStorage.setItem('offlineActions', JSON.stringify(actions));
}

function getOfflineActions() {
    try {
        return JSON.parse(localStorage.getItem('offlineActions') || '[]');
    } catch (error) {
        return [];
    }
}

function removeOfflineAction(actionId) {
    const actions = getOfflineActions();
    const filteredActions = actions.filter(action => action.id !== actionId);
    localStorage.setItem('offlineActions', JSON.stringify(filteredActions));
}

// Enhanced QR Scanner
class EnhancedQRScanner {
    constructor(elementId) {
        this.elementId = elementId;
        this.scanner = null;
        this.isScanning = false;
    }
    
    async start() {
        try {
            // Html5QrcodeScanner kütüphanesi gerekli
            if (typeof Html5QrcodeScanner === 'undefined') {
                console.error('❌ Html5QrcodeScanner kütüphanesi yüklenmemiş');
                return;
            }
            
            this.scanner = new Html5QrcodeScanner(this.elementId, {
                qrbox: { width: 250, height: 250 },
                fps: 20,
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                }
            });
            
            this.scanner.render(
                (decodedText, decodedResult) => {
                    this.onScanSuccess(decodedText, decodedResult);
                },
                (error) => {
                    // Scan failure - silent
                }
            );
            
            this.isScanning = true;
            console.log('✅ QR Scanner başlatıldı');
            
        } catch (error) {
            console.error('❌ QR Scanner başlatma hatası:', error);
        }
    }
    
    stop() {
        if (this.scanner && this.isScanning) {
            this.scanner.clear();
            this.isScanning = false;
            console.log('⏹️ QR Scanner durduruldu');
        }
    }
    
    onScanSuccess(decodedText, decodedResult) {
        // Vibration feedback
        if ('vibrate' in navigator) {
            navigator.vibrate(200);
        }
        
        // Audio feedback
        this.playBeepSound();
        
        // Process scanned data
        this.processScannedData(decodedText);
        
        // Stop scanning after successful scan
        this.stop();
    }
    
    playBeepSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'square';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (error) {
            console.log('🔇 Audio feedback hatası:', error);
        }
    }
    
    processScannedData(data) {
        console.log('📱 QR Kod okundu:', data);
        
        // ISBN kontrolü
        if (this.isISBN(data)) {
            window.location.href = `/book/${data}`;
        } else {
            showNotification('QR kod işlendi: ' + data, 'info');
        }
    }
    
    isISBN(text) {
        // Basit ISBN kontrolü
        const cleanText = text.replace(/[^0-9X]/g, '');
        return cleanText.length === 10 || cleanText.length === 13;
    }
}

// Voice Search
class VoiceSearch {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            this.recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            this.recognition.lang = 'tr-TR';
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            
            this.setupEventListeners();
        }
    }
    
    setupEventListeners() {
        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.processVoiceSearch(transcript);
        };
        
        this.recognition.onerror = (event) => {
            console.error('🎤 Ses tanıma hatası:', event.error);
            this.stopListening();
        };
        
        this.recognition.onend = () => {
            this.stopListening();
        };
    }
    
    startListening() {
        if (this.recognition && !this.isListening) {
            this.recognition.start();
            this.isListening = true;
            this.showVoiceIndicator();
            console.log('🎤 Ses tanıma başlatıldı');
        }
    }
    
    stopListening() {
        this.isListening = false;
        this.hideVoiceIndicator();
    }
    
    processVoiceSearch(query) {
        console.log('🎤 Ses komutu:', query);
        
        // Search sayfasına yönlendir
        const searchUrl = `/search?q=${encodeURIComponent(query)}&type=voice`;
        window.location.href = searchUrl;
    }
    
    showVoiceIndicator() {
        // Voice indicator göster
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
    }
    
    hideVoiceIndicator() {
        // Voice indicator gizle
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
}

// Gesture Handler
class GestureHandler {
    constructor() {
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.minSwipeDistance = 50;
        
        this.init();
    }
    
    init() {
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), false);
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), false);
    }
    
    handleTouchStart(event) {
        this.touchStartX = event.changedTouches[0].screenX;
        this.touchStartY = event.changedTouches[0].screenY;
    }
    
    handleTouchEnd(event) {
        this.touchEndX = event.changedTouches[0].screenX;
        this.touchEndY = event.changedTouches[0].screenY;
        this.handleGesture();
    }
    
    handleGesture() {
        const deltaX = this.touchEndX - this.touchStartX;
        const deltaY = this.touchEndY - this.touchStartY;
        
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            // Horizontal swipe
            if (deltaX > this.minSwipeDistance) {
                this.onSwipeRight();
            } else if (deltaX < -this.minSwipeDistance) {
                this.onSwipeLeft();
            }
        } else {
            // Vertical swipe
            if (deltaY > this.minSwipeDistance) {
                this.onSwipeDown();
            } else if (deltaY < -this.minSwipeDistance) {
                this.onSwipeUp();
            }
        }
    }
    
    onSwipeLeft() {
        // Sidebar'ı kapat
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
        }
    }
    
    onSwipeRight() {
        // Sidebar'ı aç
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && !sidebar.classList.contains('show')) {
            sidebar.classList.add('show');
        }
    }
    
    onSwipeUp() {
        // Sayfanın üstüne git
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    onSwipeDown() {
        // Sayfa yenile (sadece en üstteyse)
        if (window.scrollY === 0) {
            location.reload();
        }
    }
}

// Dark Mode Toggle
function toggleDarkMode() {
    const body = document.body;
    const isDark = body.classList.contains('dark-mode');
    
    if (isDark) {
        body.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    }
    
    // Theme icon'u güncelle
    updateThemeIcon(!isDark);
}

function updateThemeIcon(isDark) {
    const themeIcon = document.querySelector('#theme-toggle i');
    if (themeIcon) {
        themeIcon.className = isDark ? 'bi bi-sun' : 'bi bi-moon';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Apply saved theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        updateThemeIcon(true);
    }
    
    // Initialize gesture handler
    new GestureHandler();
    
    // Initialize voice search
    const voiceSearch = new VoiceSearch();
    
    // Voice search button event
    const voiceButton = document.getElementById('voice-search-btn');
    if (voiceButton) {
        voiceButton.addEventListener('click', () => {
            voiceSearch.startListening();
        });
    }
    
    // Theme toggle button event
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleDarkMode);
    }
    
    console.log('🚀 PWA özellikleri yüklendi');
});

// Utility function for notifications
function showNotification(message, type = 'info') {
    // Bootstrap toast veya basit alert kullan
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        // Bootstrap toast implementation
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'warning' ? 'warning' : type === 'error' ? 'danger' : 'primary'} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        // Toast container oluştur veya kullan
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Toast'ı otomatik temizle
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    } else {
        // Fallback: basit alert
        alert(message);
    }
}

console.log('✅ PWA Features modülü yüklendi!'); 