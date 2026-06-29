const CACHE_NAME = 'wajos-v2';
const ASSETS = ['/', '/manifest.json'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;
    event.respondWith(
        caches.match(event.request).then((cached) => {
            return cached || fetch(event.request).then((response) => {
                return response;
            }).catch(() => cached);
        })
    );
});

// ===== PUSH: показ уведомления =====
self.addEventListener('push', (event) => {
    let payload = { title: 'Wajos', body: 'Новое уведомление', url: '/' };

    try {
        if (event.data) {
            // Сервер отправляет JSON: { title, body, url }
            const parsed = event.data.json();
            if (parsed && typeof parsed === 'object') {
                payload = Object.assign(payload, parsed);
            } else {
                payload.body = event.data.text();
            }
        }
    } catch (e) {
        // Если данные не JSON — используем как текст
        if (event.data) payload.body = event.data.text();
    }

    const options = {
        body: payload.body,
        icon: '/static/recipes/icon-192.png',
        badge: '/static/recipes/icon-192.png',
        data: { url: payload.url || '/' },
        vibrate: [80, 40, 80],
        requireInteraction: false,
        tag: 'wajos-push',
        renotify: true,
    };

    event.waitUntil(
        self.registration.showNotification(payload.title, options)
    );
});

// ===== КЛИК ПО УВЕДОМЛЕНИЮ: открыть страницу =====
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const targetUrl = (event.notification.data && event.notification.data.url) || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            // Если уже есть открытое окно — фокусируемся и переходим по URL
            for (const client of clientList) {
                if ('focus' in client) {
                    client.postMessage({ type: 'NAVIGATE', url: targetUrl });
                    return client.focus();
                }
            }
            // Иначе открываем новое окно
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});

// ===== ОШИБКА ПОДПИСКИ / НЕВОЗМОЖНОСТЬ ОТОБРАЗИТЬ =====
self.addEventListener('pushsubscriptionchange', (event) => {
    event.waitUntil(
        self.registration.pushManager.subscribe({
            userVisibleOnly: true
        }).then((subscription) => {
            // Передаём новую подписку на сервер
            return fetch('/api/push/subscribe/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscription)
            }).catch(() => {});
        }).catch(() => {})
    );
});
