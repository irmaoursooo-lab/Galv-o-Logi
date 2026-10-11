/**
 * GALVÃO LOGI — MOTOR DE SINCRONIZAÇÃO OFFLINE (OUTBOX PATTERN)
 * Armazena eventos e dados da jornada localmente quando não há sinal de internet,
 * despachando automaticamente para a nuvem quando a conexão é restabelecida.
 */

class OfflineStore {
  constructor() {
    this.storageKey = 'galvao_logi_outbox_queue';
    this.routeCacheKey = 'galvao_logi_active_route';
    this.isOnline = navigator.onLine;

    window.addEventListener('online', () => this.handleConnectivityChange(true));
    window.addEventListener('offline', () => this.handleConnectivityChange(false));
  }

  getOutbox() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      return [];
    }
  }

  saveOutbox(queue) {
    localStorage.setItem(this.storageKey, JSON.stringify(queue));
    this.notifyOutboxUpdate();
  }

  enqueueEvent(eventType, payload) {
    const queue = this.getOutbox();
    const eventItem = {
      id: 'evt_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
      event_type: eventType,
      payload: payload,
      created_at_local: new Date().toISOString(),
      sync_status: 'PENDING'
    };
    queue.push(eventItem);
    this.saveOutbox(queue);

    // Tentar despachar imediatamente se estiver online
    if (this.isOnline) {
      this.syncOutbox();
    }
    return eventItem;
  }

  cacheRoute(routeData) {
    localStorage.setItem(this.routeCacheKey, JSON.stringify(routeData));
  }

  getCachedRoute() {
    try {
      const data = localStorage.getItem(this.routeCacheKey);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      return null;
    }
  }

  async syncOutbox() {
    const queue = this.getOutbox();
    const pending = queue.filter(item => item.sync_status === 'PENDING');
    if (pending.length === 0) return;

    try {
      const response = await fetch('/api/v1/sync/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          driver_id: 'motorista_principal',
          events: pending
        })
      });

      if (response.ok) {
        const result = await response.json();
        const syncedIds = new Set(result.synced_ids || []);
        
        // Atualizar status
        const updated = queue.map(item => {
          if (syncedIds.has(item.id)) {
            return { ...item, sync_status: 'SYNCED' };
          }
          return item;
        });
        
        // Manter apenas pendentes ou últimos sincronizados
        const remaining = updated.filter(item => item.sync_status === 'PENDING');
        this.saveOutbox(remaining);
        console.log(`[Galvão Logi Sync] ${result.processed_count} eventos sincronizados com sucesso.`);
      }
    } catch (err) {
      console.warn('[Galvão Logi Sync] Falha temporária ao sincronizar fila outbox:', err);
    }
  }

  handleConnectivityChange(online) {
    this.isOnline = online;
    console.log(`[Galvão Logi Network] Conectividade alterada: ${online ? 'ONLINE' : 'OFFLINE'}`);
    if (online) {
      this.syncOutbox();
    }
    this.notifyOutboxUpdate();
  }

  notifyOutboxUpdate() {
    const event = new CustomEvent('outbox_updated', {
      detail: {
        pendingCount: this.getOutbox().filter(i => i.sync_status === 'PENDING').length,
        isOnline: this.isOnline
      }
    });
    window.dispatchEvent(event);
  }
}

window.offlineStore = new OfflineStore();
