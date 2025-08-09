/**
 * Service Worker - PWA Offline Support
 */

// Service Worker for CAL Library Management System
const CACHE_NAME = 'cal-library-v1.0.0';
const urlsToCache = [
    '/',
    '/static/css/bootstrap.min.css',
    '/static/css/style.css',
    '/static/css/dark-mode.css',
    '/static/css/enhanced.css',
    '/static/js/jquery-3.6.0.min.js',
    '/static/js/bootstrap.bundle.min.js',
    '/static/js/main.js',
    '/static/js/books-and-transactions.js',
    '/static/js/pwa.js',
    '/static/img/icon-192x192.png',
    '/static/manifest.json',
    '/offline'
];

// Install event
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('Cache açıldı');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch event
self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Cache'den döndür veya network'ten getir
                if (response) {
                    return response;
                }
                
                return fetch(event.request).catch(function() {
                    // Offline durumunda offline sayfasını göster
                    if (event.request.destination === 'document') {
                        return caches.match('/offline');
                    }
                });
            })
    );
});

// Activate event
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Push notification event
self.addEventListener('push', function(event) {
    const options = {
        body: event.data ? event.data.text() : 'Yeni bildirim',
        icon: '/static/img/icon-192x192.png',
        badge: '/static/img/icon-192x192.png',
        vibrate: [200, 100, 200],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'Görüntüle',
                icon: '/static/img/icon-192x192.png'
            },
            {
                action: 'close',
                title: 'Kapat',
                icon: '/static/img/icon-192x192.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('CAL Kütüphane', options)
    );
});

// Notification click event
self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

console.log('🔧 Service Worker yüklendi!'); 