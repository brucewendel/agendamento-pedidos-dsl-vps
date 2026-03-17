let deferredPrompt;
let installButton;

window.addEventListener('load', () => {
    registerServiceWorker();
    setupInstallPrompt();
    checkIfInstalled();
    setupOnlineOfflineHandlers();
});

async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        try {
            const registration = await navigator.serviceWorker.register('/static/service-worker.js');
            console.log('✅ Service Worker registrado:', registration.scope);
            
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        showUpdateNotification();
                    }
                });
            });
        } catch (error) {
            console.error('❌ Erro ao registrar Service Worker:', error);
        }
    }
}

function setupInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        showInstallButton();
    });

    window.addEventListener('appinstalled', () => {
        console.log('✅ PWA instalado com sucesso!');
        deferredPrompt = null;
        hideInstallButton();
        showInstalledNotification();
    });
}

function showInstallButton() {
    const installBanner = document.createElement('div');
    installBanner.id = 'pwa-install-banner';
    installBanner.className = 'fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-2xl shadow-2xl p-4 z-50 transform transition-all duration-300 ease-in-out';
    installBanner.innerHTML = `
        <div class="flex items-start gap-3">
            <div class="flex-shrink-0 w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <i class="bi bi-download text-2xl"></i>
            </div>
            <div class="flex-1">
                <h3 class="font-bold text-lg mb-1">Instalar App DSL</h3>
                <p class="text-sm text-blue-100 mb-3">Acesse mais rápido e use offline!</p>
                <div class="flex gap-2">
                    <button id="install-btn" class="flex-1 bg-white text-blue-600 font-semibold py-2 px-4 rounded-lg hover:bg-blue-50 transition-colors">
                        Instalar
                    </button>
                    <button id="dismiss-install" class="px-4 py-2 text-white hover:bg-white/10 rounded-lg transition-colors">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(installBanner);
    
    setTimeout(() => {
        installBanner.style.transform = 'translateY(0)';
    }, 100);
    
    document.getElementById('install-btn').addEventListener('click', installPWA);
    document.getElementById('dismiss-install').addEventListener('click', () => {
        installBanner.style.transform = 'translateY(150%)';
        setTimeout(() => installBanner.remove(), 300);
        localStorage.setItem('pwa-install-dismissed', Date.now());
    });
    
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    if (dismissed && Date.now() - dismissed < 7 * 24 * 60 * 60 * 1000) {
        installBanner.remove();
    }
}

function hideInstallButton() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
        banner.style.transform = 'translateY(150%)';
        setTimeout(() => banner.remove(), 300);
    }
}

async function installPWA() {
    if (!deferredPrompt) return;
    
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    console.log(`Resultado da instalação: ${outcome}`);
    deferredPrompt = null;
    hideInstallButton();
}

function checkIfInstalled() {
    if (window.matchMedia('(display-mode: standalone)').matches || 
        window.navigator.standalone === true) {
        console.log('✅ App rodando como PWA instalado');
        document.body.classList.add('pwa-installed');
        addPWABadge();
    }
}

function addPWABadge() {
    const badge = document.createElement('div');
    badge.className = 'fixed top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full shadow-lg z-50 flex items-center gap-1';
    badge.innerHTML = '<i class="bi bi-check-circle-fill"></i> App Instalado';
    document.body.appendChild(badge);
    
    setTimeout(() => {
        badge.style.opacity = '0';
        setTimeout(() => badge.remove(), 300);
    }, 3000);
}

function setupOnlineOfflineHandlers() {
    window.addEventListener('online', () => {
        showConnectionStatus('online');
        syncPendingData();
    });
    
    window.addEventListener('offline', () => {
        showConnectionStatus('offline');
    });
    
    if (!navigator.onLine) {
        showConnectionStatus('offline');
    }
}

function showConnectionStatus(status) {
    const existingBanner = document.getElementById('connection-status');
    if (existingBanner) existingBanner.remove();
    
    const banner = document.createElement('div');
    banner.id = 'connection-status';
    banner.className = `fixed top-4 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-full shadow-lg z-50 flex items-center gap-2 transition-all duration-300 ${
        status === 'online' 
            ? 'bg-green-500 text-white' 
            : 'bg-orange-500 text-white'
    }`;
    banner.innerHTML = `
        <i class="bi bi-${status === 'online' ? 'wifi' : 'wifi-off'}"></i>
        <span class="font-semibold">${status === 'online' ? 'Conectado' : 'Modo Offline'}</span>
    `;
    
    document.body.appendChild(banner);
    
    setTimeout(() => {
        banner.style.opacity = '0';
        setTimeout(() => banner.remove(), 300);
    }, 3000);
}

async function syncPendingData() {
    if ('serviceWorker' in navigator && 'sync' in navigator.serviceWorker) {
        try {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('sync-agendamentos');
            console.log('✅ Sincronização em background agendada');
        } catch (error) {
            console.error('❌ Erro ao agendar sincronização:', error);
        }
    }
}

function showUpdateNotification() {
    if (window.Swal) {
        Swal.fire({
            title: 'Atualização Disponível',
            text: 'Uma nova versão do app está disponível. Deseja atualizar agora?',
            icon: 'info',
            showCancelButton: true,
            confirmButtonText: 'Atualizar',
            cancelButtonText: 'Depois',
            confirmButtonColor: '#3b82f6'
        }).then((result) => {
            if (result.isConfirmed) {
                window.location.reload();
            }
        });
    }
}

function showInstalledNotification() {
    if (window.Swal) {
        Swal.fire({
            title: 'App Instalado!',
            text: 'O DSL Agendamento foi instalado com sucesso. Agora você pode acessá-lo diretamente da tela inicial.',
            icon: 'success',
            confirmButtonText: 'Ótimo!',
            confirmButtonColor: '#10b981',
            timer: 3000
        });
    }
}

async function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        const permission = await Notification.requestPermission();
        console.log('Permissão de notificações:', permission);
        return permission === 'granted';
    }
    return Notification.permission === 'granted';
}

window.PWA = {
    install: installPWA,
    requestNotifications: requestNotificationPermission,
    isInstalled: () => window.matchMedia('(display-mode: standalone)').matches,
    isOnline: () => navigator.onLine
};
