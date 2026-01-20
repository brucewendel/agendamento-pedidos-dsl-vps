const DB_NAME = 'DSL-DB';
const DB_VERSION = 1;
const STORES = {
    AGENDAMENTOS: 'pending-agendamentos',
    PEDIDOS: 'cached-pedidos',
    USUARIOS: 'cached-usuarios'
};

let db;

async function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            if (!db.objectStoreNames.contains(STORES.AGENDAMENTOS)) {
                const agendamentosStore = db.createObjectStore(STORES.AGENDAMENTOS, { 
                    keyPath: 'id', 
                    autoIncrement: true 
                });
                agendamentosStore.createIndex('timestamp', 'timestamp', { unique: false });
                agendamentosStore.createIndex('synced', 'synced', { unique: false });
            }
            
            if (!db.objectStoreNames.contains(STORES.PEDIDOS)) {
                const pedidosStore = db.createObjectStore(STORES.PEDIDOS, { 
                    keyPath: 'NUMPED' 
                });
                pedidosStore.createIndex('timestamp', 'timestamp', { unique: false });
            }
            
            if (!db.objectStoreNames.contains(STORES.USUARIOS)) {
                db.createObjectStore(STORES.USUARIOS, { 
                    keyPath: 'CODUSUR' 
                });
            }
        };
    });
}

async function saveToIndexedDB(storeName, data) {
    if (!db) await initDB();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        
        data.timestamp = Date.now();
        data.synced = false;
        
        const request = store.add(data);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function getFromIndexedDB(storeName, key) {
    if (!db) await initDB();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readonly');
        const store = transaction.objectStore(storeName);
        const request = key ? store.get(key) : store.getAll();
        
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function updateInIndexedDB(storeName, data) {
    if (!db) await initDB();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.put(data);
        
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function deleteFromIndexedDB(storeName, key) {
    if (!db) await initDB();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.delete(key);
        
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

async function clearStore(storeName) {
    if (!db) await initDB();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.clear();
        
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

async function saveAgendamentoOffline(agendamento) {
    try {
        const id = await saveToIndexedDB(STORES.AGENDAMENTOS, agendamento);
        console.log('✅ Agendamento salvo offline:', id);
        
        showOfflineNotification('Agendamento salvo offline. Será sincronizado quando voltar online.');
        
        if ('serviceWorker' in navigator && 'sync' in navigator.serviceWorker) {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('sync-agendamentos');
        }
        
        return id;
    } catch (error) {
        console.error('❌ Erro ao salvar offline:', error);
        throw error;
    }
}

async function getPendingAgendamentos() {
    try {
        const agendamentos = await getFromIndexedDB(STORES.AGENDAMENTOS);
        return agendamentos.filter(a => !a.synced);
    } catch (error) {
        console.error('❌ Erro ao buscar agendamentos pendentes:', error);
        return [];
    }
}

async function syncAgendamentos() {
    if (!navigator.onLine) {
        console.log('⚠️ Offline - sincronização adiada');
        return;
    }
    
    try {
        const pending = await getPendingAgendamentos();
        
        if (pending.length === 0) {
            console.log('✅ Nenhum agendamento pendente para sincronizar');
            return;
        }
        
        console.log(`🔄 Sincronizando ${pending.length} agendamento(s)...`);
        
        for (const agendamento of pending) {
            try {
                const response = await fetch('/api/agendamentos', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(agendamento)
                });
                
                if (response.ok) {
                    agendamento.synced = true;
                    await updateInIndexedDB(STORES.AGENDAMENTOS, agendamento);
                    console.log('✅ Agendamento sincronizado:', agendamento.id);
                }
            } catch (error) {
                console.error('❌ Erro ao sincronizar agendamento:', error);
            }
        }
        
        await clearSyncedItems();
        showSyncNotification(pending.length);
        
    } catch (error) {
        console.error('❌ Erro na sincronização:', error);
    }
}

async function clearSyncedItems() {
    try {
        const all = await getFromIndexedDB(STORES.AGENDAMENTOS);
        const synced = all.filter(a => a.synced);
        
        for (const item of synced) {
            await deleteFromIndexedDB(STORES.AGENDAMENTOS, item.id);
        }
        
        console.log(`🗑️ ${synced.length} item(ns) sincronizado(s) removido(s)`);
    } catch (error) {
        console.error('❌ Erro ao limpar itens sincronizados:', error);
    }
}

async function cachePedidos(pedidos) {
    try {
        for (const pedido of pedidos) {
            await saveToIndexedDB(STORES.PEDIDOS, pedido);
        }
        console.log(`✅ ${pedidos.length} pedido(s) em cache`);
    } catch (error) {
        console.error('❌ Erro ao cachear pedidos:', error);
    }
}

async function getCachedPedidos() {
    try {
        return await getFromIndexedDB(STORES.PEDIDOS);
    } catch (error) {
        console.error('❌ Erro ao buscar pedidos em cache:', error);
        return [];
    }
}

function showOfflineNotification(message) {
    if (window.Swal) {
        Swal.fire({
            icon: 'info',
            title: 'Modo Offline',
            text: message,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
        });
    }
}

function showSyncNotification(count) {
    if (window.Swal) {
        Swal.fire({
            icon: 'success',
            title: 'Sincronizado!',
            text: `${count} agendamento(s) sincronizado(s) com sucesso.`,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
        });
    }
}

window.addEventListener('online', () => {
    console.log('🌐 Conexão restaurada - iniciando sincronização...');
    syncAgendamentos();
});

initDB().then(() => {
    console.log('✅ IndexedDB inicializado');
    
    if (navigator.onLine) {
        syncAgendamentos();
    }
});

window.OfflineSync = {
    saveAgendamento: saveAgendamentoOffline,
    getPending: getPendingAgendamentos,
    sync: syncAgendamentos,
    cachePedidos: cachePedidos,
    getCachedPedidos: getCachedPedidos
};
