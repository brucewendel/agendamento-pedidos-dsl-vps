const CACHE_NAME = 'dsl-agendamento-v1.0.2';
const OFFLINE_URL = '/offline';

const PRECACHE_ASSETS = [
    '/',
    '/login',
    '/painel',
    '/static/manifest.json',
    'https://cdn.tailwindcss.com',
    'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
    'https://cdn.jsdelivr.net/npm/sweetalert2@11',
    'https://cdn.plot.ly/plotly-3.6.0.min.js'
];

self.addEventListener('install', (event) => {
    console.log('[Service Worker] Instalando...');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Service Worker] Pré-cache de assets');
            return cache.addAll(PRECACHE_ASSETS).catch(err => {
                console.warn('[Service Worker] Erro no pré-cache:', err);
            });
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Ativando...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[Service Worker] Removendo cache antigo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Ignorar requisições que não sejam GET
    if (event.request.method !== 'GET') return;

    // Ignorar requisições que não sejam HTTP/HTTPS (chrome-extension, etc)
    const url = new URL(event.request.url);
    if (!url.protocol.startsWith('http')) {
        return;
    }

    // Ignorar requisições de API - sempre buscar do servidor
    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(JSON.stringify({ 
                    offline: true, 
                    message: 'Você está offline. Dados serão sincronizados quando voltar online.' 
                }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // Cache-first strategy para recursos estáticos
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Só cachear respostas válidas
                if (response && response.status === 200 && response.type === 'basic') {
                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }
                return response;
            })
            .catch(() => {
                return caches.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    if (event.request.mode === 'navigate') {
                        return caches.match(OFFLINE_URL);
                    }
                });
            })
    );
});

self.addEventListener('sync', (event) => {
    console.log('[Service Worker] Sincronização em background:', event.tag);
    
    if (event.tag === 'sync-agendamentos') {
        event.waitUntil(syncAgendamentos());
    }
});

self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'DSL Agendamento';
    const options = {
        body: data.body || 'Nova notificação',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        data: data.url || '/',
        actions: [
            { action: 'open', title: 'Abrir', icon: '/static/icons/icon-72x72.png' },
            { action: 'close', title: 'Fechar', icon: '/static/icons/icon-72x72.png' }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'open' || !event.action) {
        const urlToOpen = event.notification.data || '/';
        event.waitUntil(
            clients.openWindow(urlToOpen)
        );
    }
});

async function syncAgendamentos() {
    try {
        const pendingData = await getFromIndexedDB('pending-agendamentos');
        if (pendingData && pendingData.length > 0) {
            for (const item of pendingData) {
                await fetch('/api/agendamentos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(item)
                });
            }
            await clearIndexedDB('pending-agendamentos');
            console.log('[Service Worker] Agendamentos sincronizados com sucesso');
        }
    } catch (error) {
        console.error('[Service Worker] Erro na sincronização:', error);
    }
}

async function getFromIndexedDB(storeName) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('DSL-DB', 1);
        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const getRequest = store.getAll();
            getRequest.onsuccess = () => resolve(getRequest.result);
            getRequest.onerror = () => reject(getRequest.error);
        };
        request.onerror = () => reject(request.error);
    });
}

async function clearIndexedDB(storeName) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('DSL-DB', 1);
        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const clearRequest = store.clear();
            clearRequest.onsuccess = () => resolve();
            clearRequest.onerror = () => reject(clearRequest.error);
        };
        request.onerror = () => reject(request.error);
    });
}
