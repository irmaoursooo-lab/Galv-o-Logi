/**
 * GALVÃO LOGI — CONTROLE PRINCIPAL DO COCKPIT
 * Suporte a Seleção de Região Dinâmica, GPS Real, Modo Mudo e Arquitetura Offline-First.
 */

let currentRouteData = null;
let currentRegionConfig = null;
let selectedDelayMinutes = 60;
let simulatedAlternativeActive = false;
let autoAcceptTimer = null;

// Presets Regionais para Testes Rápidos em Qualquer Estado do Brasil
const REGIONS = {
  SP: {
    name: "São Paulo & Grande SP",
    start_latitude: -23.5300,
    start_longitude: -46.6500,
    start_address: "Centro de Operações Logísticas - SP",
    departure_time: "07:30",
    destinations: [
      { name: "Mercado Central Doca Sul", address: "Av. das Amoras, 420 - Box 14", latitude: -23.5489, longitude: -46.6388, service_time_minutes: 45 },
      { name: "Centro de Distribuição Anhanguera", address: "Rodovia Anhanguera, KM 18", latitude: -23.4920, longitude: -46.7350, service_time_minutes: 40 },
      { name: "Galpão Logístico Mooca", address: "Rua dos Trilhos, 1200", latitude: -23.5550, longitude: -46.6020, service_time_minutes: 30 },
      { name: "Hipermercado Tamboré Docas 1-4", address: "Alameda Araguaia, 800", latitude: -23.5010, longitude: -46.8520, service_time_minutes: 35 }
    ]
  },
  RJ: {
    name: "Rio de Janeiro & Baixada",
    start_latitude: -22.8123,
    start_longitude: -43.2480,
    start_address: "Polo Logístico Galeão - Rio de Janeiro",
    departure_time: "07:30",
    destinations: [
      { name: "Porto do Rio Cais do Caju", address: "Rua General Severiano, 100", latitude: -22.8910, longitude: -43.2130, service_time_minutes: 45 },
      { name: "Centro de Distribuição Pavuna", address: "Rodovia Presidente Dutra, KM 164", latitude: -22.8080, longitude: -43.3640, service_time_minutes: 40 },
      { name: "Hipermercado Barra da Tijuca", address: "Av. das Américas, 5000", latitude: -22.9990, longitude: -43.3650, service_time_minutes: 30 },
      { name: "Terminal Logístico Caxias", address: "Rodovia Washington Luís, KM 120", latitude: -22.7850, longitude: -43.3050, service_time_minutes: 35 }
    ]
  },
  MG: {
    name: "Belo Horizonte & Contagem",
    start_latitude: -19.9320,
    start_longitude: -44.0530,
    start_address: "Distrito Industrial de Contagem - MG",
    departure_time: "07:30",
    destinations: [
      { name: "Ceasa Minas Pavilhão 5", address: "Rodovia BR-040, KM 688", latitude: -19.8870, longitude: -44.0620, service_time_minutes: 45 },
      { name: "Centro de Distribuição Betim", address: "Rodovia Fernão Dias, KM 480", latitude: -19.9670, longitude: -44.1980, service_time_minutes: 40 },
      { name: "Distribuidora Anel Rodoviário", address: "Anel Rodoviário Celso Mello Azevedo", latitude: -19.9120, longitude: -43.9850, service_time_minutes: 30 },
      { name: "Mercado Central de BH", address: "Av. Augusto de Lima, 744", latitude: -19.9230, longitude: -43.9440, service_time_minutes: 35 }
    ]
  },
  PR: {
    name: "Curitiba & Região Metropolitana",
    start_latitude: -25.5080,
    start_longitude: -49.3250,
    start_address: "Cidade Industrial de Curitiba (CIC) - PR",
    departure_time: "07:30",
    destinations: [
      { name: "Polo Logístico Araucária", address: "Rodovia do Xisto, KM 14", latitude: -25.5890, longitude: -49.4050, service_time_minutes: 45 },
      { name: "Centro de Distribuição Pinhais", address: "Av. Ayrton Senna da Silva, 2500", latitude: -25.4380, longitude: -49.1920, service_time_minutes: 40 },
      { name: "Mercado Municipal Curitiba", address: "Av. Sete de Setembro, 1865", latitude: -25.4330, longitude: -49.2570, service_time_minutes: 30 },
      { name: "Ceasa Curitiba BR-116", address: "BR-116, KM 111", latitude: -25.5340, longitude: -49.2780, service_time_minutes: 35 }
    ]
  },
  RS: {
    name: "Porto Alegre & Vale dos Sinos",
    start_latitude: -29.9880,
    start_longitude: -51.1850,
    start_address: "Porto Seco de Porto Alegre - RS",
    departure_time: "07:30",
    destinations: [
      { name: "Complexo Logístico Canoas", address: "BR-116, KM 265", latitude: -29.9180, longitude: -51.1750, service_time_minutes: 45 },
      { name: "Distrito Industrial Novo Hamburgo", address: "RS-239, KM 12", latitude: -29.6880, longitude: -51.1350, service_time_minutes: 40 },
      { name: "Ceasa Rio Grande do Sul", address: "Av. Fernando Ferrari, 1001", latitude: -29.9720, longitude: -51.1680, service_time_minutes: 30 },
      { name: "Mercado Público Porto Alegre", address: "Largo Glênio Peres, s/n", latitude: -30.0270, longitude: -51.2280, service_time_minutes: 35 }
    ]
  }
};

let pendingScannedDestinations = [];
window.hasExplicitStartPoint = false;
window.currentDriverLat = -23.5300;
window.currentDriverLon = -46.6500;
window.currentDriverAddress = "Garagem / Ponto de Partida";

document.addEventListener('DOMContentLoaded', async () => {
  window.mapEngine = new MapEngine('map-container');

  // Inicializar estado do botão de voz (Mudo vs Ativado)
  updateMuteButtonUI(window.voiceCopilot.isMuted);

  // Registrar listener da fila offline
  window.addEventListener('outbox_updated', (e) => {
    updateNetworkStatus(e.detail.isOnline, e.detail.pendingCount);
  });

  // Tentar obter GPS do motorista para servir de ponto de partida
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        window.currentDriverLat = pos.coords.latitude;
        window.currentDriverLon = pos.coords.longitude;
        window.currentDriverAddress = `Localização GPS (${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)})`;
        window.hasExplicitStartPoint = true;
        if (window.mapEngine && window.mapEngine.map) {
          window.mapEngine.map.setView([pos.coords.latitude, pos.coords.longitude], 12);
        }
      },
      () => {},
      { timeout: 6000 }
    );
  }

  // Verificar se o usuário já possui um roteiro ativo salvo por ele
  const savedCustom = localStorage.getItem('galvao_custom_route');
  if (savedCustom) {
    try {
      currentRouteData = JSON.parse(savedCustom);
      renderCockpitData(currentRouteData);
      return;
    } catch (e) {
      localStorage.removeItem('galvao_custom_route');
    }
  }

  // SE NÃO HÁ ROTA DO USUÁRIO: Não carrega rotas falsas indesejadas!
  // Exibe o Cockpit Limpo com prontidão para o usuário adicionar seus destinos.
  showIdleCockpitState();
});

function showIdleCockpitState() {
  if (typeof stopNavigation === 'function') {
    stopNavigation();
  }
  const btnStart = document.getElementById('btn-start-navigation');
  if (btnStart) btnStart.style.display = 'none';
  const hudBar = document.getElementById('navigation-hud-bar');
  if (hudBar) hudBar.style.display = 'none';

  currentRouteData = null;
  if (window.mapEngine) {
    window.mapEngine.clearLayers();
  }

  const welcomeCard = document.getElementById('cockpit-welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'flex';

  document.getElementById('hud-next-stop').textContent = 'Aguardando Destinos';
  document.getElementById('hud-next-address').textContent = 'Tire fotos das notas fiscais ou digite os endereços';
  document.getElementById('hud-eta').textContent = '--:--';

  document.getElementById('metric-stops').textContent = '0';
  document.getElementById('metric-distance').textContent = '0.0 km';
  document.getElementById('metric-finish').textContent = '--:--';

  const list = document.getElementById('drawer-stops-list');
  if (list) {
    list.innerHTML = '<div style="padding:24px; color:#86868B; text-align:center; font-size:14px;">Nenhum destino ativo.<br>Toque em 📸 ou ✏️ para incluir entregas.</div>';
  }
}

function clearActiveRoute() {
  window.voiceCopilot.vibrate(50);
  localStorage.removeItem('galvao_custom_route');
  localStorage.removeItem('galvao_selected_region');
  showIdleCockpitState();
  showToast('🗑️ Roteiro limpo com sucesso.');
  window.voiceCopilot.speak('Roteiro limpo. Aguardando novos destinos.');
}

/* -------------------------------------------------------------
 * 1. LEITURA DE NOTAS FISCAIS / ITINERÁRIOS POR FOTO (LGPD CLEAN)
 * ------------------------------------------------------------- */
function openScanModal() {
  window.voiceCopilot.vibrate(30);
  pendingScannedDestinations = [];
  document.getElementById('scanned-destinations-list').style.display = 'none';
  document.getElementById('scanned-items-box').innerHTML = '';
  document.getElementById('btn-confirm-scanned').style.display = 'none';
  document.getElementById('scan-loading-indicator').style.display = 'none';
  document.getElementById('invoice-file-input').value = '';
  document.getElementById('scan-modal').style.display = 'flex';
}

function closeScanModal() {
  window.voiceCopilot.vibrate(20);
  document.getElementById('scan-modal').style.display = 'none';
}

async function handleInvoicesUpload(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  const loadingEl = document.getElementById('scan-loading-indicator');
  loadingEl.style.display = 'block';

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  formData.append('base_latitude', window.currentDriverLat);
  formData.append('base_longitude', window.currentDriverLon);

  try {
    const res = await fetch('/api/v1/routes/scan-invoices', {
      method: 'POST',
      body: formData
    });

    loadingEl.style.display = 'none';

    if (!res.ok) {
      showToast('❌ Falha ao processar imagens das notas fiscais.');
      return;
    }

    const data = await res.json();
    pendingScannedDestinations = data.destinations || [];

    if (pendingScannedDestinations.length === 0) {
      showToast('⚠️ Nenhum endereço de entrega localizado no documento.');
      return;
    }

    renderScannedDestinationsList();
    showToast(`✅ ${pendingScannedDestinations.length} destino(s) identificado(s). Dados sensíveis purgados!`);
    window.voiceCopilot.speak(`${pendingScannedDestinations.length} destinos identificados. Dados sensíveis purgados.`);
  } catch (err) {
    loadingEl.style.display = 'none';
    console.error('Erro ao ler notas fiscais:', err);
    showToast('⚠️ Erro de conexão ao enviar documentos.');
  }
}

function renderScannedDestinationsList() {
  const container = document.getElementById('scanned-destinations-list');
  const itemsBox = document.getElementById('scanned-items-box');
  const confirmBtn = document.getElementById('btn-confirm-scanned');

  itemsBox.innerHTML = '';
  pendingScannedDestinations.forEach((dest, index) => {
    const item = document.createElement('div');
    item.className = 'scanned-item';
    item.innerHTML = `
      <div class="scanned-item-text">
        <strong>${index + 1}. ${dest.name}</strong>
        <small>${dest.address}</small>
      </div>
      <button class="btn-remove-scanned" onclick="removeScannedDestination(${index})">✕</button>
    `;
    itemsBox.appendChild(item);
  });

  container.style.display = 'block';
  confirmBtn.style.display = 'block';
}

function removeScannedDestination(index) {
  pendingScannedDestinations.splice(index, 1);
  if (pendingScannedDestinations.length === 0) {
    document.getElementById('scanned-destinations-list').style.display = 'none';
    document.getElementById('btn-confirm-scanned').style.display = 'none';
  } else {
    renderScannedDestinationsList();
  }
}

async function confirmScannedDestinations() {
  if (!pendingScannedDestinations || pendingScannedDestinations.length === 0) return;
  closeScanModal();
  await calculateAndApplyRoute(pendingScannedDestinations);
}

/* -------------------------------------------------------------
 * 2. ADIÇÃO E BUSCA DE ENDEREÇOS COM AUTOCOMPLETE EM TEMPO REAL
 * ------------------------------------------------------------- */
let addressModalMode = 'default'; // 'default' | 'add_stop' | 'set_start'
let selectedPlaceSuggestion = null;
let searchDebounceTimer = null;
let currentDestinations = [];
let editingStopIndex = -1;

function openManualAddressModal(mode = 'default') {
  addressModalMode = mode;
  selectedPlaceSuggestion = null;
  window.voiceCopilot.vibrate(30);

  const searchInput = document.getElementById('place-search-input');
  if (searchInput) searchInput.value = '';
  const clearBtn = document.getElementById('btn-clear-search');
  if (clearBtn) clearBtn.style.display = 'none';

  const previewCard = document.getElementById('selected-place-card');
  if (previewCard) previewCard.style.display = 'none';

  const suggestionsList = document.getElementById('place-suggestions-list');
  if (suggestionsList) {
    suggestionsList.innerHTML = '';
    suggestionsList.style.display = 'none';
  }

  const spinner = document.getElementById('place-search-spinner');
  if (spinner) spinner.style.display = 'none';

  const titleEl = document.querySelector('#manual-address-modal .modal-header-title');
  if (titleEl) {
    if (mode === 'set_start') {
      titleEl.textContent = '🏠 Definir Ponto de Partida';
    } else if (mode === 'add_stop') {
      titleEl.textContent = '➕ Adicionar Parada ao Itinerário';
    } else {
      titleEl.textContent = '📍 Buscar Estabelecimentos & Endereços';
    }
  }

  switchAddressModalTab('search');
  document.getElementById('manual-address-modal').style.display = 'flex';

  setTimeout(() => {
    if (searchInput) searchInput.focus();
  }, 100);
}

function closeManualAddressModal() {
  window.voiceCopilot.vibrate(20);
  document.getElementById('manual-address-modal').style.display = 'none';
}

function switchAddressModalTab(tab) {
  const btnSearch = document.getElementById('tab-btn-search');
  const btnBatch = document.getElementById('tab-btn-batch');
  const contentSearch = document.getElementById('tab-content-search');
  const contentBatch = document.getElementById('tab-content-batch');

  if (tab === 'search') {
    if (btnSearch) btnSearch.classList.add('active');
    if (btnBatch) btnBatch.classList.remove('active');
    if (contentSearch) contentSearch.style.display = 'block';
    if (contentBatch) contentBatch.style.display = 'none';
  } else {
    if (btnBatch) btnBatch.classList.add('active');
    if (btnSearch) btnSearch.classList.remove('active');
    if (contentBatch) contentBatch.style.display = 'block';
    if (contentSearch) contentSearch.style.display = 'none';
  }
}

function clearPlaceSearchInput() {
  const searchInput = document.getElementById('place-search-input');
  if (searchInput) {
    searchInput.value = '';
    searchInput.focus();
  }
  const clearBtn = document.getElementById('btn-clear-search');
  if (clearBtn) clearBtn.style.display = 'none';

  const suggestionsList = document.getElementById('place-suggestions-list');
  if (suggestionsList) {
    suggestionsList.innerHTML = '';
    suggestionsList.style.display = 'none';
  }

  const previewCard = document.getElementById('selected-place-card');
  if (previewCard) previewCard.style.display = 'none';
}

let currentSuggestions = [];
let highlightedSuggestionIndex = -1;

function handlePlaceSearchInput(event) {
  const query = event.target.value.trim();
  const clearBtn = document.getElementById('btn-clear-search');
  if (clearBtn) clearBtn.style.display = query ? 'flex' : 'none';

  if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
  highlightedSuggestionIndex = -1;

  const previewCard = document.getElementById('selected-place-card');
  if (previewCard) previewCard.style.display = 'none';

  if (!query || query.length < 2) {
    const suggestionsList = document.getElementById('place-suggestions-list');
    if (suggestionsList) {
      suggestionsList.innerHTML = '';
      suggestionsList.style.display = 'none';
    }
    const spinner = document.getElementById('place-search-spinner');
    if (spinner) spinner.style.display = 'none';
    currentSuggestions = [];
    return;
  }

  const spinner = document.getElementById('place-search-spinner');
  if (spinner) spinner.style.display = 'block';

  searchDebounceTimer = setTimeout(() => {
    executePlaceSearch(query);
  }, 200);
}

async function executePlaceSearch(query) {
  const spinner = document.getElementById('place-search-spinner');
  if (spinner) spinner.style.display = 'block';

  try {
    let url = `/api/v1/routes/search-places?q=${encodeURIComponent(query)}&limit=6`;
    // Passar bias de localização apenas se o motorista já possuir ponto fixado por GPS ou escolha do usuário
    if (window.hasExplicitStartPoint && window.currentDriverLat) {
      url += `&base_lat=${window.currentDriverLat}&base_lon=${window.currentDriverLon}`;
    }

    const res = await fetch(url);
    if (spinner) spinner.style.display = 'none';

    if (res.ok) {
      const places = await res.json();
      currentSuggestions = places || [];
      renderPlaceSuggestions(places);
    }
  } catch (err) {
    if (spinner) spinner.style.display = 'none';
    console.warn('Erro ao buscar sugestões:', err);
  }
}

function handlePlaceSearchKeydown(event) {
  const list = document.getElementById('place-suggestions-list');
  const items = list ? list.querySelectorAll('.place-suggestion-item') : [];

  if (event.key === 'ArrowDown') {
    event.preventDefault();
    if (items.length > 0) {
      highlightedSuggestionIndex = (highlightedSuggestionIndex + 1) % items.length;
      items.forEach((it, idx) => it.classList.toggle('highlighted', idx === highlightedSuggestionIndex));
      items[highlightedSuggestionIndex].scrollIntoView({ block: 'nearest' });
    }
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    if (items.length > 0) {
      highlightedSuggestionIndex = (highlightedSuggestionIndex - 1 + items.length) % items.length;
      items.forEach((it, idx) => it.classList.toggle('highlighted', idx === highlightedSuggestionIndex));
      items[highlightedSuggestionIndex].scrollIntoView({ block: 'nearest' });
    }
  } else if (event.key === 'Enter') {
    event.preventDefault();
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = null;
    }
    const query = event.target.value.trim();
    if (highlightedSuggestionIndex >= 0 && currentSuggestions[highlightedSuggestionIndex]) {
      selectPlaceSuggestion(currentSuggestions[highlightedSuggestionIndex]);
    } else if (currentSuggestions.length > 0) {
      selectPlaceSuggestion(currentSuggestions[0]);
    } else if (query.length >= 2) {
      executePlaceSearch(query);
    }
  }
}

function renderPlaceSuggestions(places) {
  const list = document.getElementById('place-suggestions-list');
  if (!list) return;

  if (!places || places.length === 0) {
    list.innerHTML = '<div style="padding: 14px; text-align: center; color: #86868B; font-size: 13px;">Nenhum local encontrado. Tente incluir cidade ou número da rua.</div>';
    list.style.display = 'flex';
    return;
  }

  list.innerHTML = '';
  places.forEach((p, index) => {
    const item = document.createElement('div');
    item.className = 'place-suggestion-item';

    let icon = '📍';
    let badgeText = 'Local';
    const t = (p.type || '').toLowerCase();
    if (t.includes('supermarket') || t.includes('retail') || t.includes('shop') || t.includes('mall')) {
      icon = '🛒';
      badgeText = 'Comércio';
    } else if (t.includes('warehouse') || t.includes('industrial') || t.includes('logistics') || t.includes('depot')) {
      icon = '🚚';
      badgeText = 'Logística';
    } else if (t.includes('fuel') || t.includes('gas')) {
      icon = '⛽';
      badgeText = 'Posto';
    } else if (t.includes('restaurant') || t.includes('cafe') || t.includes('food')) {
      icon = '🍽️';
      badgeText = 'Refeição';
    } else if (t.includes('city') || t.includes('town')) {
      icon = '🏙️';
      badgeText = 'Cidade';
    }

    let quickActionHtml = '';
    if (addressModalMode === 'set_start') {
      quickActionHtml = `<button class="btn-suggestion-action" onclick="event.stopPropagation(); directSetPlaceAsStart(${index})">🏠 Partida</button>`;
    } else if (addressModalMode === 'add_stop') {
      quickActionHtml = `<button class="btn-suggestion-action btn-action-green" onclick="event.stopPropagation(); directAddPlaceAsStop(${index})">➕ Adicionar</button>`;
    } else {
      quickActionHtml = `
        <button class="btn-suggestion-action btn-action-green" onclick="event.stopPropagation(); directAddPlaceAsStop(${index})" title="Adicionar como parada de entrega">➕ Parada</button>
        <button class="btn-suggestion-action" onclick="event.stopPropagation(); directSetPlaceAsStart(${index})" title="Definir como ponto de partida (origem)">🏠 Partida</button>
      `;
    }

    item.innerHTML = `
      <span class="place-suggestion-icon">${icon}</span>
      <div class="place-suggestion-content">
        <div class="place-suggestion-title">
          <span>${p.name}</span>
          <span class="place-badge">${badgeText}</span>
        </div>
        <div class="place-suggestion-sub">${p.address}</div>
      </div>
      <div class="place-suggestion-quick-actions">
        ${quickActionHtml}
      </div>
    `;

    item.onclick = () => selectPlaceSuggestion(p, icon);
    list.appendChild(item);
  });

  list.style.display = 'flex';
}

function directAddPlaceAsStop(index) {
  if (currentSuggestions && currentSuggestions[index]) {
    selectedPlaceSuggestion = currentSuggestions[index];
    confirmAddSelectedStop();
  }
}

function directSetPlaceAsStart(index) {
  if (currentSuggestions && currentSuggestions[index]) {
    selectedPlaceSuggestion = currentSuggestions[index];
    confirmSetSelectedStart();
  }
}

function selectPlaceSuggestion(place, icon = '📍') {
  selectedPlaceSuggestion = place;
  window.voiceCopilot.vibrate(25);

  const list = document.getElementById('place-suggestions-list');
  if (list) list.style.display = 'none';

  const previewCard = document.getElementById('selected-place-card');
  if (previewCard) {
    document.getElementById('preview-place-icon').textContent = icon;
    document.getElementById('preview-place-name').textContent = place.name;
    document.getElementById('preview-place-address').textContent = place.address;

    const actionsContainer = previewCard.querySelector('.selected-place-actions');
    if (actionsContainer) {
      if (addressModalMode === 'set_start') {
        actionsContainer.innerHTML = `
          <button class="btn-capsule-small btn-green" onclick="confirmSetSelectedStart()">
            🏠 Definir como Ponto de Partida
          </button>
          <button class="btn-capsule-small btn-secondary" onclick="confirmAddSelectedStop()">
            ➕ Adicionar ao Itinerário
          </button>
        `;
      } else if (addressModalMode === 'add_stop') {
        actionsContainer.innerHTML = `
          <button class="btn-capsule-small btn-green" onclick="confirmAddSelectedStop()">
            ➕ Adicionar ao Itinerário
          </button>
          <button class="btn-capsule-small btn-secondary" onclick="confirmSetSelectedStart()">
            🏠 Definir como Ponto de Partida
          </button>
        `;
      } else {
        actionsContainer.innerHTML = `
          <button class="btn-capsule-small btn-green" onclick="confirmAddSelectedStop()">
            ➕ Adicionar ao Itinerário
          </button>
          <button class="btn-capsule-small btn-secondary" onclick="confirmSetSelectedStart()">
            🏠 Definir como Ponto de Partida
          </button>
          <button class="btn-capsule-small btn-secondary" onclick="confirmStartNewRouteHere()">
            🚀 Iniciar Nova Rota a Partir Deste Local
          </button>
        `;
      }
    }

    previewCard.style.display = 'flex';
  }
}

async function confirmAddSelectedStop() {
  if (!selectedPlaceSuggestion) return;
  window.voiceCopilot.vibrate(40);

  const newStop = {
    destination_id: selectedPlaceSuggestion.name,
    name: selectedPlaceSuggestion.name,
    address: selectedPlaceSuggestion.address,
    latitude: selectedPlaceSuggestion.latitude,
    longitude: selectedPlaceSuggestion.longitude,
    service_time_minutes: 30
  };

  // Se o ponto de partida ainda não foi explicitamente fixado e o itinerário estava vazio:
  if (!window.hasExplicitStartPoint && (!currentDestinations || currentDestinations.length === 0)) {
    // Definir partida próxima na mesma cidade/região (e NÃO em Osasco/SP!)
    window.currentDriverLat = selectedPlaceSuggestion.latitude + 0.015;
    window.currentDriverLon = selectedPlaceSuggestion.longitude + 0.015;
    window.currentDriverStartName = `Garagem / Base (${selectedPlaceSuggestion.city || selectedPlaceSuggestion.name})`;
    window.currentDriverAddress = `Ponto de Partida em ${selectedPlaceSuggestion.city || selectedPlaceSuggestion.address}`;
    updateDrawerStartDisplay();
  }

  if (!currentDestinations) currentDestinations = [];
  currentDestinations.push(newStop);

  closeManualAddressModal();
  await calculateAndApplyRoute(currentDestinations, true);
  showToast(`✅ "${newStop.name}" adicionada ao itinerário!`);
}

async function confirmSetSelectedStart() {
  if (!selectedPlaceSuggestion) return;
  window.voiceCopilot.vibrate(40);

  window.currentDriverLat = selectedPlaceSuggestion.latitude;
  window.currentDriverLon = selectedPlaceSuggestion.longitude;
  window.currentDriverAddress = selectedPlaceSuggestion.address;
  window.currentDriverStartName = selectedPlaceSuggestion.name;
  window.hasExplicitStartPoint = true;

  updateDrawerStartDisplay();

  if (window.mapEngine && window.mapEngine.map) {
    window.mapEngine.map.setView([selectedPlaceSuggestion.latitude, selectedPlaceSuggestion.longitude], 13);
  }

  closeManualAddressModal();

  if (currentDestinations.length > 0) {
    await calculateAndApplyRoute(currentDestinations, true);
    showToast(`🏠 Ponto de partida alterado para "${selectedPlaceSuggestion.name}"!`);
  } else {
    showToast(`🏠 Ponto de partida definido: ${selectedPlaceSuggestion.name}`);
  }
}

async function confirmStartNewRouteHere() {
  if (!selectedPlaceSuggestion) return;
  window.voiceCopilot.vibrate(40);

  window.currentDriverLat = selectedPlaceSuggestion.latitude;
  window.currentDriverLon = selectedPlaceSuggestion.longitude;
  window.currentDriverAddress = selectedPlaceSuggestion.address;
  window.currentDriverStartName = selectedPlaceSuggestion.name;
  window.hasExplicitStartPoint = true;
  currentDestinations = [];

  updateDrawerStartDisplay();
  if (window.mapEngine && window.mapEngine.map) {
    window.mapEngine.map.setView([selectedPlaceSuggestion.latitude, selectedPlaceSuggestion.longitude], 13);
  }
  showIdleCockpitState();
  closeManualAddressModal();
  showToast(`🏠 Ponto de partida definido: "${selectedPlaceSuggestion.name}". Adicione paradas de entrega!`);
}

function updateDrawerStartDisplay() {
  const nameEl = document.getElementById('drawer-start-name');
  const addrEl = document.getElementById('drawer-start-address');
  if (nameEl) nameEl.textContent = window.currentDriverStartName || "Garagem / Ponto de Partida";
  if (addrEl) addrEl.textContent = window.currentDriverAddress || "Defina onde a rota começa";
}

function useCurrentGpsAsStart() {
  window.voiceCopilot.vibrate(30);
  if (!navigator.geolocation) {
    showToast('⚠️ Geolocalização não suportada no navegador.');
    return;
  }
  showToast('📡 Obtendo coordenadas GPS...');
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      window.currentDriverLat = pos.coords.latitude;
      window.currentDriverLon = pos.coords.longitude;
      window.currentDriverStartName = "Meu GPS Atual";
      window.currentDriverAddress = `Localização GPS (${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)})`;
      window.hasExplicitStartPoint = true;
      updateDrawerStartDisplay();
      if (window.mapEngine && window.mapEngine.map) {
        window.mapEngine.map.setView([pos.coords.latitude, pos.coords.longitude], 13);
      }
      if (currentDestinations.length > 0) {
        await calculateAndApplyRoute(currentDestinations, true);
      }
      showToast('📡 Ponto de partida definido pelo GPS!');
    },
    (err) => {
      console.warn('Erro GPS:', err);
      showToast('⚠️ Permissão de GPS negada pelo navegador.');
    },
    { timeout: 8000 }
  );
}

async function submitManualAddresses() {
  const text = document.getElementById('manual-addresses-textarea').value.trim();
  if (!text) {
    showToast('⚠️ Digite ao menos um endereço ou estabelecimento.');
    return;
  }

  const loadingEl = document.getElementById('manual-loading-indicator');
  if (loadingEl) loadingEl.style.display = 'block';

  try {
    const payload = { addresses_text: text };
    if (window.hasExplicitStartPoint && window.currentDriverLat) {
      payload.base_latitude = window.currentDriverLat;
      payload.base_longitude = window.currentDriverLon;
    }

    const res = await fetch('/api/v1/routes/multi-addresses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (loadingEl) loadingEl.style.display = 'none';

    if (!res.ok) {
      showToast('❌ Erro ao reconhecer endereços informados.');
      return;
    }

    const waypoints = await res.json();
    if (!waypoints || waypoints.length === 0) {
      showToast('⚠️ Nenhum endereço reconhecido.');
      return;
    }

    closeManualAddressModal();

    // Se aberto para definir ponto de partida:
    if (addressModalMode === 'set_start') {
      const p = waypoints[0];
      window.currentDriverLat = p.latitude;
      window.currentDriverLon = p.longitude;
      window.currentDriverAddress = p.address;
      window.currentDriverStartName = p.name;
      window.hasExplicitStartPoint = true;
      updateDrawerStartDisplay();
      if (currentDestinations.length > 0) {
        await calculateAndApplyRoute(currentDestinations, true);
      }
      showToast(`🏠 Ponto de partida definido: ${p.name}`);
      return;
    }

    // Se o usuário ainda não fixou ponto de partida (GPS desativado):
    if (!window.hasExplicitStartPoint) {
      if (waypoints.length >= 2) {
        // Primeiro item da lista digitada é a Garagem/Origem da rota
        const startPoint = waypoints[0];
        window.currentDriverLat = startPoint.latitude;
        window.currentDriverLon = startPoint.longitude;
        window.currentDriverAddress = startPoint.address;
        window.currentDriverStartName = startPoint.name;
        window.hasExplicitStartPoint = true;
        updateDrawerStartDisplay();
        const deliveryStops = waypoints.slice(1);
        await calculateAndApplyRoute(deliveryStops, false);
        showToast(`🚀 Rota traçada partindo de "${startPoint.name}" com ${deliveryStops.length} parada(s)!`);
        return;
      } else if (waypoints.length === 1) {
        // Apenas 1 endereço: definir base na mesma cidade e traçar a rota
        const onlyStop = waypoints[0];
        window.currentDriverLat = onlyStop.latitude + 0.015;
        window.currentDriverLon = onlyStop.longitude + 0.015;
        window.currentDriverStartName = `Garagem / Base (${onlyStop.name})`;
        window.currentDriverAddress = `Ponto de Partida na região de ${onlyStop.name}`;
        updateDrawerStartDisplay();
        await calculateAndApplyRoute(waypoints, false);
        showToast(`🚀 Rota traçada para ${onlyStop.name}!`);
        return;
      }
    }

    if (addressModalMode === 'add_stop' && currentDestinations.length > 0) {
      currentDestinations.push(...waypoints);
      await calculateAndApplyRoute(currentDestinations, true);
    } else {
      await calculateAndApplyRoute(waypoints, false);
    }
  } catch (err) {
    if (loadingEl) loadingEl.style.display = 'none';
    console.error('Erro ao enviar endereços manuais:', err);
    showToast('⚠️ Erro de conexão ao reconhecer endereços.');
  }
}

/* -------------------------------------------------------------
 * 3. OTIMIZAÇÃO E APLICAÇÃO DA ROTA SEGUINDO A MALHA VIÁRIA REAL
 * ------------------------------------------------------------- */
async function calculateAndApplyRoute(destinations, preserveOrder = false) {
  if (!destinations || destinations.length === 0) {
    showIdleCockpitState();
    return;
  }

  showToast('🚚 Calculando melhor rota pelas ruas...');

  currentDestinations = destinations.map(d => ({
    destination_id: d.destination_id || d.name,
    name: d.name,
    address: d.address,
    latitude: d.latitude,
    longitude: d.longitude,
    service_time_minutes: d.service_time_minutes || 30
  }));

  const requestPayload = {
    driver_id: "motorista-principal",
    truck_profile: {
      driver_id: "motorista-principal",
      plate: "GLV-2026",
      vehicle_type: "TRUCK",
      height_meters: 4.10,
      width_meters: 2.60,
      length_meters: 18.60,
      gross_weight_tonnes: 45.0,
      axle_count: 6
    },
    start_latitude: window.currentDriverLat,
    start_longitude: window.currentDriverLon,
    start_address: window.currentDriverAddress,
    departure_time: "07:30",
    destinations: currentDestinations,
    enable_meal_breaks: true,
    preserve_order: preserveOrder
  };

  try {
    const res = await fetch('/api/v1/routes/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestPayload)
    });

    if (res.ok) {
      currentRouteData = await res.json();
      localStorage.setItem('galvao_custom_route', JSON.stringify(currentRouteData));
      window.offlineStore.cacheRoute(currentRouteData);
      renderCockpitData(currentRouteData);
      showToast(`✅ Rota calculada com ${currentDestinations.length} entrega(s) pelas ruas!`);
      window.voiceCopilot.speak(`Rota traçada pelas ruas com ${currentDestinations.length} entregas.`);
    } else {
      showToast('❌ Erro ao otimizar rota.');
    }
  } catch (err) {
    console.error('Erro ao calcular rota:', err);
    showToast('⚠️ Falha de comunicação com o servidor de roteirização.');
  }
}

async function loadSampleDemo() {
  const welcomeCard = document.getElementById('cockpit-welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'none';
  await loadRouteWithConfig(REGIONS.SP);
  showToast('📍 Demonstração de exemplo carregada.');
}

async function loadRouteWithConfig(config) {
  currentRegionConfig = config;
  window.currentDriverLat = config.start_latitude;
  window.currentDriverLon = config.start_longitude;
  window.currentDriverAddress = config.start_address;

  const requestPayload = {
    driver_id: "motorista-principal",
    truck_profile: {
      driver_id: "motorista-principal",
      plate: "GLV-2026",
      vehicle_type: "TRUCK",
      height_meters: 4.10,
      width_meters: 2.60,
      length_meters: 18.60,
      gross_weight_tonnes: 45.0,
      axle_count: 6
    },
    start_latitude: config.start_latitude,
    start_longitude: config.start_longitude,
    start_address: config.start_address,
    departure_time: config.departure_time,
    destinations: config.destinations,
    enable_meal_breaks: true
  };

  try {
    const res = await fetch('/api/v1/routes/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestPayload)
    });

    if (res.ok) {
      currentRouteData = await res.json();
      localStorage.setItem('galvao_custom_route', JSON.stringify(currentRouteData));
      window.offlineStore.cacheRoute(currentRouteData);
      renderCockpitData(currentRouteData);
    } else {
      useCachedFallback();
    }
  } catch (err) {
    console.warn('Backend inacessível, utilizando cache de rota offline:', err);
    useCachedFallback();
  }
}

function useCachedFallback() {
  const cached = window.offlineStore.getCachedRoute();
  if (cached) {
    currentRouteData = cached;
    renderCockpitData(cached);
  }
}

function renderCockpitData(route) {
  // Esconder card de boas-vindas
  const welcomeCard = document.getElementById('cockpit-welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'none';

  // Renderizar mapa com geometria real da malha viária (ruas e estradas)
  window.mapEngine.renderRoute(route.itinerary, route.road_geometry);

  // Próxima parada (ignora nó 0 de saída)
  const nextStop = route.itinerary.find(s => s.stop_type === 'DELIVERY' || s.stop_type === 'MEAL_BREAK') || route.itinerary[1];
  if (nextStop) {
    const nextStopLabel = nextStop.stop_type === 'MEAL_BREAK' ? `🍽️ ${nextStop.name}` : `${nextStop.step_number}. ${nextStop.name}`;
    document.getElementById('hud-next-stop').textContent = nextStopLabel;
    document.getElementById('hud-next-address').textContent = nextStop.slow_dock_warning 
      ? `⚠️ ${nextStop.slow_dock_warning}`
      : nextStop.address;
    document.getElementById('hud-eta').textContent = nextStop.arrival_time;
  }

  // Métricas inferiores (apenas paradas reais de entrega, sem contar alimentação)
  document.getElementById('metric-stops').textContent = route.total_stops;
  document.getElementById('metric-distance').textContent = `${route.total_distance_km} km`;
  document.getElementById('metric-finish').textContent = route.estimated_end_time;

  // Botão Iniciar Navegação pronto para o motorista
  const btnStart = document.getElementById('btn-start-navigation');
  if (btnStart) {
    btnStart.style.display = 'inline-flex';
    btnStart.classList.remove('navigating');
    btnStart.innerHTML = '<span>▶ Iniciar Navegação</span>';
  }

  // Atualizar gaveta
  renderItineraryDrawer(route.itinerary);
}

function renderItineraryDrawer(stops) {
  const list = document.getElementById('drawer-stops-list');
  if (!list) return;
  list.innerHTML = '';

  updateDrawerStartDisplay();

  const deliveryStops = (stops || []).filter(s => s.stop_type === 'DELIVERY');
  const countEl = document.getElementById('drawer-itinerary-stats');
  if (countEl) {
    countEl.textContent = `${deliveryStops.length} parada(s) planejada(s)`;
  }

  if (!stops || stops.length <= 1) {
    list.innerHTML = '<div style="padding: 24px; text-align: center; color: #86868B; font-size: 14px;">Nenhuma parada de entrega no itinerário.<br>Toque em ➕ Adicionar Nova Parada para incluir destinos.</div>';
    return;
  }

  // Sincronizar currentDestinations com as paradas de entrega da rota
  currentDestinations = deliveryStops.map(s => ({
    destination_id: s.destination_id || s.name,
    name: s.name,
    address: s.address,
    latitude: s.latitude,
    longitude: s.longitude,
    service_time_minutes: s.service_duration_minutes || 30
  }));

  let deliveryIndexCounter = 0;

  stops.forEach(s => {
    // Ponto de início é renderizado no cartão superior
    if (s.stop_type === 'START') {
      window.currentDriverStartName = s.name;
      window.currentDriverAddress = s.address;
      updateDrawerStartDisplay();
      return;
    }

    const div = document.createElement('div');
    const isSlow = s.is_slow_dock;
    const isMeal = s.stop_type === 'MEAL_BREAK';
    div.className = `itinerary-item ${isSlow ? 'slow-dock' : ''} ${isMeal ? 'meal-break' : ''}`;

    if (isMeal) {
      div.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700; font-size:15px; color:#30D158;">🍽️ ${s.name}</span>
          <span style="font-weight:700; font-size:14px; color:#30D158;">${s.arrival_time}</span>
        </div>
        <span style="font-size:12px; color:#86868B; margin-top:2px;">${s.address}</span>
        <div style="font-size:11px; color:#30D158; margin-top:4px;">${s.notes || 'Pausa de refeição programada com pátio seguro'}</div>
      `;
      list.appendChild(div);
      return;
    }

    // Parada de entrega com índice e botões de ação
    const thisIndex = deliveryIndexCounter;
    deliveryIndexCounter++;

    const isFirst = thisIndex === 0;
    const isLast = thisIndex === deliveryStops.length - 1;

    div.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:700; font-size:15px; color:#F5F5F7;">
          <span style="color:#2997FF; margin-right:4px;">#${thisIndex + 1}</span> ${s.name}
        </span>
        <span style="font-weight:700; font-size:14px; color:#30D158;">${s.arrival_time}</span>
      </div>
      <span style="font-size:12px; color:#86868B; margin-top:2px;">${s.address}</span>
      <div style="display:flex; justify-content:space-between; font-size:11px; color:#6E6E73; margin-top:4px;">
        <span>${isSlow ? '⏱️ Doca Lenta Reordenada' : '📦 Entrega Programada'}</span>
        <span>${s.service_duration_minutes > 0 ? `${s.service_duration_minutes} min parada` : ''}</span>
      </div>
      ${s.slow_dock_warning ? `<div style="font-size:11px; color:#FF9F0A; margin-top:2px;">${s.slow_dock_warning}</div>` : ''}
      ${s.notes ? `<div style="font-size:11px; color:#30D158; margin-top:2px;">${s.notes}</div>` : ''}

      <!-- Barra de Ferramentas: Reordenar (Subir/Descer), Editar e Excluir -->
      <div class="itinerary-stop-toolbar">
        <span style="font-size: 11px; color: #86868B;">Ordem / Ações:</span>
        <div class="itinerary-stop-actions">
          <button class="btn-stop-tool" title="Mover parada para cima" onclick="moveStopUp(${thisIndex})" ${isFirst ? 'disabled' : ''}>⬆️</button>
          <button class="btn-stop-tool" title="Mover parada para baixo" onclick="moveStopDown(${thisIndex})" ${isLast ? 'disabled' : ''}>⬇️</button>
          <button class="btn-stop-tool" title="Editar informações da parada" onclick="openEditStopModal(${thisIndex})">✏️</button>
          <button class="btn-stop-tool btn-tool-delete" title="Excluir parada do itinerário" onclick="removeStopFromItinerary(${thisIndex})">🗑️</button>
        </div>
      </div>
    `;
    list.appendChild(div);
  });
}

function moveStopUp(index) {
  if (index <= 0 || index >= currentDestinations.length) return;
  window.voiceCopilot.vibrate(30);
  const temp = currentDestinations[index];
  currentDestinations[index] = currentDestinations[index - 1];
  currentDestinations[index - 1] = temp;
  calculateAndApplyRoute(currentDestinations, true);
  showToast(`⬆️ Parada ${index + 1} movida para cima.`);
}

function moveStopDown(index) {
  if (index < 0 || index >= currentDestinations.length - 1) return;
  window.voiceCopilot.vibrate(30);
  const temp = currentDestinations[index];
  currentDestinations[index] = currentDestinations[index + 1];
  currentDestinations[index + 1] = temp;
  calculateAndApplyRoute(currentDestinations, true);
  showToast(`⬇️ Parada ${index + 1} movida para baixo.`);
}

function removeStopFromItinerary(index) {
  if (index < 0 || index >= currentDestinations.length) return;
  window.voiceCopilot.vibrate(50);
  const removed = currentDestinations[index];
  currentDestinations.splice(index, 1);

  if (currentDestinations.length === 0) {
    clearActiveRoute();
  } else {
    calculateAndApplyRoute(currentDestinations, true);
    showToast(`🗑️ "${removed.name}" removida do itinerário.`);
  }
}

let editingStopSelectedPlace = null;
let editStopDebounceTimer = null;

function openEditStopModal(index) {
  if (index < 0 || index >= currentDestinations.length) return;
  editingStopIndex = index;
  editingStopSelectedPlace = null;
  const stop = currentDestinations[index];

  document.getElementById('edit-stop-name-input').value = stop.name || '';
  document.getElementById('edit-stop-address-input').value = stop.address || '';
  document.getElementById('edit-stop-duration-input').value = stop.service_time_minutes || 30;

  const suggList = document.getElementById('edit-stop-suggestions');
  if (suggList) {
    suggList.innerHTML = '';
    suggList.style.display = 'none';
  }

  document.getElementById('edit-stop-modal').style.display = 'flex';
}

function closeEditStopModal() {
  editingStopIndex = -1;
  editingStopSelectedPlace = null;
  document.getElementById('edit-stop-modal').style.display = 'none';
}

function handleEditStopAddressInput(event) {
  const query = event.target.value.trim();
  const suggList = document.getElementById('edit-stop-suggestions');
  if (editStopDebounceTimer) clearTimeout(editStopDebounceTimer);

  if (!query || query.length < 2) {
    if (suggList) {
      suggList.innerHTML = '';
      suggList.style.display = 'none';
    }
    return;
  }

  editStopDebounceTimer = setTimeout(async () => {
    try {
      let url = `/api/v1/routes/search-places?q=${encodeURIComponent(query)}&limit=4`;
      if (window.hasExplicitStartPoint && window.currentDriverLat) {
        url += `&base_lat=${window.currentDriverLat}&base_lon=${window.currentDriverLon}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const places = await res.json();
        renderEditStopSuggestions(places);
      }
    } catch (e) {
      console.warn('Erro ao buscar sugestões na edição:', e);
    }
  }, 250);
}

function renderEditStopSuggestions(places) {
  const suggList = document.getElementById('edit-stop-suggestions');
  if (!suggList) return;
  if (!places || places.length === 0) {
    suggList.innerHTML = '';
    suggList.style.display = 'none';
    return;
  }

  suggList.innerHTML = '';
  places.forEach((p) => {
    const item = document.createElement('div');
    item.className = 'place-suggestion-item';
    item.innerHTML = `
      <span class="place-suggestion-icon">📍</span>
      <div class="place-suggestion-content">
        <div class="place-suggestion-title"><span>${p.name}</span></div>
        <div class="place-suggestion-sub">${p.address}</div>
      </div>
    `;
    item.onclick = () => {
      editingStopSelectedPlace = p;
      document.getElementById('edit-stop-name-input').value = p.name;
      document.getElementById('edit-stop-address-input').value = p.address;
      suggList.style.display = 'none';
    };
    suggList.appendChild(item);
  });
  suggList.style.display = 'flex';
}

async function saveEditedStop() {
  if (editingStopIndex < 0 || editingStopIndex >= currentDestinations.length) return;
  window.voiceCopilot.vibrate(30);

  const oldAddr = currentDestinations[editingStopIndex].address;
  const newName = document.getElementById('edit-stop-name-input').value.trim();
  const newAddr = document.getElementById('edit-stop-address-input').value.trim();
  const newDuration = parseInt(document.getElementById('edit-stop-duration-input').value, 10) || 30;

  if (newName) currentDestinations[editingStopIndex].name = newName;
  currentDestinations[editingStopIndex].service_time_minutes = newDuration;

  if (editingStopSelectedPlace) {
    currentDestinations[editingStopIndex].name = newName || editingStopSelectedPlace.name;
    currentDestinations[editingStopIndex].address = editingStopSelectedPlace.address;
    currentDestinations[editingStopIndex].latitude = editingStopSelectedPlace.latitude;
    currentDestinations[editingStopIndex].longitude = editingStopSelectedPlace.longitude;
  } else if (newAddr && newAddr !== oldAddr) {
    currentDestinations[editingStopIndex].address = newAddr;
    try {
      showToast('🔍 Localizando novo endereço...');
      let url = `/api/v1/routes/search-places?q=${encodeURIComponent(newAddr)}&limit=1`;
      if (window.hasExplicitStartPoint && window.currentDriverLat) {
        url += `&base_lat=${window.currentDriverLat}&base_lon=${window.currentDriverLon}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const places = await res.json();
        if (places && places.length > 0) {
          currentDestinations[editingStopIndex].latitude = places[0].latitude;
          currentDestinations[editingStopIndex].longitude = places[0].longitude;
          currentDestinations[editingStopIndex].address = places[0].address;
          if (!newName) {
            currentDestinations[editingStopIndex].name = places[0].name;
          }
        }
      }
    } catch (e) {
      console.warn('Erro ao geocodificar novo endereço da parada:', e);
    }
  }

  closeEditStopModal();
  await calculateAndApplyRoute(currentDestinations, true);
  showToast('✅ Parada atualizada com sucesso.');
}

async function recalculateCurrentRoute(preserveOrder = true) {
  if (!currentDestinations || currentDestinations.length === 0) {
    showToast('⚠️ Nenhuma parada no itinerário para recalcular.');
    return;
  }
  await calculateAndApplyRoute(currentDestinations, preserveOrder);
}

function updateNetworkStatus(online, pendingCount) {
  const dot = document.getElementById('network-dot');
  const label = document.getElementById('network-label');
  
  if (online) {
    dot.className = 'indicator-dot';
    label.textContent = `4G Conectado (Outbox: ${pendingCount})`;
  } else {
    dot.className = 'indicator-dot offline';
    label.textContent = `Modo Offline (Outbox: ${pendingCount})`;
  }
}

function toggleNetworkSimulation() {
  const currentOnline = window.offlineStore.isOnline;
  window.offlineStore.handleConnectivityChange(!currentOnline);
  window.voiceCopilot.vibrate(30);
}

// Controle de Voz: Mutar e Desmutar
function updateMuteButtonUI(isMuted) {
  const btn = document.getElementById('btn-voice-mute');
  if (!btn) return;
  if (isMuted) {
    btn.innerHTML = '🔇';
    btn.classList.add('muted');
    btn.title = 'Voz do Guia: Silenciada (Clique para Ativar)';
  } else {
    btn.innerHTML = '🔊';
    btn.classList.remove('muted');
    btn.title = 'Voz do Guia: Ativada (Clique para Silenciar)';
  }
}

function toggleVoiceMute() {
  window.voiceCopilot.vibrate(30);
  const isMuted = window.voiceCopilot.toggleMute();
  updateMuteButtonUI(isMuted);
  if (isMuted) {
    showToast('🔇 Voz do Guia: Silenciada');
  } else {
    showToast('🔊 Voz do Guia: Ativada');
    window.voiceCopilot.speak('Voz do guia ativada.');
  }
}

function showToast(message, duration = 3000) {
  const toast = document.getElementById('cockpit-toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

// Modal de Seleção de Região e GPS
function openRegionModal() {
  window.voiceCopilot.vibrate(30);
  document.getElementById('region-modal').style.display = 'flex';
}

function closeRegionModal() {
  window.voiceCopilot.vibrate(20);
  document.getElementById('region-modal').style.display = 'none';
}

async function selectRegion(regionCode) {
  closeRegionModal();
  window.voiceCopilot.vibrate(50);

  if (regionCode === 'GPS') {
    showToast('📡 Acessando sensor de GPS do seu dispositivo...');
    if (!navigator.geolocation) {
      showToast('❌ GPS não suportado neste navegador.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        showToast('📍 GPS Localizado! Gerando rota na sua região...');
        localStorage.setItem('galvao_selected_region', 'GPS');
        localStorage.setItem('galvao_gps_lat', lat);
        localStorage.setItem('galvao_gps_lon', lon);
        const gpsConfig = buildGpsRoutePayload(lat, lon);
        await loadRouteWithConfig(gpsConfig);
        window.voiceCopilot.speak('Rota calculada na sua localização atual.');
      },
      (err) => {
        console.warn('Erro ao obter GPS:', err);
        showToast('⚠️ Permissão de GPS negada pelo navegador.');
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  } else if (REGIONS[regionCode]) {
    const reg = REGIONS[regionCode];
    localStorage.setItem('galvao_selected_region', regionCode);
    showToast(`📍 Carregando rota para: ${reg.name}`);
    await loadRouteWithConfig(reg);
    window.voiceCopilot.speak(`Rota carregada para ${reg.name}.`);
  }
}

function triggerSimulatedReroute() {
  window.voiceCopilot.vibrate(60);
  simulatedAlternativeActive = true;
  document.getElementById('reroute-banner').style.display = 'flex';
  document.getElementById('banner-saved-time').textContent = '⚡ -8 MIN';

  // Mostrar polyline verde alternativo dinâmico baseado na rota atual
  if (currentRouteData && currentRouteData.itinerary && currentRouteData.itinerary.length >= 2) {
    const p1 = currentRouteData.itinerary[0];
    const p2 = currentRouteData.itinerary[1];
    const midLat = (p1.latitude + p2.latitude) / 2 + 0.008;
    const midLon = (p1.longitude + p2.longitude) / 2 + 0.008;
    const coords = [
      [p1.latitude, p1.longitude],
      [midLat, midLon],
      [p2.latitude, p2.longitude]
    ];
    window.mapEngine.showAlternativeFastRoute(coords);
  }

  // Copiloto fala aviso de voz curto
  window.voiceCopilot.speak("Nova rota economiza 8 minutos. Toque em Aceitar ou vire à direita.");

  // Regra de Usabilidade 5.3: Auto-aceite por movimento após 12 segundos se motorista virar
  if (autoAcceptTimer) clearTimeout(autoAcceptTimer);
  autoAcceptTimer = setTimeout(() => {
    if (simulatedAlternativeActive) {
      console.log('[Auto-Aceite] Conversão detectada pelo GPS. Adotando rota automaticamente sem distração.');
      acceptReroute(true);
    }
  }, 12000);
}

function acceptReroute(isAuto = false) {
  window.voiceCopilot.vibrate(80);
  simulatedAlternativeActive = false;
  if (autoAcceptTimer) clearTimeout(autoAcceptTimer);
  document.getElementById('reroute-banner').style.display = 'none';

  window.mapEngine.clearAlternativeRoute();
  
  if (isAuto) {
    window.voiceCopilot.speak("Desvio adotado.");
  } else {
    window.voiceCopilot.speak("Rota atualizada. Você economizou 8 minutos.");
  }
}

function dismissReroute() {
  window.voiceCopilot.vibrate(30);
  simulatedAlternativeActive = false;
  if (autoAcceptTimer) clearTimeout(autoAcceptTimer);
  document.getElementById('reroute-banner').style.display = 'none';
  window.mapEngine.clearAlternativeRoute();
}

function recenterMap() {
  window.voiceCopilot.vibrate(30);
  window.mapEngine.recenter();
}

function toggleMapTheme() {
  window.voiceCopilot.vibrate(25);
  const isDark = window.mapEngine.toggleTheme();
  const btn = document.getElementById('btn-theme-toggle');
  if (btn) {
    btn.innerHTML = isDark ? '☀️' : '🌙';
    btn.title = isDark ? 'Mudar para Modo Claro' : 'Mudar para Modo Escuro';
  }
}

function toggleDrawer() {
  window.voiceCopilot.vibrate(30);
  const drawer = document.getElementById('itinerary-drawer');
  drawer.classList.toggle('open');
}

/* Modal Rápido de 2 Toques: Recebimento Lento */
function openSlowDockModal() {
  window.voiceCopilot.vibrate(40);
  document.getElementById('slow-modal').style.display = 'flex';
}

function closeSlowDockModal() {
  window.voiceCopilot.vibrate(20);
  document.getElementById('slow-modal').style.display = 'none';
}

function selectDelay(minutes) {
  window.voiceCopilot.vibrate(25);
  selectedDelayMinutes = minutes;
  document.querySelectorAll('.btn-delay-choice').forEach(b => b.classList.remove('selected'));
  event.target.classList.add('selected');
}

function confirmSlowDockReport() {
  // Toque 2: Confirmação física
  window.voiceCopilot.vibrate(70);
  const now = new Date();
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

  const currentDestinationName = currentRouteData?.itinerary[1]?.name || "Mercado Central Doca Sul";

  const payload = {
    destination_id: currentDestinationName,
    driver_id: "motorista-principal",
    time_of_day: timeStr,
    excess_wait_minutes: selectedDelayMinutes,
    driver_notes: "Reportado em 2 toques no cockpit"
  };

  // Enfileirar na Fila Outbox (funciona 100% offline ou online)
  window.offlineStore.enqueueEvent('SLOW_RECEIVING_REPORT', payload);

  closeSlowDockModal();
  window.voiceCopilot.speak(`Lentidão de ${selectedDelayMinutes} minutos registrada. Obrigado.`);
}

/* =============================================================
 * SISTEMA DE NAVEGAÇÃO EM TEMPO REAL COM ACOMPANHAMENTO AO VIVO
 * ============================================================= */

let navigationState = {
  isNavigating: false,
  isPaused: false,
  simSpeed: 1, // 1x, 2x, 5x, 10x
  currentIndex: 0,
  segmentOffsetMeters: 0,
  totalDistanceMeters: 0,
  coveredDistanceMeters: 0,
  routeCoordinates: [],
  stops: [],
  watchId: null,
  animationTimer: null,
  followCamera: true,
  announcedStops: new Set()
};

function haversineMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const p1 = lat1 * Math.PI / 180;
  const p2 = lat2 * Math.PI / 180;
  const dp = (lat2 - lat1) * Math.PI / 180;
  const dl = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dp / 2) * Math.sin(dp / 2) + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function calculateBearing(lat1, lon1, lat2, lon2) {
  const p1 = lat1 * Math.PI / 180;
  const p2 = lat2 * Math.PI / 180;
  const dl = (lon2 - lon1) * Math.PI / 180;
  const y = Math.sin(dl) * Math.cos(p2);
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
  const brng = Math.atan2(y, x) * 180 / Math.PI;
  return (brng + 360) % 360;
}

function startNavigation() {
  window.voiceCopilot.vibrate(50);
  if (!currentRouteData || !currentRouteData.itinerary || currentRouteData.itinerary.length < 2) {
    showToast('⚠️ Defina ponto de partida e ao menos um destino antes de navegar!');
    return;
  }

  // Obter coordenadas viárias reais da rota atual
  let coords = window.mapEngine ? window.mapEngine.getRouteCoordinates() : [];
  if (!coords || coords.length < 2) {
    coords = currentRouteData.itinerary.map(s => [s.latitude, s.longitude]);
  }

  if (!coords || coords.length < 2) {
    showToast('⚠️ Coordenadas da rota indisponíveis.');
    return;
  }

  // Calcular distância total acumulada em metros
  let totalDist = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    totalDist += haversineMeters(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]);
  }
  if (totalDist === 0) totalDist = (currentRouteData.total_distance_km || 1) * 1000;

  navigationState.isNavigating = true;
  navigationState.isPaused = false;
  navigationState.simSpeed = 1;
  navigationState.currentIndex = 0;
  navigationState.segmentOffsetMeters = 0;
  navigationState.totalDistanceMeters = totalDist;
  navigationState.coveredDistanceMeters = 0;
  navigationState.routeCoordinates = coords;
  navigationState.stops = currentRouteData.itinerary || [];
  navigationState.announcedStops = new Set();
  navigationState.followCamera = true;

  // Atualizar visual do botão e exibir HUD de navegação
  const btnStart = document.getElementById('btn-start-navigation');
  if (btnStart) {
    btnStart.classList.add('navigating');
    btnStart.innerHTML = '<span>⏹️ Em Navegação</span>';
  }

  const hudBar = document.getElementById('navigation-hud-bar');
  if (hudBar) hudBar.style.display = 'flex';

  const dot = document.getElementById('nav-pulse-dot');
  if (dot) dot.classList.remove('paused');

  const firstDestName = navigationState.stops[1] ? navigationState.stops[1].name : "Destino";
  const statusText = document.getElementById('nav-status-text');
  if (statusText) statusText.textContent = `Em Rota: ${firstDestName}`;

  const btnPause = document.getElementById('btn-nav-pause');
  if (btnPause) btnPause.innerHTML = '⏸️ Pausar';

  const btnSpeed = document.getElementById('btn-nav-speed');
  if (btnSpeed) btnSpeed.innerHTML = '⚡ 1x';

  updateNavigationProgressUI();

  // Iniciar posicionamento GPS físico real em segundo plano caso o motorista esteja se deslocando na rua
  if (navigator.geolocation) {
    try {
      navigationState.watchId = navigator.geolocation.watchPosition(
        (pos) => onPhysicalGpsUpdate(pos.coords.latitude, pos.coords.longitude, pos.coords.heading),
        (err) => console.warn('GPS watchPosition info:', err),
        { enableHighAccuracy: true, maximumAge: 1500, timeout: 6000 }
      );
    } catch (e) {
      console.warn('Erro ao inicializar GPS watchPosition:', e);
    }
  }

  // Iniciar laço de animação / simulação suave ao vivo
  if (navigationState.animationTimer) clearInterval(navigationState.animationTimer);
  navigationState.animationTimer = setInterval(stepNavigationSimulation, 120);

  showToast(`🚀 Navegação iniciada em direção a "${firstDestName}"!`);
  window.voiceCopilot.speak(`Iniciando navegação ao vivo. Siga em frente na rota em direção a ${firstDestName}.`);
}

function onPhysicalGpsUpdate(gpsLat, gpsLon, gpsHeading) {
  if (!navigationState.isNavigating || navigationState.isPaused) return;

  const coords = navigationState.routeCoordinates;
  if (!coords || coords.length < 2) return;

  // Encontrar o ponto mais próximo na malha viária da rota
  let minDistance = Infinity;
  let closestIndex = navigationState.currentIndex;

  for (let i = navigationState.currentIndex; i < Math.min(coords.length, navigationState.currentIndex + 40); i++) {
    const d = haversineMeters(gpsLat, gpsLon, coords[i][0], coords[i][1]);
    if (d < minDistance) {
      minDistance = d;
      closestIndex = i;
    }
  }

  // Se o GPS físico está perto da rota (< 100m) e avançou
  if (minDistance < 100 && closestIndex > navigationState.currentIndex) {
    navigationState.currentIndex = closestIndex;
    navigationState.segmentOffsetMeters = 0;
    
    // Recalcular distância percorrida
    let cov = 0;
    for (let j = 0; j < closestIndex; j++) {
      cov += haversineMeters(coords[j][0], coords[j][1], coords[j+1][0], coords[j+1][1]);
    }
    navigationState.coveredDistanceMeters = cov;

    const nextCoord = coords[Math.min(coords.length - 1, closestIndex + 1)];
    const bearing = gpsHeading || calculateBearing(gpsLat, gpsLon, nextCoord[0], nextCoord[1]);
    if (window.mapEngine) {
      window.mapEngine.updateTruckNavigation(gpsLat, gpsLon, bearing, navigationState.followCamera);
    }
    updateNavigationProgressUI();
  }
}

function stepNavigationSimulation() {
  if (!navigationState.isNavigating || navigationState.isPaused) return;

  const coords = navigationState.routeCoordinates;
  if (!coords || coords.length < 2) return;

  if (navigationState.currentIndex >= coords.length - 1) {
    // Chegou ao fim do percurso!
    completeNavigationArrival();
    return;
  }

  // Avanço métrico contínuo e suave baseado em velocidade física realista
  const dt = 0.12; // tick de 120ms
  const baseSpeedMps = 18.0; // ~65 km/h velocidade cruzeiro
  let distanceToMove = baseSpeedMps * dt * navigationState.simSpeed;

  while (distanceToMove > 0 && navigationState.currentIndex < coords.length - 1) {
    const p1 = coords[navigationState.currentIndex];
    const p2 = coords[navigationState.currentIndex + 1];
    const segDist = haversineMeters(p1[0], p1[1], p2[0], p2[1]);

    if (segDist <= 0.5) {
      navigationState.currentIndex++;
      navigationState.segmentOffsetMeters = 0;
      continue;
    }

    const remainingInSeg = segDist - navigationState.segmentOffsetMeters;
    if (distanceToMove >= remainingInSeg) {
      distanceToMove -= remainingInSeg;
      navigationState.coveredDistanceMeters = Math.min(
        navigationState.totalDistanceMeters,
        navigationState.coveredDistanceMeters + remainingInSeg
      );
      navigationState.currentIndex++;
      navigationState.segmentOffsetMeters = 0;
    } else {
      navigationState.segmentOffsetMeters += distanceToMove;
      navigationState.coveredDistanceMeters = Math.min(
        navigationState.totalDistanceMeters,
        navigationState.coveredDistanceMeters + distanceToMove
      );
      distanceToMove = 0;
    }
  }

  if (navigationState.currentIndex >= coords.length - 1) {
    completeNavigationArrival();
    return;
  }

  const p1 = coords[navigationState.currentIndex];
  const p2 = coords[navigationState.currentIndex + 1];
  const segDist = Math.max(0.1, haversineMeters(p1[0], p1[1], p2[0], p2[1]));
  const ratio = Math.min(1.0, Math.max(0.0, navigationState.segmentOffsetMeters / segDist));

  const currentLat = p1[0] + ratio * (p2[0] - p1[0]);
  const currentLon = p1[1] + ratio * (p2[1] - p1[1]);
  const bearing = calculateBearing(p1[0], p1[1], p2[0], p2[1]);

  // Atualizar ícone do caminhão e câmera no mapa
  if (window.mapEngine) {
    window.mapEngine.updateTruckNavigation(currentLat, currentLon, bearing, navigationState.followCamera);
  }

  updateNavigationProgressUI();
  checkStopProximity(currentLat, currentLon);
}

function updateNavigationProgressUI() {
  const totalM = Math.max(1, navigationState.totalDistanceMeters);
  const coveredM = Math.min(totalM, navigationState.coveredDistanceMeters);
  const remainingM = Math.max(0, totalM - coveredM);

  const percent = Math.min(100, Math.round((coveredM / totalM) * 100));

  // Barra de progresso visual Apple Cupertino
  const fill = document.getElementById('nav-progress-fill');
  if (fill) fill.style.width = `${percent}%`;

  const percentEl = document.getElementById('nav-progress-percent');
  if (percentEl) percentEl.textContent = `${percent}% concluído`;

  const distEl = document.getElementById('nav-progress-distance');
  if (distEl) {
    distEl.textContent = `${(coveredM / 1000).toFixed(1)} km de ${(totalM / 1000).toFixed(1)} km`;
  }

  // ETA dinâmico em tempo real
  const speedKmh = 45 * navigationState.simSpeed;
  const remainingHours = (remainingM / 1000) / (speedKmh || 45);
  const remainingMinutes = Math.max(1, Math.round(remainingHours * 60));

  const now = new Date();
  const etaDate = new Date(now.getTime() + remainingMinutes * 60000);
  const etaStr = `${String(etaDate.getHours()).padStart(2, '0')}:${String(etaDate.getMinutes()).padStart(2, '0')}`;

  const etaTimeEl = document.getElementById('nav-eta-time');
  if (etaTimeEl) etaTimeEl.textContent = etaStr;

  const etaRemEl = document.getElementById('nav-eta-remaining');
  if (etaRemEl) etaRemEl.textContent = `(~${remainingMinutes} min)`;
}

function checkStopProximity(currentLat, currentLon) {
  const stops = navigationState.stops;
  if (!stops || stops.length === 0) return;

  stops.forEach((stop, idx) => {
    if (idx === 0) return; // Origem
    if (navigationState.announcedStops.has(idx)) return;

    const d = haversineMeters(currentLat, currentLon, stop.latitude, stop.longitude);
    if (d < 180) { // Menos de 180 metros da parada
      navigationState.announcedStops.add(idx);
      window.voiceCopilot.vibrate(60);
      showToast(`📍 Chegando à parada ${stop.step_number}: ${stop.name}`);
      window.voiceCopilot.speak(`Atenção: aproximando-se do destino número ${stop.step_number}, ${stop.name}.`);
      
      // Atualizar ilha superior
      const nextTitle = document.getElementById('hud-next-stop');
      if (nextTitle) nextTitle.textContent = `${stop.step_number}. ${stop.name} (Próximo)`;
      const nextAddr = document.getElementById('hud-next-address');
      if (nextAddr) nextAddr.textContent = stop.address;
    }
  });
}

function completeNavigationArrival() {
  if (navigationState.animationTimer) {
    clearInterval(navigationState.animationTimer);
    navigationState.animationTimer = null;
  }
  navigationState.isPaused = true;

  const fill = document.getElementById('nav-progress-fill');
  if (fill) fill.style.width = '100%';

  const percentEl = document.getElementById('nav-progress-percent');
  if (percentEl) percentEl.textContent = '100% concluído';

  const statusText = document.getElementById('nav-status-text');
  if (statusText) statusText.textContent = 'Destino Final Alcançado!';

  const dot = document.getElementById('nav-pulse-dot');
  if (dot) dot.classList.add('paused');

  window.voiceCopilot.vibrate([100, 50, 100, 50, 150]);
  showToast('🎉 Destino alcançado com sucesso! Navegação concluída.');
  window.voiceCopilot.speak('Você chegou ao seu destino final. Todas as paradas foram concluídas. Bom trabalho!');
}

function togglePauseNavigation() {
  window.voiceCopilot.vibrate(25);
  if (!navigationState.isNavigating) return;

  navigationState.isPaused = !navigationState.isPaused;
  const btn = document.getElementById('btn-nav-pause');
  const dot = document.getElementById('nav-pulse-dot');
  const statusText = document.getElementById('nav-status-text');

  if (navigationState.isPaused) {
    if (btn) btn.innerHTML = '▶ Retomar';
    if (dot) dot.classList.add('paused');
    if (statusText) statusText.textContent = 'Navegação Pausada';
    showToast('⏸️ Navegação pausada.');
  } else {
    if (btn) btn.innerHTML = '⏸️ Pausar';
    if (dot) dot.classList.remove('paused');
    if (statusText) statusText.textContent = 'Navegação em Tempo Real';
    showToast('▶ Navegação retomada.');
  }
}

function stopNavigation() {
  window.voiceCopilot.vibrate(40);
  if (navigationState.animationTimer) {
    clearInterval(navigationState.animationTimer);
    navigationState.animationTimer = null;
  }
  if (navigationState.watchId && navigator.geolocation) {
    navigator.geolocation.clearWatch(navigationState.watchId);
    navigationState.watchId = null;
  }

  navigationState.isNavigating = false;
  navigationState.isPaused = false;
  navigationState.currentIndex = 0;
  navigationState.segmentOffsetMeters = 0;

  const hudBar = document.getElementById('navigation-hud-bar');
  if (hudBar) hudBar.style.display = 'none';

  const btnStart = document.getElementById('btn-start-navigation');
  if (btnStart) {
    btnStart.classList.remove('navigating');
    btnStart.innerHTML = '<span>▶ Iniciar Navegação</span>';
  }

  // Reposicionar caminhão no ponto de partida inicial
  if (window.mapEngine && navigationState.routeCoordinates.length > 0) {
    const firstPos = navigationState.routeCoordinates[0];
    window.mapEngine.updateTruckNavigation(firstPos[0], firstPos[1], 0, false);
  }

  showToast('⏹️ Navegação encerrada.');
}

function cycleSimulationSpeed() {
  window.voiceCopilot.vibrate(25);
  const speeds = [1, 2, 5, 10];
  const curIdx = speeds.indexOf(navigationState.simSpeed);
  const nextIdx = (curIdx + 1) % speeds.length;
  navigationState.simSpeed = speeds[nextIdx];

  const btn = document.getElementById('btn-nav-speed');
  if (btn) btn.innerHTML = `⚡ ${navigationState.simSpeed}x`;
  showToast(`⚡ Velocidade da simulação ajustada para ${navigationState.simSpeed}x`);
}

function recenterTruckNavigation() {
  window.voiceCopilot.vibrate(25);
  navigationState.followCamera = true;
  if (window.mapEngine && window.mapEngine.truckMarker) {
    window.mapEngine.map.panTo(window.mapEngine.truckMarker.getLatLng(), { animate: true, duration: 0.5 });
  }
  showToast('🎯 Câmera centralizada no caminhão.');
}

