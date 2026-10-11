/**
 * GALVÃO LOGI — MOTOR DE MAPAS VETORIAIS (APPLE ESTÉTICA DARK)
 * Exibe a malha viária cristalina, rota azul de navegação e atalhos verdes.
 */

class MapEngine {
  constructor(containerId = 'map-container') {
    this.containerId = containerId;
    this.map = null;
    this.activePolyline = null;
    this.alternativePolyline = null;
    this.markers = [];
    this.truckMarker = null;

    this.defaultCenter = [-23.5505, -46.6333]; // São Paulo, SP
    this.initMap();
  }

  initMap() {
    this.map = L.map(this.containerId, {
      zoomControl: false,
      attributionControl: false
    }).setView(this.defaultCenter, 12);

    // OpenStreetMap — 100% Gratuito, Sem Chave de API, Cobertura Total e Detalhada
    this.tileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(this.map);

    this.isDarkMode = false;
  }

  toggleTheme() {
    this.isDarkMode = !this.isDarkMode;
    const tilePane = this.map.getPane('tilePane');
    if (tilePane) {
      if (this.isDarkMode) {
        tilePane.style.filter = 'brightness(0.65) invert(1) contrast(1.4) hue-rotate(180deg) saturate(0.5)';
      } else {
        tilePane.style.filter = 'none';
      }
    }
    return this.isDarkMode;
  }

  renderRoute(stops, roadGeometry = null) {
    this.clearLayers();
    if (!stops || stops.length === 0) return;

    const stopLatlngs = stops.map(s => [s.latitude, s.longitude]);
    const initialLinePoints = (roadGeometry && roadGeometry.length > 0) ? roadGeometry : stopLatlngs;
    this.currentRouteCoordinates = initialLinePoints;

    // Rota Principal: Azul Elétrico Apple (#0071E3) Seguindo a Malha Viária Real
    this.activePolyline = L.polyline(initialLinePoints, {
      color: '#0071E3',
      weight: 6,
      opacity: 0.95,
      lineCap: 'round',
      lineJoin: 'round'
    }).addTo(this.map);

    // Se a geometria detalhada das ruas não veio pronta, busca no OSRM em background
    if ((!roadGeometry || roadGeometry.length === 0) && stops.length >= 2) {
      this.fetchStreetGeometry(stops).then(streetCoords => {
        if (streetCoords && streetCoords.length > 0 && this.activePolyline) {
          this.activePolyline.setLatLngs(streetCoords);
          this.currentRouteCoordinates = streetCoords;
        }
      });
    }

    // Marcadores para cada parada
    stops.forEach((stop, index) => {
      let iconHtml = '';
      if (stop.stop_type === 'START') {
        iconHtml = `<div style="background:#0071E3; width:28px; height:28px; border-radius:50%; border:3px solid #FFF; display:flex; align-items:center; justify-content:center; color:#FFF; font-weight:bold; font-size:12px;">🏠</div>`;
      } else if (stop.stop_type === 'MEAL_BREAK') {
        iconHtml = `<div style="background:#30D158; width:28px; height:28px; border-radius:50%; border:3px solid #FFF; display:flex; align-items:center; justify-content:center; color:#000; font-weight:bold; font-size:12px;">🍽️</div>`;
      } else if (stop.is_slow_dock) {
        iconHtml = `<div style="background:#FF9F0A; width:30px; height:30px; border-radius:50%; border:3px solid #FFF; display:flex; align-items:center; justify-content:center; color:#000; font-weight:bold; font-size:13px;">${stop.step_number}</div>`;
      } else {
        iconHtml = `<div style="background:#F5F5F7; width:26px; height:26px; border-radius:50%; border:3px solid #0071E3; display:flex; align-items:center; justify-content:center; color:#1D1D1F; font-weight:bold; font-size:12px;">${stop.step_number}</div>`;
      }

      const customIcon = L.divIcon({
        className: 'custom-stop-marker',
        html: iconHtml,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });

      const marker = L.marker([stop.latitude, stop.longitude], { icon: customIcon }).addTo(this.map);
      marker.bindTooltip(`<b>${stop.name}</b><br>${stop.arrival_time}`, {
        direction: 'top',
        className: 'apple-map-tooltip'
      });
      this.markers.push(marker);
    });

    // Marcador do Caminhão em Navegação Ativa (com suporte a rotação dinâmica e pulso)
    const firstPos = [stops[0].latitude, stops[0].longitude];
    this.createTruckMarker(firstPos, 0);

    this.map.fitBounds(this.activePolyline.getBounds(), { padding: [80, 80] });
  }

  createTruckMarker(pos, bearing = 0) {
    if (this.truckMarker) {
      this.map.removeLayer(this.truckMarker);
    }
    const truckIcon = L.divIcon({
      className: 'truck-navigation-marker',
      html: `
        <div class="truck-marker-container">
          <div class="truck-marker-pulse"></div>
          <div class="truck-marker-body" id="truck-marker-inner" style="transform: rotate(${bearing}deg); background:#30D158; width:38px; height:38px; border-radius:50%; border:3px solid #FFFFFF; box-shadow:0 0 16px rgba(48,209,88,0.7); display:flex; align-items:center; justify-content:center; font-size:20px;">
            🚛
          </div>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22]
    });
    this.truckMarker = L.marker(pos, { icon: truckIcon, zIndexOffset: 1000 }).addTo(this.map);
    return this.truckMarker;
  }

  updateTruckNavigation(lat, lon, bearing = 0, shouldPan = true) {
    if (!this.truckMarker) {
      this.createTruckMarker([lat, lon], bearing);
    } else {
      this.truckMarker.setLatLng([lat, lon]);
      const el = this.truckMarker.getElement();
      const inner = el ? el.querySelector('#truck-marker-inner') : document.getElementById('truck-marker-inner');
      if (inner) {
        inner.style.transform = `rotate(${bearing}deg)`;
      }
    }
    if (shouldPan && this.map) {
      const now = Date.now();
      if (!this._lastPanTime || (now - this._lastPanTime >= 400)) {
        this.map.panTo([lat, lon], { animate: true, duration: 0.35 });
        this._lastPanTime = now;
      }
    }
  }

  getRouteCoordinates() {
    if (this.currentRouteCoordinates && this.currentRouteCoordinates.length > 0) {
      return this.currentRouteCoordinates;
    }
    if (this.activePolyline) {
      const latlngs = this.activePolyline.getLatLngs();
      return latlngs.map(ll => [ll.lat, ll.lng]);
    }
    return [];
  }

  async fetchStreetGeometry(stops) {
    try {
      const coordsQuery = stops.map(s => `${s.longitude.toFixed(6)},${s.latitude.toFixed(6)}`).join(';');
      const url = `https://router.project-osrm.org/route/v1/driving/${coordsQuery}?overview=full&geometries=geojson`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (data.routes && data.routes[0]) {
          return data.routes[0].geometry.coordinates.map(pt => [pt[1], pt[0]]);
        }
      }
    } catch (e) {
      console.warn('Erro ao consultar OSRM no client:', e);
    }
    return null;
  }

  showAlternativeFastRoute(coords) {
    if (this.alternativePolyline) {
      this.map.removeLayer(this.alternativePolyline);
    }
    // Rota Alternativa: Verde Esmeralda Apple (#30D158)
    this.alternativePolyline = L.polyline(coords, {
      color: '#30D158',
      weight: 7,
      opacity: 0.95,
      dashArray: '8, 8',
      lineCap: 'round'
    }).addTo(this.map);
  }

  clearAlternativeRoute() {
    if (this.alternativePolyline) {
      this.map.removeLayer(this.alternativePolyline);
      this.alternativePolyline = null;
    }
  }

  clearLayers() {
    if (this.activePolyline) {
      this.map.removeLayer(this.activePolyline);
      this.activePolyline = null;
    }
    this.clearAlternativeRoute();
    this.markers.forEach(m => this.map.removeLayer(m));
    this.markers = [];
    if (this.truckMarker) {
      this.map.removeLayer(this.truckMarker);
      this.truckMarker = null;
    }
  }

  recenter() {
    if (this.truckMarker) {
      this.map.setView(this.truckMarker.getLatLng(), 14, { animate: true });
    } else if (this.activePolyline) {
      this.map.fitBounds(this.activePolyline.getBounds(), { padding: [60, 60] });
    }
  }
}

window.mapEngine = null;
